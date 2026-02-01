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
from typing import Tuple, Optional, Callable
from core.translations import t
from core.logger import get_logger

logger = get_logger()


class HomingProgressDialog:
    """
    Modal dialog showing homing sequence progress.

    Displays a 6-step homing sequence with real-time status updates:
    1. Apply GRBL configuration
    2. Check door is open
    3. Lift line motor pistons
    4. Run GRBL homing ($H)
    5. Reset work coordinates to (0,0)
    6. Lower line motor pistons
    """

    STEPS = [
        "1. Apply GRBL configuration",
        "2. Check door is open",
        "3. Lift line motor pistons",
        "4. Run GRBL homing ($H)",
        "5. Reset work coordinates to (0,0)",
        "6. Lower line motor pistons"
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
        self.dialog.title(t("Homing in Progress"))
        self.dialog.geometry("500x350")
        self.dialog.transient(self.parent)
        self.dialog.grab_set()  # Make modal - block all other interaction
        self.dialog.protocol("WM_DELETE_WINDOW", lambda: None)  # Prevent closing with X

        # Center the dialog on screen
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - 250
        y = (self.dialog.winfo_screenheight() // 2) - 175
        self.dialog.geometry(f"500x350+{x}+{y}")

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
        for i, step_text in enumerate(self.STEPS, 1):
            step_row = ttk.Frame(steps_frame)
            step_row.pack(fill=tk.X, pady=3)

            # Status indicator (emoji)
            status_label = ttk.Label(step_row, text="⏸", font=("Arial", 12), width=3)
            status_label.pack(side=tk.LEFT)
            self.step_status_labels[i] = status_label

            # Step text
            text_label = ttk.Label(step_row, text=t(step_text), font=("Arial", 10))
            text_label.pack(side=tk.LEFT, padx=5)
            self.step_labels[i] = text_label

        # Waiting message label (shows door wait, etc.)
        self.waiting_label = ttk.Label(
            steps_frame,
            text="",
            font=("Arial", 10),
            foreground="orange",
            wraplength=450
        )
        self.waiting_label.pack(pady=10)

        logger.debug("Homing dialog created", category="gui")

    def _update_step_status(self, step_number: int, step_name: str, status: str, message: Optional[str] = None):
        """
        Update step status in UI.

        This is called from the homing thread and must schedule
        UI updates on the main thread.

        Args:
            step_number: Step number (1-6)
            step_name: Name of the step
            status: One of "running", "done", "error", "waiting"
            message: Optional message (used for "waiting" status)
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
            elif status == "done":
                status_label.config(text="✓", foreground="green")
                text_label.config(foreground="green", font=("Arial", 10))
                self.waiting_label.config(text="")
            elif status == "error":
                status_label.config(text="✗", foreground="red")
                text_label.config(foreground="red", font=("Arial", 10, "bold"))
                self.waiting_label.config(text="")
            elif status == "waiting":
                status_label.config(text="⏸", foreground="orange")
                text_label.config(foreground="orange", font=("Arial", 10, "bold"))
                if message:
                    self.waiting_label.config(text=f"⚠ {message}")

        # Schedule GUI update on main thread
        self.parent.after(0, update_gui)

    def _start_homing_thread(self):
        """Start the homing sequence in a background thread"""
        def homing_worker():
            try:
                logger.info("Starting homing sequence...", category="hardware")

                # Execute the complete homing sequence with progress callback
                self.success, self.error_message = self.hardware.perform_complete_homing_sequence(
                    progress_callback=self._update_step_status
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
        # Close progress window
        if self.dialog:
            self.dialog.grab_release()
            self.dialog.destroy()
            self.dialog = None

        # Show result message
        if not self.success:
            logger.error(f"Homing failed: {self.error_message}", category="hardware")
            messagebox.showerror(
                t("Homing Failed"),
                t("Homing sequence failed!\n\nError: {error}", error=self.error_message)
            )
        else:
            logger.info("Homing completed successfully", category="hardware")
            messagebox.showinfo(
                t("Homing Complete"),
                t("Homing sequence completed successfully!\n\n"
                  "Machine is now at home position (0, 0).")
            )

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
