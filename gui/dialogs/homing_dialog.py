#!/usr/bin/env python3

"""
Homing Progress Dialog
======================

Modal dialog showing the homing sequence progress with step-by-step status.
Based on the pattern from hardware/tools/hardware_test_gui.py
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import json
import time
from typing import Tuple, Optional, Callable
from core.translations import t, t_title, rtl
from core.logger import get_logger

logger = get_logger()


def _load_homing_timeout() -> float:
    """Load homing timeout from settings.json"""
    try:
        with open('config/settings.json', 'r') as f:
            settings = json.load(f)
        return settings.get('hardware_config', {}).get('arduino_grbl', {}).get('homing_timeout', 300.0)
    except Exception:
        return 300.0


class HomingProgressDialog:
    """
    Modal dialog showing homing sequence progress.

    Displays an 8-step homing sequence with real-time status updates:
    1. Apply GRBL configuration
    2. Check door is open
    3. Reset all pistons to default position
    4. Lift line motor pistons
    5. Move Y axis (pre-home clearance)
    6. Run GRBL homing ($H) - with live countdown timer
    7. Reset work coordinates to (0,0)
    8. Lower line motor pistons
    """

    STEPS_TEMPLATE = [
        "1. Apply GRBL configuration",
        "2. Check door is open",
        "3. Reset all pistons to default position",
        "4. Lift line motor pistons",
        "5. Move Y axis (pre-home clearance)",
        "6. Run GRBL homing ($H)",
        "7. Reset work coordinates to (0,0)",
        "8. Lower line motor pistons"
    ]

    def __init__(self, parent: tk.Tk, hardware, on_complete: Optional[Callable] = None):
        """
        Initialize homing dialog.

        Args:
            parent: Parent Tkinter window
            hardware: Hardware interface with perform_complete_homing_sequence method
            on_complete: Optional callback called after homing completes (success, error_msg)
        """
        self.parent = parent
        self.hardware = hardware
        self.on_complete = on_complete
        self.success = False
        self.error_message = ""
        self.dialog: Optional[tk.Toplevel] = None
        self.step_labels = {}
        self.step_status_labels = {}
        self.waiting_label: Optional[ttk.Label] = None

        # Load homing timeout for display in step 6
        self.homing_timeout = _load_homing_timeout()
        self.homing_timeout_int = int(self.homing_timeout)

        # Countdown state for step 6
        self._countdown_active = False
        self._countdown_start_time: Optional[float] = None
        self._countdown_after_id: Optional[str] = None

    def show(self) -> Tuple[bool, str]:
        """
        Show dialog and run homing sequence.

        Returns:
            Tuple of (success: bool, error_message: str)
        """
        self._create_dialog()
        self._start_homing_thread()
        self.dialog.wait_window()  # Block until dialog closes
        return self.success, self.error_message

    def _create_dialog(self):
        """Create the modal dialog UI"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title(t_title("Homing in Progress"))
        self.dialog.geometry("500x450")
        self.dialog.transient(self.parent)
        self.dialog.lift()
        self.dialog.grab_set()  # Make modal - block all other interaction
        self.dialog.protocol("WM_DELETE_WINDOW", lambda: None)  # Prevent closing with X

        # Center the dialog on screen
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - 250
        y = (self.dialog.winfo_screenheight() // 2) - 225
        self.dialog.geometry(f"500x450+{x}+{y}")

        # Title
        title_label = ttk.Label(
            self.dialog,
            text=t("Homing in Progress..."),
            font=("Arial", 14, "bold")
        )
        title_label.pack(pady=15)

        # Frame for steps
        steps_frame = ttk.Frame(self.dialog)
        steps_frame.pack(pady=10, padx=20, fill=tk.BOTH, expand=True)

        # Create step rows with status indicators
        for i, step_text in enumerate(self.STEPS_TEMPLATE, 1):
            step_row = ttk.Frame(steps_frame)
            step_row.pack(fill=tk.X, pady=3)

            # Step text (RTL: text on right side)
            # Step 6 shows the homing timeout countdown
            if i == 6:
                display_text = t("6. Run GRBL homing ($H) (timeout: {timeout} seconds)", timeout=self.homing_timeout_int)
            else:
                display_text = t(step_text)
            text_label = ttk.Label(step_row, text=display_text, font=("Arial", 10))
            text_label.pack(side=tk.RIGHT, padx=5)
            self.step_labels[i] = text_label

            # Status indicator (emoji) (RTL: status on left side)
            status_label = ttk.Label(step_row, text="⏸", font=("Arial", 12), width=3)
            status_label.pack(side=tk.RIGHT)
            self.step_status_labels[i] = status_label

        # Waiting message label (shows door wait, etc.)
        self.waiting_label = ttk.Label(
            steps_frame,
            text="",
            font=("Arial", 10),
            foreground="orange",
            wraplength=450
        )
        self.waiting_label.pack(pady=10)

        # Safety warning frame (hidden by default, shown during safety violations)
        self._safety_frame = tk.Frame(self.dialog, bg='#2d0000', padx=10, pady=8)
        # Not packed yet — shown/hidden by safety_hold / running callbacks

        self._safety_icon_label = tk.Label(
            self._safety_frame,
            text="",
            font=("Arial", 14, "bold"),
            fg='#ff3333',
            bg='#2d0000',
            anchor='e',
            justify=tk.RIGHT
        )
        self._safety_icon_label.pack(fill=tk.X)

        self._safety_msg_label = tk.Label(
            self._safety_frame,
            text="",
            font=("Arial", 11),
            fg='white',
            bg='#2d0000',
            wraplength=460,
            anchor='e',
            justify=tk.RIGHT
        )
        self._safety_msg_label.pack(fill=tk.X, pady=(2, 0))

        self._safety_resume_label = tk.Label(
            self._safety_frame,
            text="",
            font=("Arial", 10, "bold"),
            fg='#66cc66',
            bg='#2d0000',
            anchor='e',
            justify=tk.RIGHT
        )
        self._safety_resume_label.pack(fill=tk.X, pady=(2, 0))

        logger.debug("Homing dialog created", category="gui")

    def _check_homing_safety(self):
        """Safety check callback passed to the homing sequence.
        Called from the homing worker thread during motor movement steps.

        Returns:
            Tuple of (is_safe: bool, violation_info: dict | None)
        """
        try:
            from core.safety_system import safety_system
            violated_rules = safety_system.rules_manager.evaluate_monitor_rules(
                'lines',
                engine_lowered_tools=set(),
                is_setup=False
            )
            if violated_rules:
                primary = violated_rules[0]
                return False, {
                    'message_he': primary.get('message_he', primary.get('message', 'Safety violation')),
                    'name_he': primary.get('name_he', primary.get('name', '')),
                    'id': primary.get('id', '')
                }
        except Exception as e:
            logger.warning(f"Homing safety check error: {e}", category="hardware")
        return True, None

    def _update_step_status(self, step_number: int, step_name: str, status: str, message=None):
        """
        Update step status in UI.

        This is called from the homing thread and must schedule
        UI updates on the main thread.

        Args:
            step_number: Step number (1-8)
            step_name: Name of the step
            status: One of "running", "done", "error", "waiting", "safety_hold"
            message: Optional - string for "waiting", dict for "safety_hold"
        """
        def update_gui():
            if step_number not in self.step_status_labels:
                return

            status_label = self.step_status_labels[step_number]
            text_label = self.step_labels[step_number]

            if status == "running":
                status_label.config(text="⏳", foreground="blue")
                text_label.config(foreground="blue", font=("Arial", 10, "bold"))
                self.waiting_label.config(text="")
                # Hide safety warning on recovery
                self._safety_frame.pack_forget()
                # Start countdown for step 6
                if step_number == 6:
                    self._start_countdown()
            elif status == "done":
                status_label.config(text="✓", foreground="green")
                text_label.config(foreground="green", font=("Arial", 10))
                self.waiting_label.config(text="")
                self._safety_frame.pack_forget()
                # Stop countdown for step 6
                if step_number == 6:
                    self._stop_countdown()
            elif status == "error":
                status_label.config(text="✗", foreground="red")
                text_label.config(foreground="red", font=("Arial", 10, "bold"))
                self.waiting_label.config(text="")
                # Stop countdown for step 6
                if step_number == 6:
                    self._stop_countdown()
            elif status == "waiting":
                status_label.config(text="⏸", foreground="orange")
                text_label.config(foreground="orange", font=("Arial", 10, "bold"))
                if message:
                    self.waiting_label.config(text=f"⚠ {t(message)}")
            elif status == "safety_hold":
                # Safety violation — show red warning
                status_label.config(text="⚠", foreground="red")
                text_label.config(foreground="red")
                # Pause countdown during safety hold
                if step_number == 6:
                    self._stop_countdown()
                # Show safety warning frame with rule details
                if isinstance(message, dict):
                    name_he = message.get('name_he', '')
                    msg_he = message.get('message_he', '')
                else:
                    name_he = ''
                    msg_he = str(message) if message else ''
                self._safety_icon_label.config(text=rtl(f"🚨  {name_he}"))
                self._safety_msg_label.config(text=rtl(msg_he))
                self._safety_resume_label.config(
                    text=rtl("המערכת תמשיך אוטומטית כשהתנאי ייפתר"))
                self._safety_frame.pack(fill=tk.X, padx=10, pady=(0, 5))

        # Schedule GUI update on main thread
        self.parent.after(0, update_gui)

    def _start_countdown(self):
        """Start the live countdown timer for step 6"""
        self._countdown_active = True
        self._countdown_start_time = time.time()
        self._tick_countdown()

    def _stop_countdown(self):
        """Stop the countdown timer"""
        self._countdown_active = False
        if self._countdown_after_id is not None:
            try:
                self.parent.after_cancel(self._countdown_after_id)
            except Exception:
                pass
            self._countdown_after_id = None

    def _tick_countdown(self):
        """Update the countdown label every second"""
        if not self._countdown_active or self._countdown_start_time is None:
            return
        if 6 not in self.step_labels:
            return

        elapsed = time.time() - self._countdown_start_time
        remaining = max(0, self.homing_timeout_int - int(elapsed))

        text_label = self.step_labels[6]
        countdown_text = t("6. Run GRBL homing ($H) (remaining: {remaining} seconds)", remaining=remaining)
        text_label.config(text=countdown_text)

        if remaining > 0 and self._countdown_active:
            self._countdown_after_id = self.parent.after(1000, self._tick_countdown)

    def _start_homing_thread(self):
        """Start the homing sequence in a background thread"""
        def homing_worker():
            try:
                logger.info("Starting homing sequence...", category="hardware")

                # Execute the complete homing sequence with progress and safety callbacks
                self.success, self.error_message = self.hardware.perform_complete_homing_sequence(
                    progress_callback=self._update_step_status,
                    safety_check=self._check_homing_safety
                )

                logger.info(f"Homing sequence completed: success={self.success}", category="hardware")

            except Exception as e:
                self.success = False
                self.error_message = f"Unexpected exception: {str(e)}"
                logger.error(f"Homing sequence error: {self.error_message}", category="hardware")

            # Schedule completion on main thread
            self.parent.after(0, self._finish_homing)

        thread = threading.Thread(target=homing_worker, daemon=True)
        thread.start()
        logger.debug("Homing thread started", category="hardware")

    def _finish_homing(self):
        """Complete the homing sequence and close dialog"""
        # Stop countdown if still running
        self._stop_countdown()

        # Close progress window
        if self.dialog:
            self.dialog.grab_release()
            self.dialog.destroy()
            self.dialog = None

        # Return focus to parent after dialog close
        from gui.wayland_focus import force_focus_return
        force_focus_return(self.parent)

        # Show success message (failure is handled by the caller's retry loop)
        if self.success:
            logger.info("Homing completed successfully", category="hardware")
            messagebox.showinfo(
                t_title("Homing Complete"),
                t("Homing sequence completed successfully!\n\n"
                  "Machine is now at home position (0, 0).")
            )
        else:
            logger.error(f"Homing failed: {self.error_message}", category="hardware")

        # Call completion callback if provided
        if self.on_complete:
            try:
                self.on_complete(self.success, self.error_message)
            except Exception as e:
                logger.error(f"Error in homing completion callback: {e}", category="hardware")


def show_homing_dialog(parent: tk.Tk, hardware) -> Tuple[bool, str]:
    """
    Convenience function to show homing dialog.

    Args:
        parent: Parent Tkinter window
        hardware: Hardware interface

    Returns:
        Tuple of (success: bool, error_message: str)
    """
    dialog = HomingProgressDialog(parent, hardware)
    return dialog.show()
