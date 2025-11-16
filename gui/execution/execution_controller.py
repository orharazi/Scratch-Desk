import threading
import time
import tkinter as tk
from tkinter import messagebox
from core.logger import get_logger
from core.translations import t


class ExecutionController:
    """Handles execution control and status updates"""
    
    def __init__(self, main_app):
        self.main_app = main_app
        self.transition_dialog = None
        self.logger = get_logger()
    
    def on_execution_status(self, status, info=None):
        """Handle execution status updates"""
        if hasattr(self.main_app, 'progress_label'):
            if status == 'running':
                self.main_app.progress_label.config(text=t("Execution Running..."), fg='green')
            elif status == 'paused':
                self.main_app.progress_label.config(text=t("Execution Paused"), fg='orange')
            elif status == 'stopped':
                self.main_app.progress_label.config(text=t("Execution Stopped"), fg='red')
            elif status == 'completed':
                self.main_app.progress_label.config(text=t("Execution Completed"), fg='blue')
            elif status == 'error':
                error_msg = info.get('message', t('Unknown error')) if info else t('Unknown error')
                self.main_app.progress_label.config(text=t("Error: {error_msg}", error_msg=error_msg), fg='red')
        
        # Update operation label if available
        if hasattr(self.main_app, 'operation_label'):
            if status == 'step_executing':
                # Get English description for internal processing
                step_info = info.get('description', t('Executing step...')) if info else t('Executing step...')
                # Get Hebrew description for UI display
                step_info_ui = info.get('hebDescription', step_info) if info else t('Executing step...')
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
                if hasattr(self.main_app, 'right_panel'):
                    self.main_app.right_panel.update_step_display()
                
            elif status == 'completed':
                self.main_app.progress['value'] = 100
                self.main_app.progress_text.config(text=t("100% Complete - Execution finished"))
                
                # Final step display update
                if hasattr(self.main_app, 'right_panel'):
                    self.main_app.right_panel.update_step_display()
                
            elif status == 'emergency_stop':
                # EMERGENCY STOP due to safety violation
                current_progress = self.main_app.progress['value']
                self.main_app.progress_text.config(text=t("🚨 EMERGENCY STOP - Safety Violation"), fg='red')

                # Show emergency stop dialog
                violation_msg = info.get('violation_message', t('Unknown safety violation'))
                safety_code = info.get('safety_code', '')
                monitor_type = info.get('monitor_type', 'pre_execution')

                import tkinter.messagebox as messagebox
                messagebox.showerror(
                    t("🚨 EMERGENCY STOP - Safety Violation"),
                    t("Execution has been immediately stopped due to a safety violation!\n\n"
                      "Safety Code: {safety_code}\n"
                      "Detection: {monitor_type}\n\n"
                      "Details:\n{violation_msg}\n\n"
                      "⚠️  All motor movement has been halted to prevent damage.\n"
                      "Please correct the safety issue before attempting to continue.",
                      safety_code=safety_code,
                      monitor_type=monitor_type.replace('_', ' ').title(),
                      violation_msg=violation_msg)
                )
                
                # Update step display to show emergency stop state
                if hasattr(self.main_app, 'right_panel'):
                    self.main_app.right_panel.update_step_display()
                    
                # Update GUI controls to emergency stop state
                if hasattr(self.main_app, 'right_panel'):
                    # Set emergency stop button states
                    self.main_app.right_panel.run_btn.config(state='normal', text=t('🔄 RETRY'), bg='orange')
                    self.main_app.right_panel.pause_btn.config(state='disabled')
                    self.main_app.right_panel.stop_btn.config(state='disabled')

                    # Show persistent error status in right panel
                    error_message = t("⚠️  SAFETY VIOLATION: {safety_code}", safety_code=safety_code)
                    if hasattr(self.main_app.right_panel, 'progress_label'):
                        self.main_app.right_panel.progress_label.config(
                            text=error_message, 
                            fg='red'
                        )
                
                self.main_app.operation_label.config(text=t("🚨 EMERGENCY STOP - Safety Violation"), fg='red')
            
            elif status == 'safety_recovered':
                # Safety violation resolved - auto-resuming
                message = info.get('message', t('Safety violation resolved'))
                operation_type = info.get('operation_type', t('operation'))

                # Update progress and status to show recovery
                current_progress = self.main_app.progress['value']
                self.main_app.progress_text.config(
                    text=t("{progress:.1f}% - Safety resolved, resuming...", progress=current_progress),
                    fg='green'
                )

                # Restore run button to normal state
                if hasattr(self.main_app, 'right_panel'):
                    self.main_app.right_panel.run_btn.config(
                        state='disabled',
                        text=t('▶ RUN'),
                        bg='darkgreen'
                    )
                    self.main_app.right_panel.pause_btn.config(state='normal')
                    self.main_app.right_panel.stop_btn.config(state='normal')

                    # Clear error status from right panel
                    if hasattr(self.main_app.right_panel, 'progress_label'):
                        self.main_app.right_panel.progress_label.config(
                            text=t("✅ Safety violation resolved - Resuming"),
                            fg='green'
                        )

                # Update operation label
                self.main_app.operation_label.config(
                    text=t("✅ Safety resolved - {operation_type} execution resuming", operation_type=operation_type.title()),
                    fg='green'
                )
            
            elif status == 'transition_alert':
                # Show auto-dismissing transition alert
                from_op = info.get('from_operation', '').title()
                to_op = info.get('to_operation', '').title()
                message = info.get('message', '')
                
                self.logger.warning(f" TRANSITION ALERT: {from_op} → {to_op}", category="gui")
                self.logger.debug(f" TRANSITION MESSAGE: {message}", category="gui")
                
                # Show non-blocking transition dialog
                self.show_transition_dialog(from_op, to_op, message)
                
                # Update GUI status
                self.main_app.operation_label.config(
                    text=t("⏸️  Waiting: {from_op} → {to_op} transition", from_op=from_op, to_op=to_op),
                    fg='orange'
                )

                # Update progress text
                current_progress = self.main_app.progress['value']
                self.main_app.progress_text.config(
                    text=t("{progress:.1f}% - Waiting for rows motor door CLOSED", progress=current_progress)
                )
            
            elif status == 'transition_waiting':
                # Update dialog with current limit switch status (if dialog exists)
                limit_switch_state = info.get('limit_switch_state', 'up')

                if hasattr(self, 'transition_dialog') and self.transition_dialog:
                    try:
                        self.update_transition_dialog_status(limit_switch_state)
                    except:
                        pass  # Dialog may have been closed
            
            elif status == 'transition_complete':
                # Auto-dismiss the transition dialog
                if hasattr(self, 'transition_dialog') and self.transition_dialog:
                    try:
                        self.logger.debug(" TRANSITION: Auto-closing transition dialog", category="gui")
                        self.transition_dialog.destroy()
                        self.transition_dialog = None
                        self.logger.info(" TRANSITION: Dialog closed successfully", category="gui")
                    except Exception as e:
                        self.logger.error(f" Error closing transition dialog: {e}", category="gui")
                
                # Update GUI status to show rows operations starting
                self.main_app.operation_label.config(
                    text=t("▶️  Rows operations starting..."),
                    fg='blue'
                )

                # Update progress text
                current_progress = self.main_app.progress['value']
                self.main_app.progress_text.config(
                    text=t("{progress:.1f}% - Continuing execution", progress=current_progress)
                )
                
                self.logger.info(" TRANSITION COMPLETE: GUI updated for rows operations", category="gui")
            
            elif status == 'stopped' or status == 'error':
                # Keep current progress but update text
                current_progress = self.main_app.progress['value']
                self.main_app.progress_text.config(text=t("{progress:.1f}% - Execution stopped", progress=current_progress))
                
                # Update step display to show stopped state
                if hasattr(self.main_app, 'right_panel'):
                    self.main_app.right_panel.update_step_display()
        
        # Handle safety violations
        if status == 'safety_violation':
            self.handle_safety_violation(info)
    
    def handle_safety_violation(self, info):
        """Handle safety violation with immediate alerts and execution stop"""
        if not info:
            return

        violation_message = info.get('violation_message', t('Unknown safety violation'))
        safety_code = info.get('safety_code', 'UNKNOWN')
        step = info.get('step', {})
        # Use Hebrew description for UI display, fallback to English for compatibility
        step_description = step.get('hebDescription', step.get('description', t('Unknown step')))

        # Update progress label with safety violation
        if hasattr(self.main_app, 'progress_label'):
            self.main_app.progress_label.config(text=t("🚨 SAFETY VIOLATION - STOPPED"), fg='red')

        # Update operation label
        if hasattr(self.main_app, 'operation_label'):
            self.main_app.operation_label.config(text=t("SAFETY VIOLATION - Execution Stopped"), fg='red')
        
        # Show critical safety alert dialog
        self.show_safety_alert(violation_message, safety_code, step_description)
        
        # Update GUI to reflect stopped state
        self.update_gui_after_safety_stop()
    
    def show_safety_alert(self, violation_message, safety_code, step_description):
        """Show safety violation alert dialog"""
        try:
            # Create detailed alert message
            alert_title = t("🚨 SAFETY VIOLATION - {safety_code}", safety_code=safety_code)

            # Determine the required action based on the safety code
            if "ROWS" in safety_code or "rows" in violation_message.lower():
                required_action = t("Open the rows door (set row marker DOWN) to continue rows operations.")
                error_code = "ROWS_DOOR_CLOSED"
            elif "LINES" in safety_code or "lines" in violation_message.lower():
                required_action = t("Close the rows door (set row marker UP) to continue lines operations.")
                error_code = "LINES_DOOR_OPEN"
            else:
                required_action = t("Check the row marker position and resolve the safety condition.")
                error_code = safety_code

            alert_message = t("""🚨 SAFETY VIOLATION - {error_code}

{violation_message}

REQUIRED ACTION:
{required_action}

The system will remain stopped until you manually address this issue.""",
                            error_code=error_code,
                            violation_message=violation_message,
                            required_action=required_action)

            # Show critical warning dialog
            messagebox.showerror(alert_title, alert_message)
            
            # Log to console as well
            self.logger.debug(f"\n{'='*60}", category="gui")
            self.logger.warning(f"🚨 SAFETY VIOLATION: {safety_code}", category="gui")
            self.logger.debug(f"Step: {step_description}", category="gui")
            self.logger.warning(f"Issue: {violation_message}", category="gui")
            self.logger.debug(f"{'='*60}\n", category="gui")
            
        except Exception as e:
            self.logger.error(f"Error showing safety alert: {e}", category="gui")
            # Fallback to console message
            self.logger.warning(f"\n🚨 SAFETY VIOLATION: {violation_message}", category="gui")
    
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
    
    def show_transition_dialog(self, from_op, to_op, message):
        """Show auto-dismissing transition dialog"""
        import tkinter as tk
        import tkinter.ttk as ttk
        
        # Close any existing transition dialog
        if hasattr(self, 'transition_dialog') and self.transition_dialog:
            try:
                self.transition_dialog.destroy()
            except:
                pass
        
        # Create new transition dialog window
        self.transition_dialog = tk.Toplevel(self.main_app.root)
        self.transition_dialog.title(t("Operation Transition: {from_op} → {to_op}", from_op=from_op, to_op=to_op))
        self.transition_dialog.geometry("450x320")
        self.transition_dialog.resizable(False, False)
        
        # Position dialog to the side so it doesn't block main window completely
        # Get main window position
        main_x = self.main_app.root.winfo_x()
        main_y = self.main_app.root.winfo_y()
        main_width = self.main_app.root.winfo_width()
        
        # Position dialog to the right of main window
        dialog_x = main_x + main_width + 10
        dialog_y = main_y + 100
        
        self.transition_dialog.geometry(f"450x320+{dialog_x}+{dialog_y}")
        
        # Make it non-modal so user can access main window
        self.transition_dialog.transient(self.main_app.root)
        # Removed grab_set() to allow user to interact with main window controls
        
        # Main frame
        main_frame = tk.Frame(self.transition_dialog, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = tk.Label(
            main_frame,
            text=t("🔄 Operation Transition"),
            font=('Arial', 14, 'bold'),
            fg='orange'
        )
        title_label.pack(pady=(0, 10))

        # Transition info
        transition_label = tk.Label(
            main_frame,
            text=t("{from_op} Operations Complete ✅\nPreparing for {to_op} Operations", from_op=from_op, to_op=to_op),
            font=('Arial', 11),
            justify=tk.CENTER
        )
        transition_label.pack(pady=(0, 15))
        
        # Message
        message_label = tk.Label(
            main_frame,
            text=message,
            font=('Arial', 10),
            wraplength=400,
            justify=tk.LEFT
        )
        message_label.pack(pady=(0, 15))
        
        # Status frame
        status_frame = tk.Frame(main_frame, relief=tk.RIDGE, bd=2)
        status_frame.pack(fill=tk.X, pady=(0, 15))
        
        status_title = tk.Label(
            status_frame,
            text=t("Rows Motor Door Limit Switch:"),
            font=('Arial', 10, 'bold'),
            padx=10, pady=5
        )
        status_title.pack()

        # Status label (will be updated in real-time)
        self.transition_limit_switch_label = tk.Label(
            status_frame,
            text=t("Status: OFF (OPEN)"),
            font=('Arial', 9),
            padx=10, pady=2
        )
        self.transition_limit_switch_label.pack()
        
        # Progress indicator
        progress_frame = tk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(
            progress_frame,
            text=t("⏳ Waiting for rows motor door to CLOSE (limit switch ON)..."),
            font=('Arial', 10, 'italic'),
            fg='blue'
        ).pack()

        # Instructions for user
        instructions_label = tk.Label(
            main_frame,
            text=t("💡 You can use the main window controls while this dialog is open.\nUse the 'Toggle Rows Motor Limit Switch' button to close the door (set to ON)."),
            font=('Arial', 9, 'bold'),
            fg='blue',
            wraplength=400,
            justify=tk.CENTER
        )
        instructions_label.pack(pady=(5, 5))

        # Auto-dismiss info
        auto_dismiss_label = tk.Label(
            main_frame,
            text=t("This dialog will automatically close when the motor door is CLOSED (limit switch ON)."),
            font=('Arial', 9, 'italic'),
            fg='gray',
            wraplength=400,
            justify=tk.CENTER
        )
        auto_dismiss_label.pack(pady=(5, 0))
        
        self.logger.debug(f" Transition dialog shown: {from_op} → {to_op}", category="gui")
    
    def update_transition_dialog_status(self, limit_switch_state):
        """Update the transition dialog with current limit switch status"""
        if not hasattr(self, 'transition_dialog') or not self.transition_dialog:
            return

        try:
            # Update status label with current limit switch state
            # limit_switch_state is "down" (ON/CLOSED) or "up" (OFF/OPEN)
            if limit_switch_state == "down":
                status_text = t("Status: ON (CLOSED)")
                status_color = 'green'
            else:
                status_text = t("Status: OFF (OPEN)")
                status_color = 'red'

            self.transition_limit_switch_label.config(
                text=status_text,
                fg=status_color
            )
            
        except Exception as e:
            self.logger.error(f"Error updating transition dialog: {e}", category="gui")
