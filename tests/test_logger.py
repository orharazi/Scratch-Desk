#!/usr/bin/env python3

import pytest
import time
from core.logger import LogLevel, ScratchDeskLogger, get_logger


class TestLogLevel:
    """Test LogLevel constants and conversion"""

    def test_level_values(self):
        """Log level constants should have correct values"""
        assert LogLevel.DEBUG == 0
        assert LogLevel.INFO == 1
        assert LogLevel.WARNING == 2
        assert LogLevel.ERROR == 3
        assert LogLevel.SUCCESS == 4

    def test_from_string(self):
        """Should convert string to log level"""
        assert LogLevel.from_string("DEBUG") == 0
        assert LogLevel.from_string("INFO") == 1
        assert LogLevel.from_string("WARNING") == 2
        assert LogLevel.from_string("ERROR") == 3
        assert LogLevel.from_string("SUCCESS") == 4

    def test_from_string_case_insensitive(self):
        """Should handle case-insensitive conversion"""
        assert LogLevel.from_string("debug") == 0
        assert LogLevel.from_string("Info") == 1
        assert LogLevel.from_string("WARNING") == 2


class TestLoggerInitialization:
    """Test logger initialization and configuration"""

    def test_should_log_respects_level(self, settings_file):
        """Messages below threshold should be filtered"""
        logger = ScratchDeskLogger(settings_file)
        logger.set_log_level("INFO")

        # DEBUG (0) should be filtered when level is INFO (1)
        assert logger._should_log(LogLevel.DEBUG) is False
        # INFO and above should pass
        assert logger._should_log(LogLevel.INFO) is True
        assert logger._should_log(LogLevel.WARNING) is True
        assert logger._should_log(LogLevel.ERROR) is True

    def test_category_specific_level(self, settings_file):
        """Category-specific levels should override global level"""
        logger = ScratchDeskLogger(settings_file)
        logger.set_log_level("WARNING")  # Global level
        logger.set_category_level("hardware", "DEBUG")  # Category level

        # Global level should filter DEBUG
        assert logger._should_log(LogLevel.DEBUG) is False

        # Category level should allow DEBUG for hardware
        assert logger._should_log(LogLevel.DEBUG, category="hardware") is True

    def test_set_log_level_runtime(self, settings_file):
        """Should change log level at runtime"""
        logger = ScratchDeskLogger(settings_file)
        logger.set_log_level("ERROR")
        assert logger.global_level == LogLevel.ERROR

        logger.set_log_level("DEBUG")
        assert logger.global_level == LogLevel.DEBUG


class TestGUICallback:
    """Test GUI callback functionality"""

    def test_gui_callback_called(self, settings_file):
        """GUI callback should receive log messages"""
        logger = ScratchDeskLogger(settings_file)
        # Set log level to INFO to ensure messages pass through
        logger.set_log_level("INFO")
        called = {'count': 0, 'level': None, 'message': None}

        def callback(level, category, message, timestamp):
            called['count'] += 1
            called['level'] = level
            called['message'] = message

        logger.set_gui_callback(callback)
        logger.info("Test message", category="test")
        time.sleep(0.3)  # Let queue processor handle it

        assert called['count'] == 1
        assert called['level'] == LogLevel.INFO
        assert called['message'] == "Test message"

    def test_gui_callback_exception_handled(self, settings_file):
        """Bad GUI callback should not crash logger"""
        logger = ScratchDeskLogger(settings_file)

        def bad_callback(level, category, message, timestamp):
            raise ValueError("Callback error")

        logger.set_gui_callback(bad_callback)
        # Should not raise exception
        logger.info("Test message")
        time.sleep(0.3)


class TestLogMethods:
    """Test log helper methods"""

    def test_log_action(self, settings_file):
        """log_action should format correctly"""
        logger = ScratchDeskLogger(settings_file)
        logger.set_log_level("INFO")
        called = {'message': None}

        def callback(level, category, message, timestamp):
            called['message'] = message

        logger.set_gui_callback(callback)
        logger.log_action("Moving X motor", "to 25cm", category="hardware")
        time.sleep(0.3)

        assert called['message'] is not None
        assert "Moving X motor" in called['message']
        assert "25cm" in called['message']

    def test_log_sensor(self, settings_file):
        """log_sensor should format state correctly"""
        logger = ScratchDeskLogger(settings_file)
        logger.set_log_level("INFO")
        called = {'message': None}

        def callback(level, category, message, timestamp):
            called['message'] = message

        logger.set_gui_callback(callback)
        logger.log_sensor("X LEFT sensor", True, category="hardware")
        time.sleep(0.3)

        assert called['message'] is not None
        assert "X LEFT sensor" in called['message']
        assert "ACTIVE" in called['message']

    def test_log_state_change(self, settings_file):
        """log_state_change should format transition correctly"""
        logger = ScratchDeskLogger(settings_file)
        logger.set_log_level("INFO")
        called = {'message': None}

        def callback(level, category, message, timestamp):
            called['message'] = message

        logger.set_gui_callback(callback)
        logger.log_state_change("Line Marker", "up", "down", category="hardware")
        time.sleep(0.3)

        assert called['message'] is not None
        assert "Line Marker" in called['message']
        assert "up" in called['message']
        assert "down" in called['message']
