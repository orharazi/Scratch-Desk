#!/usr/bin/env python3
"""
Email Reporter for Scratch-Desk Analytics
==========================================

Generates summary reports from analytics CSV data and sends
via SMTP with CSV attachment. Includes a cron-like scheduler
for automatic periodic reports.

Usage:
    from core.email_reporter import get_email_reporter
    reporter = get_email_reporter()
    success, error = reporter.send_report()
"""

import csv
import json
import os
import smtplib
import threading
import time
from collections import Counter
from datetime import datetime, timedelta
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders

from core.logger import get_logger


def _load_settings():
    """Load settings from config/settings.json"""
    try:
        with open('config/settings.json', 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_settings(settings):
    """Save settings to config/settings.json"""
    try:
        with open('config/settings.json', 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


_reporter_instance = None
_reporter_lock = threading.Lock()


def get_email_reporter():
    """Get singleton EmailReporter instance"""
    global _reporter_instance
    if _reporter_instance is None:
        with _reporter_lock:
            if _reporter_instance is None:
                _reporter_instance = EmailReporter()
    return _reporter_instance


class EmailReporter:
    """Generates and sends analytics email reports"""

    def __init__(self):
        self.logger = get_logger()
        self._scheduler_thread = None
        self._scheduler_stop = threading.Event()

    def _get_email_settings(self):
        """Get email configuration from settings"""
        settings = _load_settings()
        return settings.get('analytics', {}).get('email', {})

    def _get_csv_path(self):
        """Get analytics CSV path from settings"""
        settings = _load_settings()
        return settings.get('analytics', {}).get('csv_file_path', 'data/analytics/runs.csv')

    # Hebrew translations for status values
    STATUS_HEBREW = {
        'success': 'הצלחה',
        'user_stop': 'עצירת משתמש',
        'emergency_stop': 'עצירת חירום',
        'safety_violation': 'הפרת בטיחות',
        'error': 'שגיאה',
        'unknown': 'לא ידוע',
    }

    HARDWARE_MODE_HEBREW = {
        'mock': 'סימולציה',
        'real': 'חומרה אמיתית',
    }

    def _translate_status(self, status):
        """Translate status to Hebrew"""
        return self.STATUS_HEBREW.get(status, status)

    def _translate_hardware_mode(self, mode):
        """Translate hardware mode to Hebrew"""
        return self.HARDWARE_MODE_HEBREW.get(mode, mode)

    FREQUENCY_HEBREW = {
        'daily': 'יומי',
        'weekly': 'שבועי',
        'monthly': 'חודשי',
    }

    @staticmethod
    def _get_period_range(frequency):
        """Return (start_date, end_date, hebrew_label) for the given frequency.

        The period covers the *previous* complete interval:
            - daily  : yesterday 00:00 → yesterday 23:59:59
            - weekly : last Monday 00:00 → last Sunday 23:59:59
            - monthly: 1st of last month 00:00 → last day of last month 23:59:59

        When the report fires at e.g. 08:00, the period that just ended
        is the one we want to report on.
        """
        now = datetime.now()

        if frequency == 'daily':
            yesterday = now.date() - timedelta(days=1)
            start = datetime(yesterday.year, yesterday.month, yesterday.day, 0, 0, 0)
            end = datetime(yesterday.year, yesterday.month, yesterday.day, 23, 59, 59)
        elif frequency == 'weekly':
            # Last completed week (Mon-Sun)
            # today.weekday(): 0=Mon ... 6=Sun
            days_since_monday = now.weekday()  # 0 if today is Mon
            this_monday = now.date() - timedelta(days=days_since_monday)
            last_monday = this_monday - timedelta(days=7)
            last_sunday = this_monday - timedelta(days=1)
            start = datetime(last_monday.year, last_monday.month, last_monday.day, 0, 0, 0)
            end = datetime(last_sunday.year, last_sunday.month, last_sunday.day, 23, 59, 59)
        elif frequency == 'monthly':
            # Last completed month
            first_of_this_month = now.date().replace(day=1)
            last_day_prev_month = first_of_this_month - timedelta(days=1)
            first_of_prev_month = last_day_prev_month.replace(day=1)
            start = datetime(first_of_prev_month.year, first_of_prev_month.month, first_of_prev_month.day, 0, 0, 0)
            end = datetime(last_day_prev_month.year, last_day_prev_month.month, last_day_prev_month.day, 23, 59, 59)
        else:
            # Fallback: everything
            return None, None, ''

        return start, end, ''

    def generate_summary(self, csv_path=None, period=None):
        """Generate a summary dict from the analytics CSV.

        Args:
            csv_path: Path to the CSV file (uses settings default if None)
            period: Optional (start_datetime, end_datetime) tuple to filter rows

        Returns:
            dict with summary statistics, or None if no data
        """
        if csv_path is None:
            csv_path = self._get_csv_path()

        if not os.path.exists(csv_path):
            return None

        rows = []
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    rows.append(row)
        except Exception as e:
            self.logger.warning(f"Failed to read analytics CSV: {e}", category="execution")

        # Filter rows by period if provided
        if period and period[0] and period[1]:
            period_start, period_end = period
            start_iso = period_start.isoformat()
            end_iso = period_end.isoformat()
            rows = [
                r for r in rows
                if start_iso <= r.get('timestamp_start', '') <= end_iso
            ]

        if not rows:
            return None

        total_runs = len(rows)

        # Count by status
        status_counts = Counter(r.get('completion_status', 'unknown') for r in rows)
        success_count = status_counts.get('success', 0)
        success_rate = (success_count / total_runs * 100) if total_runs > 0 else 0

        # Average duration
        durations = []
        for r in rows:
            try:
                d = float(r.get('duration_seconds', 0))
                if d > 0:
                    durations.append(d)
            except (ValueError, TypeError):
                pass
        avg_duration = sum(durations) / len(durations) if durations else 0

        # Most-run program
        program_counts = Counter(r.get('program_name', '') for r in rows if r.get('program_name'))
        most_run_program = program_counts.most_common(1)[0] if program_counts else ('N/A', 0)

        # Most common safety code
        safety_codes = Counter(
            r.get('safety_code', '') for r in rows
            if r.get('safety_code')
        )
        most_common_safety = safety_codes.most_common(1)[0] if safety_codes else ('N/A', 0)

        # Date range
        timestamps = [r.get('timestamp_start', '') for r in rows if r.get('timestamp_start')]
        date_from = min(timestamps) if timestamps else 'N/A'
        date_to = max(timestamps) if timestamps else 'N/A'

        # Hardware mode breakdown
        hardware_counts = Counter(r.get('hardware_mode', 'unknown') for r in rows)

        # Total steps across all runs
        total_steps_all = 0
        completed_steps_all = 0
        successful_steps_all = 0
        failed_steps_all = 0
        for r in rows:
            try:
                total_steps_all += int(r.get('total_steps', 0))
                completed_steps_all += int(r.get('completed_steps', 0))
                successful_steps_all += int(r.get('successful_steps', 0))
                failed_steps_all += int(r.get('failed_steps', 0))
            except (ValueError, TypeError):
                pass

        # Per-program breakdown: runs, durations, success/fail
        program_stats = {}
        for r in rows:
            name = r.get('program_name', '') or 'ללא שם'
            if name not in program_stats:
                program_stats[name] = {
                    'run_count': 0,
                    'success_count': 0,
                    'fail_count': 0,
                    'total_duration': 0.0,
                    'durations': [],
                }
            ps = program_stats[name]
            ps['run_count'] += 1
            status = r.get('completion_status', 'unknown')
            if status == 'success':
                ps['success_count'] += 1
            else:
                ps['fail_count'] += 1
            try:
                d = float(r.get('duration_seconds', 0))
                ps['total_duration'] += d
                if d > 0:
                    ps['durations'].append(d)
            except (ValueError, TypeError):
                pass

        # Calculate averages and sort by run_count descending
        program_breakdown = []
        for name, ps in program_stats.items():
            avg_dur = (
                round(sum(ps['durations']) / len(ps['durations']), 1)
                if ps['durations'] else 0
            )
            program_breakdown.append({
                'name': name,
                'run_count': ps['run_count'],
                'success_count': ps['success_count'],
                'fail_count': ps['fail_count'],
                'total_duration': round(ps['total_duration'], 1),
                'avg_duration': avg_dur,
            })
        program_breakdown.sort(key=lambda x: x['run_count'], reverse=True)

        # Failed/incomplete runs (anything not 'success')
        failed_runs = []
        for r in rows:
            status = r.get('completion_status', 'unknown')
            if status != 'success':
                failed_runs.append({
                    'timestamp': r.get('timestamp_start', 'N/A'),
                    'program_name': r.get('program_name', 'N/A'),
                    'status': status,
                    'completed_steps': r.get('completed_steps', '0'),
                    'total_steps': r.get('total_steps', '0'),
                    'error_message': r.get('error_message', ''),
                    'safety_code': r.get('safety_code', ''),
                    'safety_message': r.get('safety_message', ''),
                    'hardware_mode': r.get('hardware_mode', 'unknown'),
                })

        return {
            'total_runs': total_runs,
            'success_count': success_count,
            'success_rate': round(success_rate, 1),
            'status_counts': dict(status_counts),
            'avg_duration': round(avg_duration, 1),
            'most_run_program': most_run_program,
            'most_common_safety': most_common_safety,
            'date_from': date_from,
            'date_to': date_to,
            'hardware_counts': dict(hardware_counts),
            'total_steps_all': total_steps_all,
            'completed_steps_all': completed_steps_all,
            'successful_steps_all': successful_steps_all,
            'failed_steps_all': failed_steps_all,
            'failed_runs': failed_runs,
            'program_breakdown': program_breakdown,
        }

    def send_report(self, csv_path=None, period=None):
        """Build and send an HTML summary email with CSV attachment.

        Args:
            csv_path: Path to analytics CSV (uses settings default if None)
            period: Optional (start_datetime, end_datetime) tuple. When provided,
                    the report only includes data within this range. When None,
                    the period is auto-calculated from the configured schedule_frequency.

        Returns:
            tuple: (success: bool, error_message: str)
        """
        email_settings = self._get_email_settings()
        if not email_settings.get('enabled', False):
            return False, 'Email reporting is disabled'

        smtp_server = email_settings.get('smtp_server', '')
        smtp_port = email_settings.get('smtp_port', 587)
        smtp_use_tls = email_settings.get('smtp_use_tls', True)
        smtp_username = email_settings.get('smtp_username', '')
        smtp_password = email_settings.get('smtp_password', '')
        sender_email = email_settings.get('sender_email', '')
        recipient_email = email_settings.get('recipient_email', '')
        subject_prefix = email_settings.get('subject_prefix', 'Scratch-Desk Analytics Report')

        if not smtp_server or not recipient_email or not sender_email:
            return False, 'Missing email configuration (server, sender, or recipient)'

        if csv_path is None:
            csv_path = self._get_csv_path()

        # Determine period: use explicit period if given, else auto from frequency
        frequency = email_settings.get('schedule_frequency', 'daily')
        if period is not None:
            period_start, period_end = period
        else:
            period_start, period_end, _ = self._get_period_range(frequency)

        effective_period = (period_start, period_end) if period_start and period_end else None

        # Generate summary filtered to the relevant period
        summary = self.generate_summary(csv_path, period=effective_period)
        if summary is None:
            return False, 'No analytics data available'

        # Inject period metadata for the HTML builder
        freq_label = self.FREQUENCY_HEBREW.get(frequency, frequency)
        if period is not None:
            # Manual send — label as custom range
            summary['period_label'] = 'דוח אנליטיקה'
        else:
            summary['period_label'] = f'דוח {freq_label}'
        if period_start and period_end:
            summary['period_from'] = period_start.strftime('%Y-%m-%d')
            summary['period_to'] = period_end.strftime('%Y-%m-%d')

        # Build email
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = f"{subject_prefix} ({freq_label}) - {datetime.now().strftime('%Y-%m-%d')}"

        # Build Hebrew HTML body
        html_body = self._build_hebrew_html(summary)
        msg.attach(MIMEText(html_body, 'html'))

        # Attach CSV file
        if os.path.exists(csv_path):
            try:
                with open(csv_path, 'rb') as f:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(f.read())
                    encoders.encode_base64(part)
                    filename = os.path.basename(csv_path)
                    part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
                    msg.attach(part)
            except Exception as e:
                self.logger.warning(f"Failed to attach CSV: {e}", category="execution")

        # Send email
        try:
            if smtp_use_tls:
                server = smtplib.SMTP(smtp_server, smtp_port, timeout=30)
                server.starttls()
            else:
                server = smtplib.SMTP(smtp_server, smtp_port, timeout=30)

            if smtp_username and smtp_password:
                server.login(smtp_username, smtp_password)

            server.send_message(msg)
            server.quit()

            # Update last_sent timestamp
            self._update_last_sent()

            self.logger.info("Analytics report sent successfully", category="execution")
            return True, ''

        except smtplib.SMTPAuthenticationError:
            error = 'SMTP authentication failed - check username/password'
            self.logger.error(f"Email send failed: {error}", category="execution")
            return False, error
        except smtplib.SMTPConnectError:
            error = f'Could not connect to SMTP server {smtp_server}:{smtp_port}'
            self.logger.error(f"Email send failed: {error}", category="execution")
            return False, error
        except Exception as e:
            error = str(e)
            self.logger.error(f"Email send failed: {error}", category="execution")
            return False, error

    def _build_hebrew_html(self, summary):
        """Build the full Hebrew RTL HTML email body"""

        # Use period dates if available (filtered report), otherwise fall back to data range
        period_label = summary.get('period_label', 'דוח אנליטיקה')
        date_from = summary.get('period_from') or (
            summary['date_from'][:10] if summary['date_from'] != 'N/A' else 'N/A'
        )
        date_to = summary.get('period_to') or (
            summary['date_to'][:10] if summary['date_to'] != 'N/A' else 'N/A'
        )

        # Status colors for visual clarity
        status_colors = {
            'success': '#28a745',
            'user_stop': '#fd7e14',
            'emergency_stop': '#dc3545',
            'safety_violation': '#e67e22',
            'error': '#c0392b',
            'unknown': '#6c757d',
        }

        # --- Status breakdown rows ---
        status_rows = ''
        for status, count in sorted(summary['status_counts'].items()):
            color = status_colors.get(status, '#6c757d')
            hebrew_status = self._translate_status(status)
            status_rows += (
                f'<tr>'
                f'<td style="padding:8px;border:1px solid #ddd;">'
                f'<span style="color:{color};font-weight:bold;">{hebrew_status}</span></td>'
                f'<td style="padding:8px;border:1px solid #ddd;text-align:center;">{count}</td>'
                f'</tr>\n'
            )

        # --- Hardware mode breakdown rows ---
        hardware_rows = ''
        for mode, count in sorted(summary.get('hardware_counts', {}).items()):
            hebrew_mode = self._translate_hardware_mode(mode)
            hardware_rows += (
                f'<tr>'
                f'<td style="padding:8px;border:1px solid #ddd;">{hebrew_mode}</td>'
                f'<td style="padding:8px;border:1px solid #ddd;text-align:center;">{count}</td>'
                f'</tr>\n'
            )

        # --- Program breakdown rows ---
        program_rows = ''
        program_breakdown = summary.get('program_breakdown', [])
        for i, prog in enumerate(program_breakdown):
            bg = 'background-color:#f9f9f9;' if i % 2 == 0 else ''
            program_rows += (
                f'<tr style="{bg}">'
                f'<td style="padding:8px;border:1px solid #ddd;">{prog["name"]}</td>'
                f'<td style="padding:8px;border:1px solid #ddd;text-align:center;">{prog["run_count"]}</td>'
                f'<td style="padding:8px;border:1px solid #ddd;text-align:center;color:#28a745;">'
                f'{prog["success_count"]}</td>'
                f'<td style="padding:8px;border:1px solid #ddd;text-align:center;color:#dc3545;">'
                f'{prog["fail_count"]}</td>'
                f'<td style="padding:8px;border:1px solid #ddd;text-align:center;">'
                f'{prog["avg_duration"]} שנ\'</td>'
                f'<td style="padding:8px;border:1px solid #ddd;text-align:center;">'
                f'{prog["total_duration"]} שנ\'</td>'
                f'</tr>\n'
            )

        # --- Failed runs detail rows ---
        failed_runs_html = ''
        failed_runs = summary.get('failed_runs', [])
        if failed_runs:
            failed_detail_rows = ''
            for run in failed_runs[-20:]:  # Last 20 failed runs
                ts = run['timestamp'][:19].replace('T', ' ') if run['timestamp'] != 'N/A' else 'N/A'
                color = status_colors.get(run['status'], '#6c757d')
                hebrew_status = self._translate_status(run['status'])
                hebrew_hw = self._translate_hardware_mode(run['hardware_mode'])
                info = run['error_message'] or run['safety_message'] or ''
                if len(info) > 60:
                    info = info[:60] + '...'

                failed_detail_rows += (
                    f'<tr>'
                    f'<td style="padding:6px;border:1px solid #ddd;font-size:13px;">{ts}</td>'
                    f'<td style="padding:6px;border:1px solid #ddd;font-size:13px;">{run["program_name"]}</td>'
                    f'<td style="padding:6px;border:1px solid #ddd;font-size:13px;">'
                    f'<span style="color:{color};font-weight:bold;">{hebrew_status}</span></td>'
                    f'<td style="padding:6px;border:1px solid #ddd;font-size:13px;text-align:center;">'
                    f'{run["completed_steps"]}/{run["total_steps"]}</td>'
                    f'<td style="padding:6px;border:1px solid #ddd;font-size:13px;">{hebrew_hw}</td>'
                    f'<td style="padding:6px;border:1px solid #ddd;font-size:13px;">{info}</td>'
                    f'</tr>\n'
                )

            failed_runs_html = f"""
            <h3 style="color:#dc3545;">הרצות שנכשלו / לא הושלמו ({len(failed_runs)})</h3>
            <table border="0" cellpadding="0" cellspacing="0"
                   style="border-collapse:collapse;width:100%;border:1px solid #ddd;">
            <tr style="background-color:#f8d7da;">
                <th style="padding:8px;border:1px solid #ddd;">תאריך</th>
                <th style="padding:8px;border:1px solid #ddd;">תוכנית</th>
                <th style="padding:8px;border:1px solid #ddd;">סטטוס</th>
                <th style="padding:8px;border:1px solid #ddd;">צעדים</th>
                <th style="padding:8px;border:1px solid #ddd;">מצב חומרה</th>
                <th style="padding:8px;border:1px solid #ddd;">פרטים</th>
            </tr>
            {failed_detail_rows}
            </table>
            """

        # --- Step completion stats ---
        total_steps_all = summary.get('total_steps_all', 0)
        completed_steps_all = summary.get('completed_steps_all', 0)
        successful_steps_all = summary.get('successful_steps_all', 0)
        failed_steps_all = summary.get('failed_steps_all', 0)
        step_completion_rate = (
            round(completed_steps_all / total_steps_all * 100, 1)
            if total_steps_all > 0 else 0
        )

        html = f"""
        <html>
        <head>
        <meta charset="utf-8">
        </head>
        <body dir="rtl" style="font-family: Arial, sans-serif; direction: rtl; text-align: right;
                                background-color: #f5f5f5; padding: 20px;">

        <div style="max-width: 700px; margin: 0 auto; background: white; border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1); padding: 30px;">

        <h2 style="color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px;">
            {period_label} - Scratch-Desk
        </h2>

        <p style="color: #7f8c8d;">
            הדוח הופק: <b>{datetime.now().strftime('%Y-%m-%d %H:%M')}</b>
        </p>
        <p style="color: #7f8c8d;">
            תקופת דוח: <b>{date_from}</b> עד <b>{date_to}</b>
        </p>

        <!-- סיכום כללי -->
        <h3 style="color: #2c3e50;">סיכום כללי</h3>
        <table border="0" cellpadding="0" cellspacing="0"
               style="border-collapse:collapse;width:100%;border:1px solid #ddd;">
        <tr style="background-color:#eaf2f8;">
            <td style="padding:10px;border:1px solid #ddd;font-weight:bold;width:50%;">סה"כ הרצות</td>
            <td style="padding:10px;border:1px solid #ddd;text-align:center;">{summary['total_runs']}</td>
        </tr>
        <tr>
            <td style="padding:10px;border:1px solid #ddd;font-weight:bold;">הרצות מוצלחות</td>
            <td style="padding:10px;border:1px solid #ddd;text-align:center;color:#28a745;font-weight:bold;">
                {summary['success_count']}</td>
        </tr>
        <tr style="background-color:#eaf2f8;">
            <td style="padding:10px;border:1px solid #ddd;font-weight:bold;">אחוז הצלחה</td>
            <td style="padding:10px;border:1px solid #ddd;text-align:center;">{summary['success_rate']}%</td>
        </tr>
        <tr>
            <td style="padding:10px;border:1px solid #ddd;font-weight:bold;">הרצות שנכשלו</td>
            <td style="padding:10px;border:1px solid #ddd;text-align:center;color:#dc3545;font-weight:bold;">
                {len(failed_runs)}</td>
        </tr>
        <tr style="background-color:#eaf2f8;">
            <td style="padding:10px;border:1px solid #ddd;font-weight:bold;">משך ממוצע</td>
            <td style="padding:10px;border:1px solid #ddd;text-align:center;">{summary['avg_duration']} שניות</td>
        </tr>
        <tr>
            <td style="padding:10px;border:1px solid #ddd;font-weight:bold;">תוכנית שהורצה הכי הרבה</td>
            <td style="padding:10px;border:1px solid #ddd;text-align:center;">
                {summary['most_run_program'][0]} ({summary['most_run_program'][1]} הרצות)</td>
        </tr>
        <tr style="background-color:#eaf2f8;">
            <td style="padding:10px;border:1px solid #ddd;font-weight:bold;">קוד בטיחות שכיח</td>
            <td style="padding:10px;border:1px solid #ddd;text-align:center;">
                {summary['most_common_safety'][0]} ({summary['most_common_safety'][1]} פעמים)</td>
        </tr>
        </table>

        <!-- מצב חומרה -->
        <h3 style="color: #2c3e50;">מצב חומרה</h3>
        <table border="0" cellpadding="0" cellspacing="0"
               style="border-collapse:collapse;width:100%;border:1px solid #ddd;">
        <tr style="background-color:#d5f5e3;">
            <th style="padding:8px;border:1px solid #ddd;">מצב</th>
            <th style="padding:8px;border:1px solid #ddd;">כמות הרצות</th>
        </tr>
        {hardware_rows}
        </table>

        <!-- סטטיסטיקת צעדים -->
        <h3 style="color: #2c3e50;">סטטיסטיקת צעדים</h3>
        <table border="0" cellpadding="0" cellspacing="0"
               style="border-collapse:collapse;width:100%;border:1px solid #ddd;">
        <tr style="background-color:#eaf2f8;">
            <td style="padding:10px;border:1px solid #ddd;font-weight:bold;">סה"כ צעדים</td>
            <td style="padding:10px;border:1px solid #ddd;text-align:center;">{total_steps_all}</td>
        </tr>
        <tr>
            <td style="padding:10px;border:1px solid #ddd;font-weight:bold;">צעדים שבוצעו</td>
            <td style="padding:10px;border:1px solid #ddd;text-align:center;">{completed_steps_all}</td>
        </tr>
        <tr style="background-color:#eaf2f8;">
            <td style="padding:10px;border:1px solid #ddd;font-weight:bold;">צעדים מוצלחים</td>
            <td style="padding:10px;border:1px solid #ddd;text-align:center;color:#28a745;">
                {successful_steps_all}</td>
        </tr>
        <tr>
            <td style="padding:10px;border:1px solid #ddd;font-weight:bold;">צעדים שנכשלו</td>
            <td style="padding:10px;border:1px solid #ddd;text-align:center;color:#dc3545;">
                {failed_steps_all}</td>
        </tr>
        <tr style="background-color:#eaf2f8;">
            <td style="padding:10px;border:1px solid #ddd;font-weight:bold;">אחוז השלמת צעדים</td>
            <td style="padding:10px;border:1px solid #ddd;text-align:center;">{step_completion_rate}%</td>
        </tr>
        </table>

        <!-- התפלגות לפי סטטוס -->
        <h3 style="color: #2c3e50;">התפלגות לפי סטטוס</h3>
        <table border="0" cellpadding="0" cellspacing="0"
               style="border-collapse:collapse;width:100%;border:1px solid #ddd;">
        <tr style="background-color:#fdebd0;">
            <th style="padding:8px;border:1px solid #ddd;">סטטוס</th>
            <th style="padding:8px;border:1px solid #ddd;">כמות</th>
        </tr>
        {status_rows}
        </table>

        <!-- הרצות לפי תוכנית -->
        <h3 style="color: #2c3e50;">הרצות לפי תוכנית</h3>
        <table border="0" cellpadding="0" cellspacing="0"
               style="border-collapse:collapse;width:100%;border:1px solid #ddd;">
        <tr style="background-color:#d6eaf8;">
            <th style="padding:8px;border:1px solid #ddd;">שם תוכנית</th>
            <th style="padding:8px;border:1px solid #ddd;">הרצות</th>
            <th style="padding:8px;border:1px solid #ddd;">הצלחות</th>
            <th style="padding:8px;border:1px solid #ddd;">כישלונות</th>
            <th style="padding:8px;border:1px solid #ddd;">משך ממוצע</th>
            <th style="padding:8px;border:1px solid #ddd;">זמן כולל</th>
        </tr>
        {program_rows}
        </table>

        <!-- הרצות שנכשלו -->
        {failed_runs_html}

        <hr style="border:none;border-top:1px solid #eee;margin:20px 0;">
        <p style="color: #95a5a6; font-size: 12px;">
            קובץ CSV מלא עם כל הנתונים מצורף להודעה זו.
        </p>

        </div>
        </body>
        </html>
        """
        return html

    def _update_last_sent(self):
        """Update the last_sent timestamp in settings"""
        try:
            settings = _load_settings()
            if 'analytics' not in settings:
                settings['analytics'] = {}
            if 'email' not in settings['analytics']:
                settings['analytics']['email'] = {}
            settings['analytics']['email']['last_sent'] = datetime.now().isoformat()
            _save_settings(settings)
        except Exception as e:
            self.logger.warning(f"Failed to update last_sent: {e}", category="execution")

    def start_scheduler(self):
        """Start the background email scheduler thread"""
        email_settings = self._get_email_settings()
        if not email_settings.get('schedule_enabled', False):
            return

        if self._scheduler_thread and self._scheduler_thread.is_alive():
            return  # Already running

        self._scheduler_stop.clear()
        self._scheduler_thread = threading.Thread(
            target=self._scheduler_loop, daemon=True
        )
        self._scheduler_thread.start()
        self.logger.info("Email report scheduler started", category="execution")

    def stop_scheduler(self):
        """Stop the background email scheduler"""
        self._scheduler_stop.set()
        if self._scheduler_thread and self._scheduler_thread.is_alive():
            self._scheduler_thread.join(timeout=5)
        self._scheduler_thread = None
        self.logger.info("Email report scheduler stopped", category="execution")

    def _is_schedule_due(self, now, email_settings):
        """Check whether a scheduled report should be sent right now.

        Supports three frequencies:
            - 'daily'   : every day at schedule_time
            - 'weekly'  : on schedule_day_of_week (0=Mon..6=Sun) at schedule_time
            - 'monthly' : on schedule_day_of_month (1-28) at schedule_time

        Returns True only when:
            1. The current time is at or past schedule_time, AND
            2. Today matches the correct day for the chosen frequency, AND
            3. Enough time has passed since last_sent to avoid duplicate sends
               within the same scheduling window.
        """
        schedule_time = email_settings.get('schedule_time', '08:00')
        frequency = email_settings.get('schedule_frequency', 'daily')
        last_sent = email_settings.get('last_sent', '')

        current_time = now.strftime('%H:%M')

        # Not yet time today
        if current_time < schedule_time:
            return False

        # Check day match for weekly / monthly
        if frequency == 'weekly':
            target_dow = email_settings.get('schedule_day_of_week', 0)  # 0=Mon
            if now.weekday() != target_dow:
                return False
        elif frequency == 'monthly':
            target_dom = email_settings.get('schedule_day_of_month', 1)  # 1-28
            if now.day != target_dom:
                return False
        # 'daily' matches every day — no extra check needed

        # Guard against duplicate sends in the same window
        if last_sent:
            try:
                last_sent_dt = datetime.fromisoformat(last_sent)
                if frequency == 'daily':
                    # Already sent today
                    if last_sent_dt.date() == now.date():
                        return False
                elif frequency == 'weekly':
                    # Already sent this calendar week (same iso week)
                    if (last_sent_dt.isocalendar()[1] == now.isocalendar()[1]
                            and last_sent_dt.year == now.year):
                        return False
                elif frequency == 'monthly':
                    # Already sent this calendar month
                    if (last_sent_dt.month == now.month
                            and last_sent_dt.year == now.year):
                        return False
            except (ValueError, TypeError):
                pass  # Invalid last_sent → allow send

        return True

    def _scheduler_loop(self):
        """Background loop that checks if it's time to send a report"""
        while not self._scheduler_stop.is_set():
            try:
                email_settings = self._get_email_settings()
                if not email_settings.get('schedule_enabled', False):
                    break

                if not email_settings.get('enabled', False):
                    self._scheduler_stop.wait(60)
                    continue

                now = datetime.now()
                if self._is_schedule_due(now, email_settings):
                    freq = email_settings.get('schedule_frequency', 'daily')
                    self.logger.info(
                        f"Scheduled {freq} analytics report sending...",
                        category="execution",
                    )
                    success, error = self.send_report()
                    if not success:
                        self.logger.warning(
                            f"Scheduled report failed: {error}",
                            category="execution",
                        )

            except Exception as e:
                self.logger.warning(f"Scheduler error: {e}", category="execution")

            # Check every 60 seconds
            self._scheduler_stop.wait(60)
