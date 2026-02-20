#!/usr/bin/env python3
"""
Analytics Data Collector for Scratch-Desk CNC
==============================================

Collects execution run data and persists to CSV.
Hooks into the execution engine's status callback chain
without modifying the engine itself.

Usage:
    from core.analytics import get_analytics_collector
    collector = get_analytics_collector()
    collector.attach_to_engine(engine, program)
"""

import csv
import json
import os
import threading
import time
import uuid
from datetime import datetime

from core.logger import get_logger


def _load_settings():
    """Load settings from config/settings.json"""
    try:
        with open('config/settings.json', 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


_collector_instance = None
_collector_lock = threading.Lock()


def get_analytics_collector():
    """Get singleton AnalyticsCollector instance"""
    global _collector_instance
    if _collector_instance is None:
        with _collector_lock:
            if _collector_instance is None:
                _collector_instance = AnalyticsCollector()
    return _collector_instance


CSV_COLUMNS = [
    'run_id',
    'timestamp_start',
    'timestamp_end',
    'duration_seconds',
    'program_number',
    'program_name',
    'completion_status',
    'total_steps',
    'completed_steps',
    'successful_steps',
    'failed_steps',
    'error_message',
    'safety_code',
    'safety_message',
    'hardware_mode',
    'repeat_rows',
    'repeat_lines',
]


class AnalyticsCollector:
    """Collects execution analytics and writes to CSV"""

    def __init__(self):
        self.logger = get_logger()
        self._lock = threading.Lock()

        # Current run tracking
        self._run_id = None
        self._start_time = None
        self._engine = None
        self._program = None
        self._original_callback = None
        self._completion_status = None
        self._error_message = ''
        self._safety_code = ''
        self._safety_message = ''
        self._finalized = False

    def _get_settings(self):
        """Get analytics settings"""
        settings = _load_settings()
        return settings.get('analytics', {})

    def _get_csv_path(self):
        """Get CSV file path from settings"""
        analytics_settings = self._get_settings()
        return analytics_settings.get('csv_file_path', 'data/analytics/runs.csv')

    def _is_enabled(self):
        """Check if analytics collection is enabled"""
        analytics_settings = self._get_settings()
        return analytics_settings.get('enabled', True)

    def _ensure_csv_exists(self):
        """Create CSV file with headers if it doesn't exist"""
        csv_path = self._get_csv_path()
        csv_dir = os.path.dirname(csv_path)

        if csv_dir and not os.path.exists(csv_dir):
            os.makedirs(csv_dir, exist_ok=True)

        if not os.path.exists(csv_path):
            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(CSV_COLUMNS)
            self.logger.info(f"Created analytics CSV: {csv_path}", category="execution")

    def attach_to_engine(self, engine, program):
        """Attach collector to an execution engine for the upcoming run.

        Wraps the engine's existing status_callback so the collector
        intercepts status events, records data, then forwards to the
        original callback. Zero changes needed in ExecutionEngine.

        Args:
            engine: ExecutionEngine instance
            program: ScratchDeskProgram instance for this run
        """
        if not self._is_enabled():
            return

        with self._lock:
            self._engine = engine
            self._program = program
            self._run_id = str(uuid.uuid4())
            self._start_time = None
            self._completion_status = None
            self._error_message = ''
            self._safety_code = ''
            self._safety_message = ''
            self._finalized = False

            # Save original callback and insert ourselves in the chain
            self._original_callback = engine.status_callback
            engine.status_callback = self._on_status

            self.logger.debug(f"Analytics collector attached for run {self._run_id[:8]}", category="execution")

    def _on_status(self, status, info=None):
        """Intercept status callback, record data, forward to original"""
        # Capture callback ref BEFORE processing (_finalize_run clears self._original_callback)
        original_callback = self._original_callback
        try:
            self._process_status(status, info)
        except Exception as e:
            self.logger.warning(f"Analytics processing error: {e}", category="execution")

        # Forward using local ref (survives _finalize_run clearing the instance var)
        if original_callback:
            original_callback(status, info)

    def _process_status(self, status, info):
        """Process a status event for analytics"""
        if status == 'started':
            self._start_time = time.time()

        elif status == 'completed':
            self._completion_status = 'success'
            self._finalize_run()

        elif status == 'stopped':
            if self._completion_status is None:
                self._completion_status = 'user_stop'
            self._finalize_run()

        elif status == 'emergency_stop':
            self._completion_status = 'emergency_stop'
            if info:
                self._safety_code = info.get('safety_code', '')
                self._safety_message = info.get('violation_message', '')
            self._finalize_run()

        elif status == 'safety_violation':
            self._completion_status = 'safety_violation'
            if info:
                self._safety_code = info.get('safety_code', '')
                self._safety_message = info.get('violation_message', '')

        elif status == 'error':
            self._completion_status = 'error'
            if info:
                self._error_message = info.get('error', '')
            self._finalize_run()

    def _finalize_run(self):
        """Write the completed run data to CSV"""
        with self._lock:
            if self._finalized:
                return
            self._finalized = True

            if not self._run_id or not self._start_time:
                return

            try:
                self._ensure_csv_exists()

                end_time = time.time()
                duration = end_time - self._start_time

                # Get execution summary from engine
                summary = None
                if self._engine:
                    summary = self._engine.get_execution_summary()

                total_steps = 0
                completed_steps = 0
                successful_steps = 0
                failed_steps = 0

                if summary:
                    total_steps = summary.get('total_steps', 0)
                    completed_steps = summary.get('completed_steps', 0)
                    successful_steps = summary.get('successful_steps', 0)
                    failed_steps = summary.get('failed_steps', 0)
                elif self._engine:
                    total_steps = len(self._engine.steps)
                    completed_steps = len(self._engine.step_results)

                # Determine hardware mode from settings + runtime check
                hardware_mode = 'mock'
                try:
                    settings = _load_settings()
                    if settings.get('hardware_config', {}).get('use_real_hardware', False):
                        hardware_mode = 'real'
                except Exception:
                    pass
                # Also verify via runtime type if possible
                try:
                    from hardware.implementations.real.real_hardware import RealHardware
                    if self._engine and isinstance(self._engine.hardware, RealHardware):
                        hardware_mode = 'real'
                except ImportError:
                    pass

                # If program didn't complete all steps and status is not already
                # set to an error/stop status, mark as 'error' (unexpected stop)
                if (self._completion_status == 'success'
                        and total_steps > 0
                        and completed_steps < total_steps):
                    self._completion_status = 'error'
                    self._error_message = (
                        self._error_message or
                        f'התוכנית הופסקה באמצע - בוצעו {completed_steps} מתוך {total_steps} צעדים'
                    )

                # Program info
                program_number = ''
                program_name = ''
                repeat_rows = ''
                repeat_lines = ''
                if self._program:
                    program_number = getattr(self._program, 'program_number', '')
                    program_name = getattr(self._program, 'program_name', '')
                    repeat_rows = getattr(self._program, 'repeat_rows', '')
                    repeat_lines = getattr(self._program, 'repeat_lines', '')

                row = {
                    'run_id': self._run_id,
                    'timestamp_start': datetime.fromtimestamp(self._start_time).isoformat(),
                    'timestamp_end': datetime.fromtimestamp(end_time).isoformat(),
                    'duration_seconds': round(duration, 2),
                    'program_number': program_number,
                    'program_name': program_name,
                    'completion_status': self._completion_status or 'unknown',
                    'total_steps': total_steps,
                    'completed_steps': completed_steps,
                    'successful_steps': successful_steps,
                    'failed_steps': failed_steps,
                    'error_message': self._error_message,
                    'safety_code': self._safety_code,
                    'safety_message': self._safety_message,
                    'hardware_mode': hardware_mode,
                    'repeat_rows': repeat_rows,
                    'repeat_lines': repeat_lines,
                }

                csv_path = self._get_csv_path()
                with open(csv_path, 'a', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
                    writer.writerow(row)

                self.logger.info(
                    f"Analytics: Run {self._run_id[:8]} recorded - "
                    f"status={self._completion_status}, "
                    f"steps={completed_steps}/{total_steps}, "
                    f"duration={duration:.1f}s",
                    category="execution"
                )

            except Exception as e:
                self.logger.warning(f"Failed to write analytics: {e}", category="execution")

            finally:
                # Restore original callback on engine
                if self._engine and self._engine.status_callback == self._on_status:
                    self._engine.status_callback = self._original_callback

                # Clear references
                self._engine = None
                self._program = None
                self._original_callback = None
