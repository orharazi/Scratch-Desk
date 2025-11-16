#!/usr/bin/env python3

"""
Centralized Logging System for Scratch Desk
============================================

Thread-safe, configurable logging with support for multiple log levels,
categories, and output targets (console, file, GUI).

Log Levels:
- DEBUG: Internal state, function tracing, detailed flow
- INFO: User actions, movements, sensor triggers, state changes
- WARNING: Non-critical issues, user interventions needed
- ERROR: Critical failures, safety violations, operation failures
- SUCCESS: Successful completion of operations

Usage:
    from core.logger import get_logger

    logger = get_logger()
    logger.info("Moving X motor to 25cm")
    logger.debug("Execution loop: Step 12/50")
    logger.error("Hardware initialization failed")
"""

import json
import threading
import queue
import time
from datetime import datetime
from typing import Optional, Callable, Dict, Any
from pathlib import Path


class LogLevel:
    """Log level constants"""
    DEBUG = 0
    INFO = 1
    WARNING = 2
    ERROR = 3
    SUCCESS = 4  # Special level for successful operations

    NAMES = {
        0: "DEBUG",
        1: "INFO",
        2: "WARNING",
        3: "ERROR",
        4: "SUCCESS"
    }

    ICONS = {
        0: "🔍",  # DEBUG
        1: "ℹ️",   # INFO
        2: "⚠️",   # WARNING
        3: "🚨",  # ERROR
        4: "✅"   # SUCCESS
    }

    # ANSI color codes for terminal output
    COLORS = {
        0: "\033[90m",      # DEBUG - Gray
        1: "\033[97m",      # INFO - White
        2: "\033[93m",      # WARNING - Yellow
        3: "\033[91m",      # ERROR - Red
        4: "\033[92m",      # SUCCESS - Green
        "RESET": "\033[0m"
    }

    @classmethod
    def from_string(cls, level_str: str) -> int:
        """Convert string to log level"""
        level_map = {
            "DEBUG": cls.DEBUG,
            "INFO": cls.INFO,
            "WARNING": cls.WARNING,
            "ERROR": cls.ERROR,
            "SUCCESS": cls.SUCCESS
        }
        return level_map.get(level_str.upper(), cls.INFO)


class ScratchDeskLogger:
    """
    Centralized logger for Scratch Desk application.
    Thread-safe, configurable, with support for multiple output targets.
    """

    _instance: Optional['ScratchDeskLogger'] = None
    _lock = threading.Lock()

    def __init__(self, config_path: str = "config/settings.json"):
        """Initialize logger with configuration"""
        self.config_path = config_path
        self.config = self._load_config()

        # Log level configuration
        self.global_level = LogLevel.from_string(self.config.get("level", "INFO"))
        self.category_levels = self.config.get("categories", {})

        # Output configuration
        self.console_output = self.config.get("console_output", True)
        self.file_output = self.config.get("file_output", False)
        self.file_path = self.config.get("file_path", "logs/scratch_desk.log")

        # Formatting options
        self.show_timestamps = self.config.get("show_timestamps", True)
        self.show_thread_names = self.config.get("show_thread_names", False)
        self.use_colors = self.config.get("use_colors", True)
        self.use_icons = self.config.get("use_icons", True)

        # GUI callback for displaying logs in GUI widgets
        self.gui_callback: Optional[Callable] = None

        # Thread-safe message queue
        self.log_queue = queue.Queue()
        self.processor_running = False
        self.processor_thread: Optional[threading.Thread] = None

        # File handle for log file
        self.log_file = None
        self._setup_file_logging()

        # Start log processor thread
        self.start_processor()

    def _load_config(self) -> Dict[str, Any]:
        """Load logging configuration from settings.json"""
        try:
            with open(self.config_path, 'r') as f:
                settings = json.load(f)
                return settings.get("logging", {
                    "level": "INFO",
                    "show_timestamps": True,
                    "show_thread_names": False,
                    "console_output": True,
                    "file_output": False,
                    "file_path": "logs/scratch_desk.log",
                    "use_colors": True,
                    "use_icons": True,
                    "categories": {
                        "hardware": "INFO",
                        "execution": "INFO",
                        "gui": "WARNING",
                        "grbl": "INFO"
                    }
                })
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            # Return default configuration
            return {
                "level": "INFO",
                "show_timestamps": True,
                "console_output": True,
                "file_output": False,
                "use_colors": True,
                "use_icons": True,
                "categories": {}
            }

    def _setup_file_logging(self):
        """Setup file logging if enabled"""
        if self.file_output:
            try:
                # Create logs directory if it doesn't exist
                log_dir = Path(self.file_path).parent
                log_dir.mkdir(parents=True, exist_ok=True)

                # Open log file in append mode
                self.log_file = open(self.file_path, 'a', encoding='utf-8')
            except Exception as e:
                print(f"Failed to setup file logging: {e}")
                self.file_output = False

    def start_processor(self):
        """Start the log processor thread"""
        if not self.processor_running:
            self.processor_running = True
            self.processor_thread = threading.Thread(
                target=self._process_logs,
                daemon=True,
                name="LogProcessor"
            )
            self.processor_thread.start()

    def stop_processor(self):
        """Stop the log processor thread"""
        self.processor_running = False
        if self.processor_thread:
            self.processor_thread.join(timeout=1.0)
        if self.log_file:
            self.log_file.close()

    def _process_logs(self):
        """Process log messages from queue (runs in background thread)"""
        while self.processor_running:
            try:
                # Get message from queue (block with timeout)
                try:
                    timestamp, level, category, message = self.log_queue.get(timeout=0.1)
                except queue.Empty:
                    continue

                # Format the message
                formatted = self._format_message(timestamp, level, category, message)

                # Output to console
                if self.console_output:
                    print(formatted["console"])

                # Output to file
                if self.file_output and self.log_file:
                    self.log_file.write(formatted["file"] + "\n")
                    self.log_file.flush()

                # Output to GUI callback
                if self.gui_callback:
                    try:
                        self.gui_callback(level, category, message, timestamp)
                    except Exception:
                        pass  # Silently ignore GUI callback errors

                self.log_queue.task_done()

            except Exception as e:
                # Don't let processor thread crash
                print(f"Log processor error: {e}")
                time.sleep(0.1)

    def _format_message(self, timestamp: datetime, level: int, category: str, message: str) -> Dict[str, str]:
        """Format log message for different outputs"""
        level_name = LogLevel.NAMES[level]
        level_icon = LogLevel.ICONS[level] if self.use_icons else ""

        # Build timestamp string
        time_str = ""
        if self.show_timestamps:
            time_str = f"[{timestamp.strftime('%H:%M:%S.%f')[:-3]}] "

        # Build thread name string
        thread_str = ""
        if self.show_thread_names:
            thread_str = f"[{threading.current_thread().name}] "

        # Build category string
        category_str = f"[{category}] " if category else ""

        # Console output (with colors and icons)
        if self.use_colors:
            color = LogLevel.COLORS[level]
            reset = LogLevel.COLORS["RESET"]
            console_msg = f"{time_str}{color}{level_icon} {level_name:7}{reset} {category_str}{message}"
        else:
            console_msg = f"{time_str}{level_icon} {level_name:7} {category_str}{message}"

        # File output (no colors)
        file_msg = f"{time_str}{level_name:7} {category_str}{message}"

        return {
            "console": console_msg,
            "file": file_msg
        }

    def _should_log(self, level: int, category: Optional[str] = None) -> bool:
        """Determine if message should be logged based on level and category"""
        # Check category-specific level first
        if category and category in self.category_levels:
            category_level = LogLevel.from_string(self.category_levels[category])
            return level >= category_level

        # Fall back to global level
        return level >= self.global_level

    def log(self, level: int, message: str, category: Optional[str] = None):
        """
        Log a message at specified level.

        Args:
            level: Log level (use LogLevel constants)
            message: Message to log
            category: Optional category (e.g., "hardware", "execution", "gui")
        """
        if not self._should_log(level, category):
            return

        timestamp = datetime.now()
        self.log_queue.put((timestamp, level, category or "", message))

    def debug(self, message: str, category: Optional[str] = None):
        """Log debug message (internal state, function tracing)"""
        self.log(LogLevel.DEBUG, message, category)

    def info(self, message: str, category: Optional[str] = None):
        """Log info message (user actions, movements, state changes)"""
        self.log(LogLevel.INFO, message, category)

    def warning(self, message: str, category: Optional[str] = None):
        """Log warning message (non-critical issues)"""
        self.log(LogLevel.WARNING, message, category)

    def error(self, message: str, category: Optional[str] = None):
        """Log error message (critical failures)"""
        self.log(LogLevel.ERROR, message, category)

    def success(self, message: str, category: Optional[str] = None):
        """Log success message (successful operation completion)"""
        self.log(LogLevel.SUCCESS, message, category)

    # Helper methods for common operations
    def log_action(self, action: str, details: str = "", category: Optional[str] = None):
        """Log a user action or physical operation"""
        message = f"{action}"
        if details:
            message += f" - {details}"
        self.info(message, category)

    def log_sensor(self, sensor_name: str, state: bool, category: Optional[str] = None):
        """Log sensor state change"""
        state_str = "ACTIVE" if state else "INACTIVE"
        self.info(f"Sensor {sensor_name}: {state_str}", category or "hardware")

    def log_state_change(self, component: str, old_state: str, new_state: str, category: Optional[str] = None):
        """Log component state change"""
        self.info(f"{component}: {old_state} → {new_state}", category)

    def log_hardware_call(self, function_name: str, args: str = "", category: Optional[str] = None):
        """Log hardware function call (DEBUG level)"""
        message = f"Hardware call: {function_name}"
        if args:
            message += f"({args})"
        self.debug(message, category or "hardware")

    def log_execution_step(self, step_num: int, total: int, description: str, category: Optional[str] = None):
        """Log execution step (DEBUG level)"""
        self.debug(f"Step {step_num}/{total}: {description}", category or "execution")

    def set_gui_callback(self, callback: Callable):
        """Set callback function for GUI log display"""
        self.gui_callback = callback

    def set_log_level(self, level: str):
        """Change global log level at runtime"""
        self.global_level = LogLevel.from_string(level)

    def set_category_level(self, category: str, level: str):
        """Set log level for specific category"""
        self.category_levels[category] = level


# Singleton instance
_logger_instance: Optional[ScratchDeskLogger] = None
_logger_lock = threading.Lock()


def get_logger(config_path: str = "config/settings.json") -> ScratchDeskLogger:
    """
    Get singleton logger instance.

    Args:
        config_path: Path to settings.json configuration file

    Returns:
        ScratchDeskLogger instance
    """
    global _logger_instance

    if _logger_instance is None:
        with _logger_lock:
            if _logger_instance is None:
                _logger_instance = ScratchDeskLogger(config_path)

    return _logger_instance


def shutdown_logger():
    """Shutdown the logger (call on application exit)"""
    global _logger_instance

    if _logger_instance:
        _logger_instance.stop_processor()
        _logger_instance = None


# Convenience functions for direct module-level usage
def debug(message: str, category: Optional[str] = None):
    """Log debug message"""
    get_logger().debug(message, category)


def info(message: str, category: Optional[str] = None):
    """Log info message"""
    get_logger().info(message, category)


def warning(message: str, category: Optional[str] = None):
    """Log warning message"""
    get_logger().warning(message, category)


def error(message: str, category: Optional[str] = None):
    """Log error message"""
    get_logger().error(message, category)


def success(message: str, category: Optional[str] = None):
    """Log success message"""
    get_logger().success(message, category)


if __name__ == "__main__":
    # Example usage
    logger = get_logger()

    print("Testing Scratch Desk Logger\n")
    print("=" * 60)

    logger.debug("This is a debug message - internal state details")
    logger.info("Moving X motor to 25.0cm")
    logger.warning("GRBL not available - using mock hardware")
    logger.error("Hardware initialization failed - check connections")
    logger.success("X motor positioned at 25.0cm")

    print("\nWith categories:\n")
    logger.info("Line Marker piston raised", category="hardware")
    logger.debug("Execution loop: Step 12/50", category="execution")
    logger.info("Canvas update complete", category="gui")
    logger.success("GRBL connected on /dev/ttyACM0", category="grbl")

    print("\nHelper methods:\n")
    logger.log_action("Moving to position", "X=25cm, Y=30cm", category="hardware")
    logger.log_sensor("X LEFT sensor", True, category="hardware")
    logger.log_state_change("Line 5", "PENDING", "COMPLETED", category="execution")
    logger.log_hardware_call("move_x", "25.0", category="hardware")
    logger.log_execution_step(12, 50, "move_x - Move to X position 25cm", category="execution")

    # Clean shutdown
    time.sleep(0.5)  # Let processor finish
    shutdown_logger()
