#!/usr/bin/env python3
"""
Analytics Tab for Admin Tool
=============================

Provides analytics dashboard with:
- Summary cards (total runs, success rate, counts by status, etc.)
- Runs table with date filtering
- Email configuration and manual send
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import csv
import json
import os
from datetime import datetime, timedelta

from core.translations import t


class AnalyticsTab:
    """Analytics dashboard tab for the admin tool"""

    def __init__(self, parent_frame, admin_app):
        self.parent_frame = parent_frame
        self.admin_app = admin_app
        self.runs_data = []
        self.filtered_data = []

        self.create_ui()
        self.load_data()

    def _load_settings(self):
        """Load settings from config/settings.json"""
        try:
            with open('config/settings.json', 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_settings(self, settings):
        """Save settings to config/settings.json"""
        try:
            with open('config/settings.json', 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
        except Exception as e:
            messagebox.showerror(t("Error"), str(e))

    def _get_csv_path(self):
        """Get analytics CSV path"""
        settings = self._load_settings()
        return settings.get('analytics', {}).get('csv_file_path', 'data/analytics/runs.csv')

    def create_ui(self):
        """Create the analytics tab UI"""
        # Main container with padding
        main_frame = ttk.Frame(self.parent_frame, padding="5")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ---- Top bar: filters and actions ----
        top_bar = ttk.Frame(main_frame)
        top_bar.pack(fill=tk.X, pady=(0, 5))

        # Date range filter with spinbox-style date pickers (RTL: labels on right)
        now = datetime.now()
        one_month_ago = now - timedelta(days=30)

        ttk.Label(top_bar, text=t("Date From:"), font=("Arial", 9)).pack(side=tk.RIGHT, padx=(5, 2))

        self.date_from_frame = ttk.Frame(top_bar)
        self.date_from_frame.pack(side=tk.RIGHT, padx=2)

        self.from_day_var = tk.StringVar(value=str(one_month_ago.day).zfill(2))
        self.from_month_var = tk.StringVar(value=str(one_month_ago.month).zfill(2))
        self.from_year_var = tk.StringVar(value=str(one_month_ago.year))

        ttk.Spinbox(self.date_from_frame, from_=1, to=31, width=3,
                     textvariable=self.from_day_var, format='%02.0f').pack(side=tk.RIGHT)
        ttk.Label(self.date_from_frame, text="/").pack(side=tk.RIGHT)
        ttk.Spinbox(self.date_from_frame, from_=1, to=12, width=3,
                     textvariable=self.from_month_var, format='%02.0f').pack(side=tk.RIGHT)
        ttk.Label(self.date_from_frame, text="/").pack(side=tk.RIGHT)
        ttk.Spinbox(self.date_from_frame, from_=2020, to=2030, width=5,
                     textvariable=self.from_year_var).pack(side=tk.RIGHT)

        ttk.Label(top_bar, text=t("Date To:"), font=("Arial", 9)).pack(side=tk.RIGHT, padx=(10, 2))

        self.date_to_frame = ttk.Frame(top_bar)
        self.date_to_frame.pack(side=tk.RIGHT, padx=2)

        self.to_day_var = tk.StringVar(value=str(now.day).zfill(2))
        self.to_month_var = tk.StringVar(value=str(now.month).zfill(2))
        self.to_year_var = tk.StringVar(value=str(now.year))

        ttk.Spinbox(self.date_to_frame, from_=1, to=31, width=3,
                     textvariable=self.to_day_var, format='%02.0f').pack(side=tk.RIGHT)
        ttk.Label(self.date_to_frame, text="/").pack(side=tk.RIGHT)
        ttk.Spinbox(self.date_to_frame, from_=1, to=12, width=3,
                     textvariable=self.to_month_var, format='%02.0f').pack(side=tk.RIGHT)
        ttk.Label(self.date_to_frame, text="/").pack(side=tk.RIGHT)
        ttk.Spinbox(self.date_to_frame, from_=2020, to=2030, width=5,
                     textvariable=self.to_year_var).pack(side=tk.RIGHT)

        ttk.Button(top_bar, text=t("Refresh"), command=self.load_data).pack(side=tk.RIGHT, padx=5)
        ttk.Button(top_bar, text=t("Export CSV"), command=self.export_csv).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_bar, text=t("Clear Data"), command=self.clear_data).pack(side=tk.LEFT, padx=5)

        # ---- Content area: summary + table ----
        content_pane = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        content_pane.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        # Left column: Summary cards
        summary_frame = ttk.LabelFrame(content_pane, text=t("Summary"), padding="10")
        content_pane.add(summary_frame, weight=1)

        self.summary_labels = {}
        summary_items = [
            ('total_runs', t("Total Runs")),
            ('success_rate', t("Success Rate")),
            ('success_count', t("Successful")),
            ('user_stop_count', t("User Stopped")),
            ('safety_violation_count', t("Safety Violations")),
            ('emergency_stop_count', t("Emergency Stops")),
            ('error_count', t("Errors")),
            ('avg_duration', t("Avg Duration")),
            ('most_run_program', t("Most Run Program")),
            ('most_common_safety', t("Common Safety Code")),
        ]

        for i, (key, label_text) in enumerate(summary_items):
            row_frame = ttk.Frame(summary_frame)
            row_frame.pack(fill=tk.X, pady=2)

            ttk.Label(row_frame, text=label_text + ":", font=("Arial", 9, "bold"),
                      width=20, anchor="e").pack(side=tk.RIGHT, padx=(5, 0))
            value_label = ttk.Label(row_frame, text="-", font=("Arial", 10), anchor="e")
            value_label.pack(side=tk.RIGHT, padx=5)
            self.summary_labels[key] = value_label

        # Right column: Runs table
        table_frame = ttk.LabelFrame(content_pane, text=t("Execution History"), padding="5")
        content_pane.add(table_frame, weight=3)

        # Treeview for runs
        columns = ('datetime', 'program', 'status', 'duration', 'steps', 'info')
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=15)

        self.tree.heading('datetime', text=t("Date/Time"))
        self.tree.heading('program', text=t("Program"))
        self.tree.heading('status', text=t("Status"))
        self.tree.heading('duration', text=t("Duration"))
        self.tree.heading('steps', text=t("Steps"))
        self.tree.heading('info', text=t("Info"))

        self.tree.column('datetime', width=140, minwidth=120)
        self.tree.column('program', width=120, minwidth=80)
        self.tree.column('status', width=100, minwidth=80)
        self.tree.column('duration', width=80, minwidth=60)
        self.tree.column('steps', width=80, minwidth=60)
        self.tree.column('info', width=200, minwidth=100)

        # Scrollbar
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Bind double-click for details
        self.tree.bind('<Double-1>', self.show_run_details)

        # Configure tag colors for status
        self.tree.tag_configure('success', foreground='#27AE60')
        self.tree.tag_configure('user_stop', foreground='#F39C12')
        self.tree.tag_configure('emergency_stop', foreground='#E74C3C')
        self.tree.tag_configure('safety_violation', foreground='#E67E22')
        self.tree.tag_configure('error', foreground='#C0392B')

        # ---- Bottom section: Email configuration ----
        email_frame = ttk.LabelFrame(main_frame, text=t("Email Reports"), padding="10")
        email_frame.pack(fill=tk.X, pady=(5, 0))

        # SMTP settings row
        smtp_row = ttk.Frame(email_frame)
        smtp_row.pack(fill=tk.X, pady=2)

        ttk.Label(smtp_row, text=t("SMTP Server:"), width=14, anchor="e").grid(row=0, column=5, padx=2)
        self.smtp_server_var = tk.StringVar()
        ttk.Entry(smtp_row, textvariable=self.smtp_server_var, width=20).grid(row=0, column=4, padx=2)

        ttk.Label(smtp_row, text=t("Port:"), anchor="e").grid(row=0, column=3, padx=2)
        self.smtp_port_var = tk.StringVar()
        ttk.Entry(smtp_row, textvariable=self.smtp_port_var, width=6).grid(row=0, column=2, padx=2)

        self.smtp_tls_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(smtp_row, text="TLS", variable=self.smtp_tls_var).grid(row=0, column=1, padx=5)

        ttk.Label(smtp_row, text=t("Username:"), anchor="e").grid(row=0, column=0, padx=2)
        # Next row for username value
        ttk.Label(smtp_row, text=t("Username:"), anchor="e").grid(row=1, column=5, padx=2)
        self.smtp_username_var = tk.StringVar()
        ttk.Entry(smtp_row, textvariable=self.smtp_username_var, width=20).grid(row=1, column=4, padx=2)

        ttk.Label(smtp_row, text=t("Password:"), anchor="e").grid(row=1, column=3, padx=2)
        self.smtp_password_var = tk.StringVar()
        ttk.Entry(smtp_row, textvariable=self.smtp_password_var, width=15, show="*").grid(row=1, column=2, padx=2)

        # Remove the duplicate label at (0,0) and set up sender/recipient
        smtp_row.grid_columnconfigure(4, weight=1)

        # Sender/Recipient row
        addr_row = ttk.Frame(email_frame)
        addr_row.pack(fill=tk.X, pady=2)

        ttk.Label(addr_row, text=t("Sender Email:"), width=14, anchor="e").pack(side=tk.RIGHT, padx=2)
        self.sender_email_var = tk.StringVar()
        ttk.Entry(addr_row, textvariable=self.sender_email_var, width=25).pack(side=tk.RIGHT, padx=2)

        ttk.Label(addr_row, text=t("Recipient Email:"), anchor="e").pack(side=tk.RIGHT, padx=(10, 2))
        self.recipient_email_var = tk.StringVar()
        ttk.Entry(addr_row, textvariable=self.recipient_email_var, width=25).pack(side=tk.RIGHT, padx=2)

        ttk.Label(addr_row, text=t("Subject Prefix:"), anchor="e").pack(side=tk.RIGHT, padx=(10, 2))
        self.subject_prefix_var = tk.StringVar()
        ttk.Entry(addr_row, textvariable=self.subject_prefix_var, width=25).pack(side=tk.RIGHT, padx=2)

        # Schedule row 1: checkboxes + frequency
        schedule_row = ttk.Frame(email_frame)
        schedule_row.pack(fill=tk.X, pady=2)

        self.email_enabled_var = tk.BooleanVar()
        ttk.Checkbutton(schedule_row, text=t("Enable Email"),
                        variable=self.email_enabled_var).pack(side=tk.RIGHT, padx=5)

        self.schedule_enabled_var = tk.BooleanVar()
        ttk.Checkbutton(schedule_row, text=t("Schedule Enabled"),
                        variable=self.schedule_enabled_var).pack(side=tk.RIGHT, padx=5)

        ttk.Label(schedule_row, text=t("Frequency:"), anchor="e").pack(side=tk.RIGHT, padx=(10, 2))
        self.schedule_frequency_var = tk.StringVar(value='daily')
        freq_combo = ttk.Combobox(schedule_row, textvariable=self.schedule_frequency_var,
                                  values=['daily', 'weekly', 'monthly'],
                                  state='readonly', width=8)
        freq_combo.pack(side=tk.RIGHT, padx=2)
        freq_combo.bind('<<ComboboxSelected>>', self._on_frequency_changed)

        ttk.Label(schedule_row, text=t("Send Time (HH:MM):"), anchor="e").pack(side=tk.RIGHT, padx=(10, 2))
        self.schedule_time_var = tk.StringVar()
        ttk.Entry(schedule_row, textvariable=self.schedule_time_var, width=6).pack(side=tk.RIGHT, padx=2)

        # Schedule row 2: day-of-week / day-of-month selectors
        self.schedule_day_row = ttk.Frame(email_frame)
        self.schedule_day_row.pack(fill=tk.X, pady=2)

        # Day of week (for weekly)
        self.dow_frame = ttk.Frame(self.schedule_day_row)
        ttk.Label(self.dow_frame, text=t("Day of Week:"), anchor="e").pack(side=tk.RIGHT, padx=(10, 2))
        self.schedule_dow_var = tk.StringVar(value='0')
        dow_values = [
            ('0', t('Monday')), ('1', t('Tuesday')), ('2', t('Wednesday')),
            ('3', t('Thursday')), ('4', t('Friday')), ('5', t('Saturday')), ('6', t('Sunday')),
        ]
        dow_combo = ttk.Combobox(self.dow_frame, textvariable=self.schedule_dow_var,
                                 values=[f"{v} - {lbl}" for v, lbl in dow_values],
                                 state='readonly', width=16)
        dow_combo.pack(side=tk.RIGHT, padx=2)
        dow_combo.current(0)

        # Day of month (for monthly)
        self.dom_frame = ttk.Frame(self.schedule_day_row)
        ttk.Label(self.dom_frame, text=t("Day of Month:"), anchor="e").pack(side=tk.RIGHT, padx=(10, 2))
        self.schedule_dom_var = tk.StringVar(value='1')
        dom_combo = ttk.Combobox(self.dom_frame, textvariable=self.schedule_dom_var,
                                 values=[str(d) for d in range(1, 29)],
                                 state='readonly', width=4)
        dom_combo.pack(side=tk.RIGHT, padx=2)
        dom_combo.current(0)

        # Show/hide based on initial frequency
        self._on_frequency_changed()

        # Buttons row
        btn_row = ttk.Frame(email_frame)
        btn_row.pack(fill=tk.X, pady=(5, 0))

        ttk.Button(btn_row, text=t("Test Connection"), command=self.test_email_connection).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_row, text=t("Send Report Now"), command=self.send_report_now).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_row, text=t("Save Email Settings"), command=self.save_email_settings).pack(side=tk.LEFT, padx=5)

        self.last_sent_label = ttk.Label(btn_row, text=t("Last sent: Never"), font=("Arial", 9))
        self.last_sent_label.pack(side=tk.RIGHT, padx=10)

        self.email_status_label = ttk.Label(btn_row, text="", font=("Arial", 9))
        self.email_status_label.pack(side=tk.RIGHT, padx=5)

        # Load email settings into UI
        self._load_email_settings()

    def _load_email_settings(self):
        """Load email settings from config into UI fields"""
        settings = self._load_settings()
        email = settings.get('analytics', {}).get('email', {})

        self.email_enabled_var.set(email.get('enabled', False))
        self.smtp_server_var.set(email.get('smtp_server', ''))
        self.smtp_port_var.set(str(email.get('smtp_port', 587)))
        self.smtp_tls_var.set(email.get('smtp_use_tls', True))
        self.smtp_username_var.set(email.get('smtp_username', ''))
        self.smtp_password_var.set(email.get('smtp_password', ''))
        self.sender_email_var.set(email.get('sender_email', ''))
        self.recipient_email_var.set(email.get('recipient_email', ''))
        self.subject_prefix_var.set(email.get('subject_prefix', 'Scratch-Desk Analytics Report'))
        self.schedule_enabled_var.set(email.get('schedule_enabled', False))
        self.schedule_frequency_var.set(email.get('schedule_frequency', 'daily'))
        self.schedule_time_var.set(email.get('schedule_time', '08:00'))

        # Day of week: set combo to matching index
        dow = email.get('schedule_day_of_week', 0)
        try:
            self.schedule_dow_var.set(self.dow_frame.winfo_children()[-1]['values'][int(dow)])
        except Exception:
            pass

        # Day of month
        dom = email.get('schedule_day_of_month', 1)
        self.schedule_dom_var.set(str(dom))

        # Show/hide day selectors
        self._on_frequency_changed()

        last_sent = email.get('last_sent', '')
        if last_sent:
            try:
                dt = datetime.fromisoformat(last_sent)
                self.last_sent_label.config(text=t("Last sent: {time}", time=dt.strftime('%Y-%m-%d %H:%M')))
            except (ValueError, TypeError):
                self.last_sent_label.config(text=t("Last sent: {time}", time=last_sent))
        else:
            self.last_sent_label.config(text=t("Last sent: Never"))

    def _on_frequency_changed(self, event=None):
        """Show/hide day-of-week or day-of-month selectors based on frequency"""
        freq = self.schedule_frequency_var.get()

        # Hide both first
        self.dow_frame.pack_forget()
        self.dom_frame.pack_forget()

        if freq == 'weekly':
            self.dow_frame.pack(side=tk.RIGHT, padx=5)
        elif freq == 'monthly':
            self.dom_frame.pack(side=tk.RIGHT, padx=5)
        # 'daily' — neither shown

    def save_email_settings(self):
        """Save email settings from UI to config and update scheduler at runtime"""
        settings = self._load_settings()
        if 'analytics' not in settings:
            settings['analytics'] = {}
        if 'email' not in settings['analytics']:
            settings['analytics']['email'] = {}

        email = settings['analytics']['email']
        email['enabled'] = self.email_enabled_var.get()
        email['smtp_server'] = self.smtp_server_var.get()
        try:
            email['smtp_port'] = int(self.smtp_port_var.get())
        except ValueError:
            email['smtp_port'] = 587
        email['smtp_use_tls'] = self.smtp_tls_var.get()
        email['smtp_username'] = self.smtp_username_var.get()
        email['smtp_password'] = self.smtp_password_var.get()
        email['sender_email'] = self.sender_email_var.get()
        email['recipient_email'] = self.recipient_email_var.get()
        email['subject_prefix'] = self.subject_prefix_var.get()
        email['schedule_enabled'] = self.schedule_enabled_var.get()
        email['schedule_frequency'] = self.schedule_frequency_var.get() or 'daily'
        email['schedule_time'] = self.schedule_time_var.get()

        # Parse day_of_week from combo value like "0 - Monday"
        try:
            dow_val = self.schedule_dow_var.get()
            email['schedule_day_of_week'] = int(dow_val.split(' ')[0])
        except (ValueError, IndexError):
            email['schedule_day_of_week'] = 0

        try:
            email['schedule_day_of_month'] = int(self.schedule_dom_var.get())
        except ValueError:
            email['schedule_day_of_month'] = 1

        self._save_settings(settings)

        # Runtime scheduler update: restart or stop based on new settings
        try:
            from core.email_reporter import get_email_reporter
            reporter = get_email_reporter()
            reporter.stop_scheduler()
            if email['schedule_enabled'] and email['enabled']:
                reporter.start_scheduler()
                self.admin_app.log("INFO", t("Email scheduler started"))
            else:
                self.admin_app.log("INFO", t("Email scheduler stopped"))
        except Exception as e:
            self.admin_app.log("WARNING", f"Scheduler update failed: {e}")

        self.email_status_label.config(text=t("Settings saved"), foreground="green")
        self.admin_app.log("INFO", t("Email settings saved"))

    def test_email_connection(self):
        """Test SMTP connection using current UI values (without saving first)"""
        self.email_status_label.config(text=t("Testing..."), foreground="blue")
        self.parent_frame.update_idletasks()

        import smtplib
        smtp_server = self.smtp_server_var.get().strip()
        smtp_username = self.smtp_username_var.get().strip()
        smtp_password = self.smtp_password_var.get().strip()
        try:
            smtp_port = int(self.smtp_port_var.get())
        except ValueError:
            smtp_port = 587
        smtp_use_tls = self.smtp_tls_var.get()

        if not smtp_server or not smtp_username or not smtp_password:
            self.email_status_label.config(text=t("Fill server, username & password"), foreground="red")
            return

        try:
            server = smtplib.SMTP(smtp_server, smtp_port, timeout=15)
            if smtp_use_tls:
                server.starttls()
            server.login(smtp_username, smtp_password)
            server.quit()
            self.email_status_label.config(text=t("Connection OK!"), foreground="green")
            self.admin_app.log("SUCCESS", t("SMTP connection test passed"))
        except smtplib.SMTPAuthenticationError:
            self.email_status_label.config(text=t("Auth failed - check App Password"), foreground="red")
            self.admin_app.log("ERROR", t("SMTP auth failed - wrong username or App Password"))
        except smtplib.SMTPConnectError:
            self.email_status_label.config(text=t("Cannot connect to server"), foreground="red")
            self.admin_app.log("ERROR", f"Cannot connect to {smtp_server}:{smtp_port}")
        except Exception as e:
            self.email_status_label.config(text=t("Error: {error}", error=str(e)[:50]), foreground="red")
            self.admin_app.log("ERROR", f"SMTP test failed: {e}")

    def send_report_now(self):
        """Send analytics report immediately using the current UI date filter"""
        self.email_status_label.config(text=t("Sending..."), foreground="blue")
        self.parent_frame.update_idletasks()

        try:
            from core.email_reporter import get_email_reporter
            reporter = get_email_reporter()

            # Build period from the date filter the user set in the UI
            date_from, date_to = self._get_filter_dates()
            period = None
            if date_from and date_to:
                period_start = datetime.strptime(date_from, '%Y-%m-%d')
                period_end = datetime.strptime(date_to, '%Y-%m-%d').replace(
                    hour=23, minute=59, second=59
                )
                period = (period_start, period_end)

            success, error = reporter.send_report(period=period)

            if success:
                self.email_status_label.config(text=t("Report sent!"), foreground="green")
                self.admin_app.log("SUCCESS", t("Analytics report sent"))
                self._load_email_settings()
            else:
                self.email_status_label.config(text=t("Failed: {error}", error=error[:50]), foreground="red")
                self.admin_app.log("ERROR", t("Report send failed: {error}", error=error))
        except Exception as e:
            self.email_status_label.config(text=t("Error: {error}", error=str(e)[:50]), foreground="red")

    def load_data(self):
        """Load analytics data from CSV and refresh displays"""
        csv_path = self._get_csv_path()
        self.runs_data = []

        if os.path.exists(csv_path):
            try:
                with open(csv_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        self.runs_data.append(row)
            except Exception as e:
                self.admin_app.log("ERROR", t("Failed to load analytics: {error}", error=str(e)))

        self._apply_filter()
        self._update_summary()
        self._update_table()

    def _get_filter_dates(self):
        """Read date-from and date-to from the spinbox widgets.

        Returns:
            (date_from_str, date_to_str) in YYYY-MM-DD format, or ('', '') if invalid.
        """
        try:
            df = (f"{int(self.from_year_var.get()):04d}-"
                  f"{int(self.from_month_var.get()):02d}-"
                  f"{int(self.from_day_var.get()):02d}")
            # Validate
            datetime.strptime(df, '%Y-%m-%d')
        except (ValueError, TypeError):
            df = ''

        try:
            dt = (f"{int(self.to_year_var.get()):04d}-"
                  f"{int(self.to_month_var.get()):02d}-"
                  f"{int(self.to_day_var.get()):02d}")
            datetime.strptime(dt, '%Y-%m-%d')
        except (ValueError, TypeError):
            dt = ''

        return df, dt

    def _apply_filter(self):
        """Apply date range filter to runs data"""
        date_from, date_to = self._get_filter_dates()

        self.filtered_data = self.runs_data[:]

        if date_from:
            self.filtered_data = [
                r for r in self.filtered_data
                if r.get('timestamp_start', '') >= date_from
            ]

        if date_to:
            date_to_full = date_to + 'T23:59:59'
            self.filtered_data = [
                r for r in self.filtered_data
                if r.get('timestamp_start', '') <= date_to_full
            ]

    def _update_summary(self):
        """Update summary labels from filtered data"""
        data = self.filtered_data
        total = len(data)

        if total == 0:
            for key in self.summary_labels:
                self.summary_labels[key].config(text="-")
            return

        from collections import Counter
        status_counts = Counter(r.get('completion_status', 'unknown') for r in data)

        success_count = status_counts.get('success', 0)
        success_rate = (success_count / total * 100) if total > 0 else 0

        # Average duration
        durations = []
        for r in data:
            try:
                d = float(r.get('duration_seconds', 0))
                if d > 0:
                    durations.append(d)
            except (ValueError, TypeError):
                pass
        avg_duration = sum(durations) / len(durations) if durations else 0

        # Most-run program
        prog_counts = Counter(r.get('program_name', '') for r in data if r.get('program_name'))
        most_run = prog_counts.most_common(1)[0] if prog_counts else ('N/A', 0)

        # Most common safety code
        safety_counts = Counter(r.get('safety_code', '') for r in data if r.get('safety_code'))
        most_safety = safety_counts.most_common(1)[0] if safety_counts else ('N/A', 0)

        self.summary_labels['total_runs'].config(text=str(total))
        self.summary_labels['success_rate'].config(text=f"{success_rate:.1f}%")
        self.summary_labels['success_count'].config(text=str(success_count))
        self.summary_labels['user_stop_count'].config(text=str(status_counts.get('user_stop', 0)))
        self.summary_labels['safety_violation_count'].config(text=str(status_counts.get('safety_violation', 0)))
        self.summary_labels['emergency_stop_count'].config(text=str(status_counts.get('emergency_stop', 0)))
        self.summary_labels['error_count'].config(text=str(status_counts.get('error', 0)))
        self.summary_labels['avg_duration'].config(text=f"{avg_duration:.1f}s")
        self.summary_labels['most_run_program'].config(text=f"{most_run[0]} ({most_run[1]})")
        self.summary_labels['most_common_safety'].config(text=f"{most_safety[0]} ({most_safety[1]})")

    def _update_table(self):
        """Update the treeview table with filtered data"""
        # Clear existing rows
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Insert rows (newest first)
        for row in reversed(self.filtered_data):
            ts = row.get('timestamp_start', '')
            try:
                dt = datetime.fromisoformat(ts)
                display_time = dt.strftime('%Y-%m-%d %H:%M:%S')
            except (ValueError, TypeError):
                display_time = ts

            program = row.get('program_name', '')
            status = row.get('completion_status', '')
            duration = row.get('duration_seconds', '')
            if duration:
                try:
                    duration = f"{float(duration):.1f}s"
                except (ValueError, TypeError):
                    pass

            completed = row.get('completed_steps', '')
            total = row.get('total_steps', '')
            steps = f"{completed}/{total}" if completed and total else ''

            # Info: show error or safety message
            info = ''
            if row.get('error_message'):
                info = row['error_message'][:60]
            elif row.get('safety_message'):
                info = row['safety_message'][:60]
            elif row.get('safety_code'):
                info = row['safety_code']

            tag = status if status in ('success', 'user_stop', 'emergency_stop', 'safety_violation', 'error') else ''

            self.tree.insert('', tk.END,
                           values=(display_time, program, status, duration, steps, info),
                           tags=(tag,),
                           iid=row.get('run_id', ''))

    def show_run_details(self, event):
        """Show full details for a selected run"""
        selection = self.tree.selection()
        if not selection:
            return

        run_id = selection[0]
        # Find the run data
        run = None
        for r in self.filtered_data:
            if r.get('run_id') == run_id:
                run = r
                break

        if not run:
            return

        # Create details popup
        popup = tk.Toplevel(self.parent_frame)
        popup.title(t("Run Details"))
        popup.geometry("500x400")
        popup.transient(self.parent_frame.winfo_toplevel())

        text = tk.Text(popup, font=("Courier", 10), wrap=tk.WORD, bg='white', fg='black')
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Format details
        details = f"Run ID: {run.get('run_id', '')}\n"
        details += f"Start: {run.get('timestamp_start', '')}\n"
        details += f"End: {run.get('timestamp_end', '')}\n"
        details += f"Duration: {run.get('duration_seconds', '')}s\n"
        details += f"\nProgram: {run.get('program_name', '')} (#{run.get('program_number', '')})\n"
        details += f"Status: {run.get('completion_status', '')}\n"
        details += f"Hardware: {run.get('hardware_mode', '')}\n"
        details += f"\nSteps: {run.get('completed_steps', '')}/{run.get('total_steps', '')}\n"
        details += f"Successful: {run.get('successful_steps', '')}\n"
        details += f"Failed: {run.get('failed_steps', '')}\n"
        details += f"\nRepeat Rows: {run.get('repeat_rows', '')}\n"
        details += f"Repeat Lines: {run.get('repeat_lines', '')}\n"

        if run.get('error_message'):
            details += f"\nError: {run.get('error_message', '')}\n"
        if run.get('safety_code'):
            details += f"\nSafety Code: {run.get('safety_code', '')}\n"
        if run.get('safety_message'):
            details += f"Safety Message: {run.get('safety_message', '')}\n"

        text.insert(1.0, details)
        text.config(state=tk.DISABLED)

        ttk.Button(popup, text=t("Close"), command=popup.destroy).pack(pady=5)

    def export_csv(self):
        """Export filtered data to a new CSV file"""
        if not self.filtered_data:
            messagebox.showinfo(t("No Data"), t("No data to export"))
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"analytics_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )

        if not filename:
            return

        try:
            from core.analytics import CSV_COLUMNS
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
                writer.writeheader()
                for row in self.filtered_data:
                    writer.writerow(row)

            self.admin_app.log("SUCCESS", t("Analytics exported to {filename}", filename=filename))
            messagebox.showinfo(t("Success"), t("Data exported to {filename}", filename=filename))
        except Exception as e:
            messagebox.showerror(t("Error"), str(e))

    def clear_data(self):
        """Clear all analytics data"""
        if not messagebox.askyesno(t("Clear Data"),
                                    t("Delete all analytics data? This cannot be undone.")):
            return

        csv_path = self._get_csv_path()
        if os.path.exists(csv_path):
            try:
                from core.analytics import CSV_COLUMNS
                with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(CSV_COLUMNS)
                self.admin_app.log("INFO", t("Analytics data cleared"))
            except Exception as e:
                messagebox.showerror(t("Error"), str(e))
                return

        self.load_data()
