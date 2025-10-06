import threading
import time
import tkinter as tk
from tkinter import messagebox


class ExecutionController:
    """Handles execution control and status updates"""
    
    def __init__(self, main_app):
        self.main_app = main_app
        self.transition_dialog = None
    
    def on_execution_status(self, status, info=None):
        """Handle execution status updates"""
        if hasattr(self.main_app, 'progress_label'):
            if status == 'running':
                self.main_app.progress_label.config(text="Execution Running...", fg='green')
            elif status == 'paused':
                self.main_app.progress_label.config(text="Execution Paused", fg='orange')
            elif status == 'stopped':
                self.main_app.progress_label.config(text="Execution Stopped", fg='red')
            elif status == 'completed':
                self.main_app.progress_label.config(text="Execution Completed", fg='blue')
            elif status == 'error':
                error_msg = info.get('message', 'Unknown error') if info else 'Unknown error'
                self.main_app.progress_label.config(text=f"Error: {error_msg}", fg='red')
        
        # Update operation label if available
        if hasattr(self.main_app, 'operation_label'):
            if status == 'step_executing':
                step_info = info.get('description', 'Executing step...') if info else 'Executing step...'
                self.main_app.operation_label.config(text=step_info, fg='green')
                
                # Track operation from step description for color updates
                if hasattr(self.main_app, 'canvas_manager') and info:
                    # Detect motor operation mode from step description
                    self.main_app.canvas_manager.detect_operation_mode_from_step(step_info)
                    
                    self.main_app.canvas_manager.track_operation_from_step(step_info)
                    # Smart sensor override clearing for move operations
                    if 'move' in step_info.lower():
                        # Only clear sensor override if we're moving on the same axis as the sensor
                        if hasattr(self.main_app.canvas_manager, 'sensor_override_active') and self.main_app.canvas_manager.sensor_override_active:
                            self.main_app.canvas_manager.smart_sensor_override_clear(step_info)
                        self.main_app.canvas_manager.update_position_display()
                        
            elif status == 'step_completed':
                # Force position update after each step completion for all position-related operations
                if hasattr(self.main_app, 'canvas_manager') and info:
                    step_info = info.get('description', '')
                    
                    # Detect motor operation mode from completed step
                    self.main_app.canvas_manager.detect_operation_mode_from_step(step_info)
                    
                    # Update for move operations and sensor operations that might change position
                    if any(keyword in step_info.lower() for keyword in ['move', 'init', 'sensor', 'cut', 'mark']):
                        self.main_app.canvas_manager.update_position_display()
                    
                    # Update tool status indicators for tool actions
                    if any(keyword in step_info.lower() for keyword in ['line marker', 'line cutter', 'row marker', 'row cutter']):
                        self.main_app.canvas_manager.update_tool_status_from_step(step_info)
                    
                    # Special handling for line completion - ensure automatic move to next line
                    if 'close line marker' in step_info.lower() and 'lines' in step_info.lower():
                        print(f"🚀 LINE MARKING COMPLETED: {step_info}")
                        print(f"    Current step: {self.main_app.execution_engine.current_step_index}/{len(self.main_app.steps)}")
                        
                        # Check what the next step is
                        if (self.main_app.execution_engine.current_step_index < len(self.main_app.steps)):
                            next_step = self.main_app.steps[self.main_app.execution_engine.current_step_index]
                            print(f"    Next step: {next_step.get('operation', 'unknown')} - {next_step.get('description', 'no description')}")
                            
                            # If next step is a move operation, it should execute automatically
                            if next_step.get('operation') == 'move_y':
                                print(f"    ✅ Next step is Y movement - will execute automatically")
                                print(f"    🎯 Line marking sequence complete - ready for automatic move to next line")
                        
                        # Force position update to ensure we're ready for the next move
                        self.main_app.canvas_manager.update_position_display()
                    
            elif status == 'waiting_sensor':
                sensor_info = info.get('sensor', 'sensor') if info else 'sensor'
                self.main_app.operation_label.config(text=f"Waiting for {sensor_info} sensor", fg='orange')
        
        # Update progress bar if available
        if hasattr(self.main_app, 'progress') and hasattr(self.main_app, 'progress_text'):
            if status == 'executing' and info:
                progress = info.get('progress', 0)
                step_index = info.get('step_index', 0)
                total_steps = info.get('total_steps', 1)
                
                # Update progress bar
                self.main_app.progress['value'] = progress
                
                # Update progress text
                self.main_app.progress_text.config(text=f"{progress:.1f}% Complete ({step_index}/{total_steps} steps)")
                
                # Update step display to show current step progress
                if hasattr(self.main_app, 'right_panel'):
                    self.main_app.right_panel.update_step_display()
                
            elif status == 'completed':
                self.main_app.progress['value'] = 100
                self.main_app.progress_text.config(text="100% Complete - Execution finished")
                
                # Final step display update
                if hasattr(self.main_app, 'right_panel'):
                    self.main_app.right_panel.update_step_display()
                
            elif status == 'emergency_stop':
                # EMERGENCY STOP due to safety violation
                current_progress = self.main_app.progress['value']
                self.main_app.progress_text.config(text=f"🚨 EMERGENCY STOP - Safety Violation", fg='red')
                
                # Show emergency stop dialog
                violation_msg = info.get('violation_message', 'Unknown safety violation')
                safety_code = info.get('safety_code', '')
                monitor_type = info.get('monitor_type', 'pre_execution')
                
                import tkinter.messagebox as messagebox
                messagebox.showerror(
                    "🚨 EMERGENCY STOP - Safety Violation",
                    f"Execution has been immediately stopped due to a safety violation!\n\n"
                    f"Safety Code: {safety_code}\n"
                    f"Detection: {monitor_type.replace('_', ' ').title()}\n\n"
                    f"Details:\n{violation_msg}\n\n"
                    f"⚠️  All motor movement has been halted to prevent damage.\n"
                    f"Please correct the safety issue before attempting to continue."
                )
                
                # Update step display to show emergency stop state
                if hasattr(self.main_app, 'right_panel'):
                    self.main_app.right_panel.update_step_display()
                    
                # Update GUI controls to emergency stop state
                if hasattr(self.main_app, 'right_panel'):
                    # Set emergency stop button states
                    self.main_app.right_panel.run_btn.config(state='normal', text='🔄 RETRY', bg='orange')
                    self.main_app.right_panel.pause_btn.config(state='disabled')
                    self.main_app.right_panel.stop_btn.config(state='disabled')
                    
                    # Show persistent error status in right panel
                    error_message = f"⚠️  SAFETY VIOLATION: {safety_code}"
                    if hasattr(self.main_app.right_panel, 'progress_label'):
                        self.main_app.right_panel.progress_label.config(
                            text=error_message, 
                            fg='red'
                        )
                
                self.main_app.operation_label.config(text="🚨 EMERGENCY STOP - Safety Violation", fg='red')
            
            elif status == 'safety_recovered':
                # Safety violation resolved - auto-resuming
                message = info.get('message', 'Safety violation resolved')
                operation_type = info.get('operation_type', 'operation')
                
                # Update progress and status to show recovery
                current_progress = self.main_app.progress['value']
                self.main_app.progress_text.config(
                    text=f"{current_progress:.1f}% - Safety resolved, resuming...", 
                    fg='green'
                )
                
                # Restore run button to normal state
                if hasattr(self.main_app, 'right_panel'):
                    self.main_app.right_panel.run_btn.config(
                        state='disabled', 
                        text='▶ RUN', 
                        bg='darkgreen'
                    )
                    self.main_app.right_panel.pause_btn.config(state='normal')
                    self.main_app.right_panel.stop_btn.config(state='normal')
                    
                    # Clear error status from right panel
                    if hasattr(self.main_app.right_panel, 'progress_label'):
                        self.main_app.right_panel.progress_label.config(
                            text="✅ Safety violation resolved - Resuming", 
                            fg='green'
                        )
                
                # Update operation label
                self.main_app.operation_label.config(
                    text=f"✅ Safety resolved - {operation_type.title()} execution resuming", 
                    fg='green'
                )
            
            elif status == 'transition_alert':
                # Show auto-dismissing transition alert
                from_op = info.get('from_operation', '').title()
                to_op = info.get('to_operation', '').title()
                message = info.get('message', '')
                
                # Show non-blocking transition dialog
                self.show_transition_dialog(from_op, to_op, message)
                
                # Update GUI status
                self.main_app.operation_label.config(
                    text=f"⏸️  Waiting: {from_op} → {to_op} transition", 
                    fg='orange'
                )
                
                # Update progress text
                current_progress = self.main_app.progress['value']
                self.main_app.progress_text.config(
                    text=f"{current_progress:.1f}% - Waiting for row marker DOWN"
                )
            
            elif status == 'transition_waiting':
                # Update dialog with current status (if dialog exists)
                current_programmed = info.get('current_programmed', 'unknown').upper()
                current_actual = info.get('current_actual', 'unknown').upper()
                
                if hasattr(self, 'transition_dialog') and self.transition_dialog:
                    try:
                        self.update_transition_dialog_status(current_programmed, current_actual)
                    except:
                        pass  # Dialog may have been closed
            
            elif status == 'transition_complete':
                # Auto-dismiss the transition dialog
                if hasattr(self, 'transition_dialog') and self.transition_dialog:
                    try:
                        self.transition_dialog.destroy()
                        self.transition_dialog = None
                    except:
                        pass  # Dialog may already be closed
                
                # Update GUI status
                self.main_app.operation_label.config(
                    text="▶️  Rows operations starting...", 
                    fg='blue'
                )
                
                # Update progress text
                current_progress = self.main_app.progress['value']
                self.main_app.progress_text.config(
                    text=f"{current_progress:.1f}% - Continuing execution"
                )
            
            elif status == 'stopped' or status == 'error':
                # Keep current progress but update text
                current_progress = self.main_app.progress['value']
                self.main_app.progress_text.config(text=f"{current_progress:.1f}% - Execution stopped")
                
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
        
        violation_message = info.get('violation_message', 'Unknown safety violation')
        safety_code = info.get('safety_code', 'UNKNOWN')
        step = info.get('step', {})
        step_description = step.get('description', 'Unknown step')
        
        # Update progress label with safety violation
        if hasattr(self.main_app, 'progress_label'):
            self.main_app.progress_label.config(text="🚨 SAFETY VIOLATION - STOPPED", fg='red')
        
        # Update operation label
        if hasattr(self.main_app, 'operation_label'):
            self.main_app.operation_label.config(text="SAFETY VIOLATION - Execution Stopped", fg='red')
        
        # Show critical safety alert dialog
        self.show_safety_alert(violation_message, safety_code, step_description)
        
        # Update GUI to reflect stopped state
        self.update_gui_after_safety_stop()
    
    def show_safety_alert(self, violation_message, safety_code, step_description):
        """Show safety violation alert dialog"""
        try:
            # Create detailed alert message
            alert_title = f"🚨 SAFETY VIOLATION - {safety_code}"
            
            alert_message = f"""CRITICAL SAFETY VIOLATION DETECTED!

Execution has been stopped immediately for safety reasons.

Blocked Step: {step_description}

Safety Issue:
{violation_message}

REQUIRED ACTION:
Please resolve the safety condition before continuing execution.
Check the row marker position and ensure it is raised (UP) before attempting Y-axis movements.

The system will remain stopped until you manually address this issue."""

            # Show critical warning dialog
            messagebox.showerror(alert_title, alert_message)
            
            # Log to console as well
            print(f"\n{'='*60}")
            print(f"🚨 SAFETY VIOLATION: {safety_code}")
            print(f"Step: {step_description}")
            print(f"Issue: {violation_message}")
            print(f"{'='*60}\n")
            
        except Exception as e:
            print(f"Error showing safety alert: {e}")
            # Fallback to console message
            print(f"\n🚨 SAFETY VIOLATION: {violation_message}")
    
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
                    text=f"{current_progress:.1f}% - STOPPED: Safety Violation"
                )
            
        except Exception as e:
            print(f"Error updating GUI after safety stop: {e}")
    
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
        self.transition_dialog.title(f"Operation Transition: {from_op} → {to_op}")
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
            text=f"🔄 Operation Transition", 
            font=('Arial', 14, 'bold'),
            fg='orange'
        )
        title_label.pack(pady=(0, 10))
        
        # Transition info
        transition_label = tk.Label(
            main_frame,
            text=f"{from_op} Operations Complete ✅\nPreparing for {to_op} Operations",
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
            text="Current Row Marker Status:",
            font=('Arial', 10, 'bold'),
            padx=10, pady=5
        )
        status_title.pack()
        
        # Status labels (will be updated in real-time)
        self.transition_programmed_label = tk.Label(
            status_frame,
            text="Programmed: UP",
            font=('Arial', 9),
            padx=10, pady=2
        )
        self.transition_programmed_label.pack()
        
        self.transition_actual_label = tk.Label(
            status_frame,
            text="Actual: UP",
            font=('Arial', 9),
            padx=10, pady=2
        )
        self.transition_actual_label.pack()
        
        # Progress indicator
        progress_frame = tk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(
            progress_frame,
            text="⏳ Waiting for row marker DOWN position...",
            font=('Arial', 10, 'italic'),
            fg='blue'
        ).pack()
        
        # Instructions for user
        instructions_label = tk.Label(
            main_frame,
            text="💡 You can use the main window controls while this dialog is open.\nUse the 'Toggle Switch' button to set the row marker to DOWN position.",
            font=('Arial', 9, 'bold'),
            fg='blue',
            wraplength=400,
            justify=tk.CENTER
        )
        instructions_label.pack(pady=(5, 5))
        
        # Auto-dismiss info
        auto_dismiss_label = tk.Label(
            main_frame,
            text="This dialog will automatically close when the row marker is set to DOWN position.",
            font=('Arial', 9, 'italic'),
            fg='gray',
            wraplength=400,
            justify=tk.CENTER
        )
        auto_dismiss_label.pack(pady=(5, 0))
        
        print(f"📋 Transition dialog shown: {from_op} → {to_op}")
    
    def update_transition_dialog_status(self, current_programmed, current_actual):
        """Update the transition dialog with current status"""
        if not hasattr(self, 'transition_dialog') or not self.transition_dialog:
            return
            
        try:
            # Update status labels with current state
            prog_color = 'green' if current_programmed == 'DOWN' else 'red'
            actual_color = 'green' if current_actual == 'DOWN' else 'red'
            
            self.transition_programmed_label.config(
                text=f"Programmed: {current_programmed}",
                fg=prog_color
            )
            
            self.transition_actual_label.config(
                text=f"Actual: {current_actual}",
                fg=actual_color
            )
            
        except Exception as e:
            print(f"Error updating transition dialog: {e}")