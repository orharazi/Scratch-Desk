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
from datetime import datetime
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

    def generate_summary(self, csv_path=None):
        """Generate a summary dict from the analytics CSV.

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
            return None

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
        }

    def send_report(self, csv_path=None):
        """Build and send an HTML summary email with CSV attachment.

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

        # Generate summary
        summary = self.generate_summary(csv_path)
        if summary is None:
            return False, 'No analytics data available'

        # Build email
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = f"{subject_prefix} - {datetime.now().strftime('%Y-%m-%d')}"

        # HTML body
        status_rows = ''
        for status, count in sorted(summary['status_counts'].items()):
            status_rows += f'<tr><td>{status}</td><td>{count}</td></tr>\n'

        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
        <h2>Scratch-Desk Analytics Report</h2>
        <p>Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        <p>Date range: {summary['date_from'][:10] if summary['date_from'] != 'N/A' else 'N/A'}
           to {summary['date_to'][:10] if summary['date_to'] != 'N/A' else 'N/A'}</p>

        <h3>Summary</h3>
        <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse;">
        <tr><td><b>Total Runs</b></td><td>{summary['total_runs']}</td></tr>
        <tr><td><b>Success Rate</b></td><td>{summary['success_rate']}%</td></tr>
        <tr><td><b>Average Duration</b></td><td>{summary['avg_duration']}s</td></tr>
        <tr><td><b>Most Run Program</b></td><td>{summary['most_run_program'][0]} ({summary['most_run_program'][1]} runs)</td></tr>
        <tr><td><b>Most Common Safety Code</b></td><td>{summary['most_common_safety'][0]} ({summary['most_common_safety'][1]} times)</td></tr>
        </table>

        <h3>Runs by Status</h3>
        <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse;">
        <tr><th>Status</th><th>Count</th></tr>
        {status_rows}
        </table>

        <p><i>Full CSV data is attached.</i></p>
        </body>
        </html>
        """

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

    def _scheduler_loop(self):
        """Background loop that checks if it's time to send a report"""
        while not self._scheduler_stop.is_set():
            try:
                email_settings = self._get_email_settings()
                if not email_settings.get('schedule_enabled', False):
                    break

                if not email_settings.get('enabled', False):
                    # Email disabled, just sleep and check again
                    self._scheduler_stop.wait(60)
                    continue

                schedule_time = email_settings.get('schedule_time', '08:00')
                interval_hours = email_settings.get('schedule_interval_hours', 24)
                last_sent = email_settings.get('last_sent', '')

                # Check if we should send now
                should_send = False
                now = datetime.now()

                if last_sent:
                    try:
                        last_sent_dt = datetime.fromisoformat(last_sent)
                        hours_since = (now - last_sent_dt).total_seconds() / 3600
                        if hours_since >= interval_hours:
                            # Check if we're at or past the schedule time
                            current_time = now.strftime('%H:%M')
                            if current_time >= schedule_time:
                                should_send = True
                    except (ValueError, TypeError):
                        should_send = True  # Invalid last_sent, send now
                else:
                    # Never sent before, check schedule time
                    current_time = now.strftime('%H:%M')
                    if current_time >= schedule_time:
                        should_send = True

                if should_send:
                    self.logger.info("Scheduled analytics report sending...", category="execution")
                    success, error = self.send_report()
                    if not success:
                        self.logger.warning(f"Scheduled report failed: {error}", category="execution")

            except Exception as e:
                self.logger.warning(f"Scheduler error: {e}", category="execution")

            # Check every 60 seconds
            self._scheduler_stop.wait(60)
