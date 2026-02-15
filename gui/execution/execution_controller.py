import threading
import time
import tkinter as tk
from core.logger import get_logger
from core.translations import t, rtl


# Reason-type styling for safety modals
REASON_STYLE = {
    "operational": {
        "icon": "\u2699\ufe0f",
        "title_he": "\u05ea\u05e0\u05d0\u05d9 \u05ea\u05e4\u05e2\u05d5\u05dc\u05d9",
        "bg": "#2d1a00",
        "accent": "#ff9900",
        "btn_color": "#cc7700",
    },
    "collision": {
        "icon": "\ud83d\udea8",
        "title_he": "\u05e1\u05db\u05e0\u05ea \u05d4\u05ea\u05e0\u05d2\u05e9\u05d5\u05ea!",
        "bg": "#2d0000",
        "accent": "#ff3333",
        "btn_color": "#cc0000",
    },
    "mechanical": {
        "icon": "\u26a0\ufe0f",
        "title_he": "\u05e1\u05db\u05e0\u05ea \u05e0\u05d6\u05e7 \u05de\u05db\u05e0\u05d9",
        "bg": "#1a002d",
        "accent": "#cc66ff",
        "btn_color": "#9933cc",
    },
}

REASON_FALLBACK = {
    "icon": "\ud83d\udea8",
    "title_he": "\u05d4\u05e4\u05e8\u05ea \u05d1\u05d8\u05d9\u05d7\u05d5\u05ea",
    "bg": "#2d0000",
    "accent": "#ff3333",
    "btn_color": "#cc0000",
}


class ExecutionController:
    """Handles execution control and status updates"""

    def __init__(self, main_app):
        self.main_app = main_app
        self.safety_modal = None
        self.transition_modal = None
        self.logger = get_logger()

    def cleanup_for_reset(self):
        """Clean up controller state during system reset"""
        # Destroy any open safety modal
        if self.safety_modal:
            try:
                self.safety_modal.destroy()
            except Exception:
                pass
            self.safety_modal = None

        # Destroy any open transition modal
        if self.transition_modal:
            try:
                self.transition_modal.destroy()
            except Exception:
                pass
            self.transition_modal = None

        # Clear inline safety error
        self._clear_inline_safety_error()

        self.logger.debug("ExecutionController cleaned up for reset", category="gui")

    def on_execution_status(self, status, info=None):
        """Handle execution status updates (called from execution thread).
        Marshals all GUI updates to the main thread via root.after() for thread safety.
        """
        try:
            self.main_app.root.after(0, lambda s=status, i=info: self._on_execution_status_impl(s, i))
        except Exception as e:
            self.logger.error(f"Failed to marshal status update to main thread: {e}", category="gui")

    def _on_execution_status_impl(self, status, info=None):
        """Actual execution status handler - runs on main thread via root.after()"""
        # Ensure panel unlock for terminal states, even if GUI updates below fail
        if status in ('completed', 'stopped', 'error'):
            try:
                if status == 'completed' and hasattr(self.main_app, 'controls_panel'):
                    self.main_app.controls_panel.auto_reload_after_completion()
                elif hasattr(self.main_app, 'controls_panel'):
                    # For stopped/error: reset engine and prepare for fresh run
                    self.main_app.controls_panel._prepare_for_new_run()
                elif hasattr(self.main_app, 'program_panel'):
                    self.main_app.program_panel.set_locked(False)
            except Exception as e:
                self.logger.error(f"Failed to unlock panel: {e}", category="gui")
            finally:
                # Fail-safe: ALWAYS unlock program panel for terminal states
                if hasattr(self.main_app, 'program_panel'):
                    self.main_app.program_panel.set_locked(False)
            return  # Terminal states fully handled above

        if hasattr(self.main_app, 'progress_label'):
            if status == 'running':
                self.main_app.progress_label.config(text=t("Execution Running..."), fg='green')
            elif status == 'paused':
                self.main_app.progress_label.config(text=t("Execution Paused"), fg='orange')
            elif status == 'stopped':
                self.main_app.progress_label.config(text=t("Execution Stopped"), fg='red')
            elif status == 'completed':
                self.main_app.progress_label.config(text=t("Program Completed Successfully!"), fg='green')
            elif status == 'error':
                error_msg = info.get('message', t('Unknown error')) if info else t('Unknown error')
                self.main_app.progress_label.config(text=t("Error: {error_msg}", error_msg=error_msg), fg='red')

        # Update operation label if available
        if hasattr(self.main_app, 'operation_label'):
            if status == 'running':
                # Clear any inline safety error when resuming
                self._clear_inline_safety_error()
                # Reset operation label when resuming (e.g., after safety wait)
                self.main_app.operation_label.config(text=t("Running..."), fg='green')
            elif status == 'step_executing':
                # Get English description for internal processing
                step_info = info.get('description', t('Executing step...')) if info else t('Executing step...')
                # Get Hebrew description for UI display (apply RTL formatting)
                step_info_ui = rtl(info.get('hebDescription', step_info)) if info else t('Executing step...')
                self.main_app.operation_label.config(text=step_info_ui, fg='green')

                # Detect motor operation mode but DON'T track colors yet (wait for completion)
                if hasattr(self.main_app, 'canvas_manager') and info:
                    # Detect motor operation mode from step description (use English for pattern matching)
                    self.main_app.canvas_manager.detect_operation_mode_from_step(step_info)

                    # Force immediate position update for all move operations
                    if 'move' in step_info.lower():
                        self.logger.debug(f" MOVE DETECTED - Forcing position update: {step_info}", category="gui")
                        # ALWAYS clear sensor override when starting a move operation
                        if hasattr(self.main_app.canvas_manager, 'sensor_override_active') and self.main_app.canvas_manager.sensor_override_active:
                            self.logger.debug(f" Clearing sensor override before move", category="gui")
                            self.main_app.canvas_manager.sensor_override_active = False
                            # Cancel any pending sensor override timer
                            if hasattr(self.main_app.canvas_manager, 'sensor_override_timer') and self.main_app.canvas_manager.sensor_override_timer:
                                self.main_app.root.after_cancel(self.main_app.canvas_manager.sensor_override_timer)
                                self.main_app.canvas_manager.sensor_override_timer = None
                        # Force multiple position updates to ensure canvas refreshes
                        self.main_app.canvas_manager.update_position_display()
                        self.main_app.canvas_manager.canvas_position.update_position_display()
                        self.logger.debug(f" Position display updated for move operation", category="gui")

            elif status == 'step_completed':
                # Force position update after each step completion for all position-related operations
                if hasattr(self.main_app, 'canvas_manager') and info:
                    step_info = info.get('description', '')

                    # Detect motor operation mode from completed step
                    self.main_app.canvas_manager.detect_operation_mode_from_step(step_info)

                    # Track operation colors AFTER step completes (user has triggered sensor)
                    self.main_app.canvas_manager.track_operation_from_step(step_info)

                    # Force position update for move operations
                    if 'move' in step_info.lower():
                        self.logger.info(f" MOVE COMPLETED - Forcing position update: {step_info}", category="gui")
                        self.main_app.canvas_manager.update_position_display()
                        if hasattr(self.main_app.canvas_manager, 'canvas_position'):
                            self.main_app.canvas_manager.canvas_position.update_position_display()
                        self.logger.debug(f" Position display updated after move completion", category="gui")
                    # Update for sensor operations that might change position
                    elif any(keyword in step_info.lower() for keyword in ['init', 'sensor', 'cut', 'mark']):
                        self.main_app.canvas_manager.update_position_display()

                    # Update tool status indicators for tool actions
                    if any(keyword in step_info.lower() for keyword in ['line marker', 'line cutter', 'row marker', 'row cutter']):
                        self.main_app.canvas_manager.update_tool_status_from_step(step_info)

                    # Special handling for line completion - ensure automatic move to next line
                    if 'close line marker' in step_info.lower() and 'lines' in step_info.lower():
                        self.logger.info(f" LINE MARKING COMPLETED: {step_info}", category="gui")
                        self.logger.debug(f" Current step: {self.main_app.execution_engine.current_step_index}/{len(self.main_app.steps)}", category="gui")

                        # Check what the next step is
                        if (self.main_app.execution_engine.current_step_index < len(self.main_app.steps)):
                            next_step = self.main_app.steps[self.main_app.execution_engine.current_step_index]
                            self.logger.debug(f" Next step: {next_step.get('operation', 'unknown')} - {next_step.get('description', 'no description')}", category="gui")

                            # If next step is a move operation, it should execute automatically
                            if next_step.get('operation') == 'move_y':
                                self.logger.debug(f" Next step is Y movement - will execute automatically", category="gui")
                                self.logger.info(f" Line marking sequence complete - ready for automatic move to next line", category="gui")

                        # Force position update to ensure we're ready for the next move
                        self.main_app.canvas_manager.update_position_display()

            elif status == 'waiting_sensor':
                # Get sensor name and translate it to Hebrew
                sensor_name = info.get('sensor', 'sensor') if info else 'sensor'
                sensor_name_hebrew = t(sensor_name)  # Translate sensor name (e.g., "y_top" -> "Y עליון")
                self.main_app.operation_label.config(text=t("Waiting for {sensor} sensor", sensor=sensor_name_hebrew), fg='orange')
            elif status == 'transition_alert':
                from_op = t(info.get('from_operation', 'lines').title()) if info else t('Lines')
                to_op = t(info.get('to_operation', 'rows').title()) if info else t('Rows')
                self.main_app.operation_label.config(
                    text=t("\u23f8\ufe0f  Waiting: {from_op} \u2192 {to_op} transition", from_op=from_op, to_op=to_op),
                    fg='orange'
                )
            elif status == 'transition_complete':
                self.main_app.operation_label.config(
                    text=t("\u25b6\ufe0f  Rows operations starting..."),
                    fg='green'
                )

        # Update progress bar if available
        if hasattr(self.main_app, 'progress') and hasattr(self.main_app, 'progress_text'):
            if status == 'executing' and info:
                progress = info.get('progress', 0)
                step_index = info.get('step_index', 0)
                total_steps = info.get('total_steps', 1)

                # Update progress bar
                self.main_app.progress['value'] = progress

                # Update progress text
                self.main_app.progress_text.config(text=t("{progress:.1f}% Complete ({step_index}/{total_steps} steps)", progress=progress, step_index=step_index, total_steps=total_steps))

                # Update step display to show current step progress
                if hasattr(self.main_app, 'controls_panel'):
                    self.main_app.controls_panel.update_step_display()

            elif status == 'completed':
                self.main_app.progress['value'] = 100
                self.main_app.progress_text.config(text=t("100% Complete - Success!"))
                # Note: auto_reload_after_completion is called via panel unlock
                # at the top of _on_execution_status_impl

            elif status == 'emergency_stop':
                # EMERGENCY STOP due to safety violation
                current_progress = self.main_app.progress['value']
                self.main_app.progress_text.config(text=t("\ud83d\udea8 EMERGENCY STOP - Safety Violation"), fg='red')

                # Load the rule and show unified safety modal
                safety_code = info.get('safety_code', '') if info else ''
                violation_msg = info.get('violation_message', t('Unknown safety violation')) if info else ''
                rule = self._load_safety_rule(safety_code)
                self._show_safety_modal(rule, safety_code, violation_msg)

                # Show inline emergency stop error on the bottom bar
                self._show_inline_safety_error(violation_msg, safety_code, '', is_waiting=False)

                # Update step display to show emergency stop state
                if hasattr(self.main_app, 'controls_panel'):
                    self.main_app.controls_panel.update_step_display()

                # Update GUI controls to emergency stop state
                if hasattr(self.main_app, 'controls_panel'):
                    # Set emergency stop button states
                    self.main_app.controls_panel.run_btn.config(state='normal', text=t('\ud83d\udd04 RETRY'), bg='orange')
                    self.main_app.controls_panel.pause_btn.config(state='disabled')
                    self.main_app.controls_panel.stop_btn.config(state='disabled')

                    # Show persistent error status in right panel
                    error_message = t("\u26a0\ufe0f  SAFETY VIOLATION: {safety_code}", safety_code=safety_code)
                    if hasattr(self.main_app.controls_panel, 'progress_label'):
                        self.main_app.controls_panel.progress_label.config(
                            text=error_message,
                            fg='red'
                        )

                self.main_app.operation_label.config(text=t("\ud83d\udea8 EMERGENCY STOP - Safety Violation"), fg='red')

            elif status == 'safety_recovered':
                # Safety violation resolved - auto-resuming
                message = info.get('message', t('Safety violation resolved'))
                operation_type = info.get('operation_type', t('operation'))

                # Auto-close the safety modal
                if self.safety_modal:
                    try:
                        self.safety_modal.destroy()
                    except Exception:
                        pass
                    self.safety_modal = None

                # Update progress and status to show recovery
                current_progress = self.main_app.progress['value']
                self.main_app.progress_text.config(
                    text=t("{progress:.1f}% - Safety resolved, resuming...", progress=current_progress),
                    fg='green'
                )

                # Restore run button to normal state
                if hasattr(self.main_app, 'controls_panel'):
                    self.main_app.controls_panel.run_btn.config(
                        state='disabled',
                        text=t('\u25b6 RUN'),
                        bg='darkgreen'
                    )
                    self.main_app.controls_panel.pause_btn.config(state='normal')
                    self.main_app.controls_panel.stop_btn.config(state='normal')

                    # Clear error status from right panel
                    if hasattr(self.main_app.controls_panel, 'progress_label'):
                        self.main_app.controls_panel.progress_label.config(
                            text=t("\u2705 Safety violation resolved - Resuming"),
                            fg='green'
                        )

                # Update operation label
                # Translate operation type to Hebrew for UI display
                operation_type_raw = operation_type.title()
                operation_type_hebrew = t(operation_type_raw) if operation_type_raw else operation_type_raw
                self.main_app.operation_label.config(
                    text=t("\u2705 Safety resolved - {operation_type} execution resuming", operation_type=operation_type_hebrew),
                    fg='green'
                )

                # Clear inline safety error from bottom bar
                self._clear_inline_safety_error()

            elif status == 'transition_alert':
                # Transition from lines to rows - show dialog
                current_progress = self.main_app.progress['value']
                from_op = t(info.get('from_operation', 'lines').title()) if info else t('Lines')
                to_op = t(info.get('to_operation', 'rows').title()) if info else t('Rows')
                self.main_app.progress_text.config(
                    text=t("\u23f8\ufe0f  Waiting: {from_op} \u2192 {to_op} transition", from_op=from_op, to_op=to_op),
                    fg='orange'
                )
                self._show_transition_modal(info)

            elif status == 'transition_complete':
                # Transition complete - door closed, resuming
                current_progress = self.main_app.progress['value']
                self.main_app.progress_text.config(
                    text=t("{progress:.1f}% - Rows motor door CLOSED, resuming...", progress=current_progress),
                    fg='green'
                )
                # Auto-close transition modal
                if self.transition_modal:
                    try:
                        self.transition_modal.destroy()
                    except Exception:
                        pass
                    self.transition_modal = None

            elif status == 'transition_waiting':
                # Still waiting for door - update progress
                current_progress = self.main_app.progress['value']
                self.main_app.progress_text.config(
                    text=t("{progress:.1f}% - Waiting for rows motor door CLOSED", progress=current_progress),
                    fg='orange'
                )

            elif status == 'stopped' or status == 'error':
                # Keep current progress but update text
                current_progress = self.main_app.progress['value']
                self.main_app.progress_text.config(text=t("{progress:.1f}% - Execution stopped", progress=current_progress))

                # Update step display to show stopped state
                if hasattr(self.main_app, 'controls_panel'):
                    self.main_app.controls_panel.update_step_display()

        # Panel unlock is handled at the top of _on_execution_status_impl

        # Handle safety violations
        if status == 'safety_violation':
            self.handle_safety_violation(info)

        # Handle safety waiting (auto-resume when condition clears)
        if status == 'safety_waiting':
            self.handle_safety_waiting(info)

    def handle_safety_waiting(self, info):
        """Handle safety waiting state - show modal and inline error"""
        if not info:
            return

        violation_message = info.get('violation_message', t('Unknown safety violation'))
        safety_code = info.get('safety_code', 'UNKNOWN')
        step = info.get('step', {})
        step_description = rtl(step.get('hebDescription', step.get('description', t('Unknown step'))))

        # Update progress label with safety waiting state
        if hasattr(self.main_app, 'progress_label'):
            self.main_app.progress_label.config(text=t("\u23f8\ufe0f SAFETY - Waiting for condition to clear..."), fg='orange')

        # Update operation label
        if hasattr(self.main_app, 'operation_label'):
            self.main_app.operation_label.config(text=t("SAFETY WAIT - Will auto-resume"), fg='orange')

        # Load the rule and show unified safety modal
        rule = self._load_safety_rule(safety_code)
        self._show_safety_modal(rule, safety_code, violation_message)

        # Show inline safety error on the bottom bar
        self._show_inline_safety_error(violation_message, safety_code, step_description, is_waiting=True)

    def handle_safety_violation(self, info):
        """Handle safety violation - show inline error on main screen"""
        if not info:
            return

        violation_message = info.get('violation_message', t('Unknown safety violation'))
        safety_code = info.get('safety_code', 'UNKNOWN')
        step = info.get('step', {})
        # Use Hebrew description for UI display, fallback to English for compatibility
        step_description = rtl(step.get('hebDescription', step.get('description', t('Unknown step'))))

        # Update progress label with safety violation
        if hasattr(self.main_app, 'progress_label'):
            self.main_app.progress_label.config(text=t("\ud83d\udea8 SAFETY VIOLATION - STOPPED"), fg='red')

        # Update operation label
        if hasattr(self.main_app, 'operation_label'):
            self.main_app.operation_label.config(text=t("SAFETY VIOLATION - Execution Stopped"), fg='red')

        # Show inline safety error on the bottom bar
        self._show_inline_safety_error(violation_message, safety_code, step_description, is_waiting=False)

        # Update GUI to reflect stopped state
        self.update_gui_after_safety_stop()

    def update_gui_after_safety_stop(self):
        """Update GUI components after safety-triggered stop"""
        try:
            # Update execution buttons
            if hasattr(self.main_app, 'run_btn'):
                self.main_app.run_btn.config(state=tk.NORMAL if self.main_app.steps else tk.DISABLED)
            if hasattr(self.main_app, 'pause_btn'):
                self.main_app.pause_btn.config(state=tk.DISABLED)
            if hasattr(self.main_app, 'stop_btn'):
                self.main_app.stop_btn.config(state=tk.DISABLED)

            # Update progress text with safety warning
            if hasattr(self.main_app, 'progress') and hasattr(self.main_app, 'progress_text'):
                current_progress = self.main_app.progress.get('value', 0)
                self.main_app.progress_text.config(
                    text=t("{progress:.1f}% - STOPPED: Safety Violation", progress=current_progress)
                )

        except Exception as e:
            self.logger.error(f"Error updating GUI after safety stop: {e}", category="gui")

    def _load_safety_rule(self, safety_code):
        """Load a safety rule by ID from safety_rules.json"""
        try:
            import json
            import os
            rules_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config', 'safety_rules.json')
            with open(rules_path, 'r', encoding='utf-8') as f:
                rules_data = json.load(f)
            for rule in rules_data.get('rules', []):
                if rule.get('id') == safety_code:
                    return rule
        except Exception as e:
            self.logger.error(f"Error loading safety rule: {e}", category="gui")
        return None

    def _show_safety_modal(self, rule, safety_code, violation_message):
        """Show unified safety modal styled per the rule's reason type.
        Non-modal so user can still interact with hardware buttons.
        Auto-closes on safety_recovered status."""
        try:
            # Close any existing safety modal first
            if self.safety_modal:
                try:
                    self.safety_modal.destroy()
                except Exception:
                    pass
                self.safety_modal = None

            # Determine styling from rule reason
            reason = rule.get('reason', '') if rule else ''
            style = REASON_STYLE.get(reason, REASON_FALLBACK)

            icon = style["icon"]
            reason_title = style["title_he"]
            bg = style["bg"]
            accent = style["accent"]
            btn_color = style["btn_color"]

            # Get Hebrew fields from rule
            if rule:
                rule_name_he = rule.get('name_he', rule.get('name', safety_code))
                rule_message_he = rule.get('message_he', rule.get('message', violation_message))
            else:
                rule_name_he = safety_code
                rule_message_he = violation_message

            # Create dialog
            dialog = tk.Toplevel(self.main_app.root)
            dialog.title(reason_title)
            dialog.configure(bg=bg)

            # Size and center
            dialog_width = 650
            dialog_height = 420
            screen_width = dialog.winfo_screenwidth()
            screen_height = dialog.winfo_screenheight()
            x = (screen_width - dialog_width) // 2
            y = (screen_height - dialog_height) // 2
            dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
            dialog.minsize(dialog_width, dialog_height)
            dialog.resizable(False, False)

            # Non-modal so user can interact with hardware controls
            dialog.transient(self.main_app.root)

            # Main frame
            main_frame = tk.Frame(dialog, bg=bg, padx=30, pady=20)
            main_frame.pack(fill=tk.BOTH, expand=True)

            # 1. Icon + reason title (large, accented)
            tk.Label(
                main_frame,
                text=rtl(f"{icon}  {reason_title}"),
                font=('Arial', 24, 'bold'),
                fg=accent,
                bg=bg
            ).pack(pady=(0, 5))

            # 2. Rule name_he + safety code (smaller)
            code_text = f"{rule_name_he}  [{safety_code}]" if safety_code else rule_name_he
            tk.Label(
                main_frame,
                text=rtl(code_text),
                font=('Arial', 13),
                fg='#cccccc',
                bg=bg
            ).pack(pady=(0, 10))

            # 3. Separator line (accent color)
            tk.Frame(main_frame, bg=accent, height=3).pack(fill=tk.X, pady=(0, 15))

            # 4. Rule message_he (white text)
            tk.Label(
                main_frame,
                text=rtl(rule_message_he),
                font=('Arial', 14),
                fg='white',
                bg=bg,
                wraplength=600,
                justify=tk.RIGHT,
                anchor='e'
            ).pack(pady=(0, 20), fill=tk.X)

            # 5. Green auto-resume note
            tk.Label(
                main_frame,
                text=rtl("\u05d4\u05de\u05e2\u05e8\u05db\u05ea \u05ea\u05de\u05e9\u05d9\u05da \u05d0\u05d5\u05d8\u05d5\u05de\u05d8\u05d9\u05ea \u05db\u05e9\u05d4\u05ea\u05e0\u05d0\u05d9 \u05d9\u05d9\u05e4\u05ea\u05e8"),
                font=('Arial', 13, 'bold'),
                fg='#66cc66',
                bg=bg,
                wraplength=600,
                justify=tk.RIGHT,
                anchor='e'
            ).pack(pady=(0, 25), fill=tk.X)

            # 6. OK button
            tk.Button(
                main_frame,
                text=t("OK"),
                font=('Arial', 16, 'bold'),
                bg=btn_color,
                fg='white',
                activebackground='#333333',
                activeforeground='white',
                command=lambda: self._close_safety_modal_manual(dialog),
                padx=40,
                pady=12
            ).pack()

            # Ensure content fits
            dialog.update_idletasks()

            # Store reference for auto-close
            self.safety_modal = dialog

            dialog.focus_set()

        except Exception as e:
            self.logger.error(f"Error showing safety modal: {e}", category="gui")

    def _close_safety_modal_manual(self, dialog):
        """Handle manual OK click on safety modal"""
        try:
            dialog.destroy()
        except Exception:
            pass
        if self.safety_modal is dialog:
            self.safety_modal = None

    def _show_transition_modal(self, info):
        """Show transition dialog when moving from lines to rows operations.
        Non-modal so user can interact with hardware controls.
        Auto-closes on transition_complete status."""
        try:
            # Close existing transition modal
            if self.transition_modal:
                try:
                    self.transition_modal.destroy()
                except Exception:
                    pass
                self.transition_modal = None

            # Use operational styling (orange)
            style = REASON_STYLE.get("operational", REASON_FALLBACK)
            icon = style["icon"]
            bg = style["bg"]
            accent = style["accent"]
            btn_color = style["btn_color"]

            dialog = tk.Toplevel(self.main_app.root)
            dialog.title(t("Transition to rows operations"))
            dialog.configure(bg=bg)

            # Size and center
            dialog_width = 650
            dialog_height = 420
            screen_width = dialog.winfo_screenwidth()
            screen_height = dialog.winfo_screenheight()
            x = (screen_width - dialog_width) // 2
            y = (screen_height - dialog_height) // 2
            dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
            dialog.minsize(dialog_width, dialog_height)
            dialog.resizable(False, False)

            # Non-modal so user can interact with hardware controls
            dialog.transient(self.main_app.root)

            main_frame = tk.Frame(dialog, bg=bg, padx=30, pady=20)
            main_frame.pack(fill=tk.BOTH, expand=True)

            # Title
            tk.Label(
                main_frame,
                text=rtl(f"{icon}  \u05de\u05e2\u05d1\u05e8 \u05dc\u05e4\u05e2\u05d5\u05dc\u05d5\u05ea \u05e2\u05de\u05d5\u05d3\u05d5\u05ea"),
                font=('Arial', 24, 'bold'),
                fg=accent,
                bg=bg
            ).pack(pady=(0, 5))

            # Subtitle
            tk.Label(
                main_frame,
                text=rtl("\u05e4\u05e2\u05d5\u05dc\u05d5\u05ea \u05d4\u05e9\u05d5\u05e8\u05d5\u05ea \u05d4\u05d5\u05e9\u05dc\u05de\u05d5"),
                font=('Arial', 13),
                fg='#cccccc',
                bg=bg
            ).pack(pady=(0, 10))

            # Separator
            tk.Frame(main_frame, bg=accent, height=3).pack(fill=tk.X, pady=(0, 15))

            # Message (use explicit line breaks - wraplength breaks RTL visual reordering)
            tk.Label(
                main_frame,
                text=rtl("\u05de\u05e0\u05d5\u05e2 \u05d4\u05e2\u05de\u05d5\u05d3\u05d5\u05ea \u05d4\u05d5\u05d6\u05d6 \u05dc\u05de\u05d9\u05e7\u05d5\u05dd \u05d4\u05d4\u05ea\u05d7\u05dc\u05d4.\n\n\u05d0\u05e0\u05d0 \u05e1\u05d2\u05d5\u05e8 \u05d0\u05ea \u05d3\u05dc\u05ea \u05de\u05e0\u05d5\u05e2 \u05d4\u05e2\u05de\u05d5\u05d3\u05d5\u05ea\n\u05db\u05d3\u05d9 \u05dc\u05d4\u05de\u05e9\u05d9\u05da \u05d1\u05e4\u05e2\u05d5\u05dc\u05d5\u05ea \u05e2\u05de\u05d5\u05d3\u05d5\u05ea."),
                font=('Arial', 14),
                fg='white',
                bg=bg,
                justify=tk.RIGHT,
                anchor='e'
            ).pack(pady=(0, 20), fill=tk.X)

            # Auto-resume note (green)
            tk.Label(
                main_frame,
                text=rtl("\u05d4\u05de\u05e2\u05e8\u05db\u05ea \u05ea\u05de\u05e9\u05d9\u05da \u05d0\u05d5\u05d8\u05d5\u05de\u05d8\u05d9\u05ea \u05db\u05e9\u05d4\u05d3\u05dc\u05ea \u05ea\u05d9\u05e1\u05d2\u05e8"),
                font=('Arial', 13, 'bold'),
                fg='#66cc66',
                bg=bg,
                justify=tk.RIGHT,
                anchor='e'
            ).pack(pady=(0, 25), fill=tk.X)

            # OK button
            tk.Button(
                main_frame,
                text=t("OK"),
                font=('Arial', 16, 'bold'),
                bg=btn_color,
                fg='white',
                activebackground='#333333',
                activeforeground='white',
                command=lambda: self._close_transition_modal(dialog),
                padx=40,
                pady=12
            ).pack()

            dialog.update_idletasks()
            self.transition_modal = dialog
            dialog.focus_set()

        except Exception as e:
            self.logger.error(f"Error showing transition modal: {e}", category="gui")

    def _close_transition_modal(self, dialog):
        """Handle manual OK click on transition modal"""
        try:
            dialog.destroy()
        except Exception:
            pass
        if self.transition_modal is dialog:
            self.transition_modal = None

    def _show_inline_safety_error(self, violation_message, safety_code, step_description, is_waiting=False):
        """Show safety error inline on the bottom bar with full Hebrew rule details"""
        try:
            if not hasattr(self.main_app, 'safety_error_label') or not hasattr(self.main_app, 'safety_details_btn'):
                return

            # Look up the full rule to get Hebrew details
            rule = self._load_safety_rule(safety_code)

            if rule:
                rule_name_he = rule.get('name_he', rule.get('name', safety_code))
                rule_message_he = rule.get('message_he', rule.get('message', violation_message))
                # Compact: "name | message" in Hebrew
                error_text = rtl(f"{rule_name_he}  |  {rule_message_he}")
            else:
                error_text = rtl(violation_message)

            # Prefix icon based on state
            if is_waiting:
                error_text = f"\u23f8\ufe0f  {error_text}"
                bg_color = '#fff3cd'
                fg_color = '#856404'
                btn_bg = '#cc7700'
            else:
                error_text = f"\ud83d\udea8  {error_text}"
                bg_color = '#ffcccc'
                fg_color = '#cc0000'
                btn_bg = '#cc0000'

            # Update the inline error label
            self.main_app.safety_error_label.config(
                text=error_text,
                bg=bg_color,
                fg=fg_color
            )

            # Store details for the details button (include full rule)
            self._safety_detail_info = {
                'violation_message': violation_message,
                'safety_code': safety_code,
                'step_description': step_description,
                'is_waiting': is_waiting,
                'rule': rule
            }

            # Configure details button
            self.main_app.safety_details_btn.config(
                bg=btn_bg,
                command=self._show_safety_details_dialog
            )

            # Show the error label and details button in the bottom bar
            self.main_app.safety_error_label.pack(side=tk.RIGHT, padx=(5, 5), fill=tk.X, expand=True)
            self.main_app.safety_details_btn.pack(side=tk.RIGHT, padx=(0, 2))

            # Hide the operation label to make room
            self.main_app.operation_label.pack_forget()

        except Exception as e:
            self.logger.error(f"Error showing inline safety error: {e}", category="gui")

    def _clear_inline_safety_error(self):
        """Clear inline safety error from the bottom bar"""
        try:
            if hasattr(self.main_app, 'safety_error_label'):
                self.main_app.safety_error_label.pack_forget()
            if hasattr(self.main_app, 'safety_details_btn'):
                self.main_app.safety_details_btn.pack_forget()

            # Restore the operation label
            if hasattr(self.main_app, 'operation_label'):
                self.main_app.operation_label.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(0, 5))

        except Exception as e:
            self.logger.error(f"Error clearing inline safety error: {e}", category="gui")

    def _show_safety_details_dialog(self):
        """Show compact safety details dialog when user clicks the Details button"""
        try:
            info = getattr(self, '_safety_detail_info', {})
            safety_code = info.get('safety_code', '')
            is_waiting = info.get('is_waiting', False)
            rule = info.get('rule')

            # Determine styling from rule reason
            reason = rule.get('reason', '') if rule else ''
            style = REASON_STYLE.get(reason, REASON_FALLBACK)
            bg_color = style["bg"]
            accent_color = style["accent"]
            btn_color = style["btn_color"]
            icon = style["icon"]

            # Use Hebrew fields from the rule, fallback to English
            if rule:
                rule_name = rule.get('name_he', rule.get('name', safety_code))
                rule_desc = rule.get('description_he', rule.get('description', ''))
                rule_message = rule.get('message_he', rule.get('message', ''))
                severity = rule.get('severity', '')
            else:
                rule_name = safety_code
                rule_desc = info.get('violation_message', t('Unknown safety violation'))
                rule_message = ''
                severity = ''

            # Create compact dialog
            dialog = tk.Toplevel(self.main_app.root)
            dialog.title(style["title_he"])
            dialog.configure(bg=bg_color)

            dialog_width = 500
            dialog_height = 350
            screen_width = dialog.winfo_screenwidth()
            screen_height = dialog.winfo_screenheight()
            x = (screen_width - dialog_width) // 2
            y = (screen_height - dialog_height) // 2
            dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
            dialog.minsize(dialog_width, dialog_height)
            dialog.resizable(False, False)
            dialog.transient(self.main_app.root)
            dialog.grab_set()

            main_frame = tk.Frame(dialog, bg=bg_color, padx=20, pady=15)
            main_frame.pack(fill=tk.BOTH, expand=True)

            # Title - Hebrew rule name
            tk.Label(main_frame, text=rtl(f"{icon}  {rule_name}"),
                     font=('Arial', 16, 'bold'), fg=accent_color, bg=bg_color).pack(pady=(0, 5))

            # Safety code + severity
            code_text = safety_code
            if severity:
                code_text = f"{safety_code}  ({severity})"
            tk.Label(main_frame, text=code_text, font=('Arial', 10),
                     fg='#999999', bg=bg_color).pack(pady=(0, 8))

            # Separator
            tk.Frame(main_frame, bg=accent_color, height=2).pack(fill=tk.X, pady=(0, 10))

            # Hebrew description
            if rule_desc:
                tk.Label(main_frame, text=rtl(rule_desc), font=('Arial', 12),
                         fg='white', bg=bg_color, wraplength=450,
                         justify=tk.RIGHT, anchor='e').pack(pady=(0, 10), fill=tk.X)

            # Hebrew action message
            if rule_message:
                tk.Label(main_frame, text=rtl(rule_message), font=('Arial', 12, 'bold'),
                         fg='#ffcc00', bg=bg_color, wraplength=450,
                         justify=tk.RIGHT, anchor='e').pack(pady=(0, 10), fill=tk.X)

            # Auto-resume note for waiting state
            if is_waiting:
                tk.Label(main_frame,
                         text=rtl("\u05d4\u05de\u05e2\u05e8\u05db\u05ea \u05ea\u05de\u05e9\u05d9\u05da \u05d0\u05d5\u05d8\u05d5\u05de\u05d8\u05d9\u05ea \u05db\u05e9\u05d4\u05ea\u05e0\u05d0\u05d9 \u05d9\u05d9\u05e4\u05ea\u05e8"),
                         font=('Arial', 10, 'bold'), fg='#66cc66', bg=bg_color,
                         wraplength=450, justify=tk.RIGHT, anchor='e').pack(pady=(0, 10), fill=tk.X)

            # OK button
            tk.Button(main_frame, text=t("OK"), font=('Arial', 14, 'bold'),
                      bg=btn_color, fg='white', activebackground='#333333',
                      command=dialog.destroy, padx=30, pady=8).pack()

            # Ensure content fits
            dialog.update_idletasks()
            dialog.focus_set()

        except Exception as e:
            self.logger.error(f"Error showing safety details dialog: {e}", category="gui")
