#!/usr/bin/env python3

import threading
import time
import json
from hardware.interfaces.hardware_factory import get_hardware_interface
from core.safety_system import SafetyViolation, check_step_safety
from core.logger import get_logger

# Load settings
def load_settings():
    """Load settings from config/settings.json"""
    try:
        with open('config/settings.json', 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

settings = load_settings()
timing_settings = settings.get("timing", {})

class ExecutionEngine:
    """Lightweight execution engine optimized for Raspberry Pi with threading support"""

    def __init__(self):
        # Initialize logger
        self.logger = get_logger()

        # Simple state variables for minimal memory usage
        self.steps = []
        self.current_step_index = 0
        self.is_running = False
        self.is_paused = False
        self.execution_thread = None

        # Hardware interface (factory pattern)
        self.hardware = get_hardware_interface()

        # Threading events for control
        self.pause_event = threading.Event()
        self.stop_event = threading.Event()
        self.safety_monitor_stop = threading.Event()
        self.in_transition = False  # Flag to pause safety monitoring during transitions

        # Progress tracking
        self.step_results = []
        self.start_time = None
        self.end_time = None

        # Status callback (for GUI updates)
        self.status_callback = None

        # Operation callback (for individual operation tracking)
        self.operation_callback = None

        # Safety monitoring
        self.safety_monitor_thread = None
        self.current_operation_type = None  # 'lines' or 'rows'

        # Set pause event initially (not paused)
        self.pause_event.set()

    def set_status_callback(self, callback):
        """Set callback function for status updates"""
        self.status_callback = callback

    def _update_status(self, status, step_info=None):
        """Update status and call callback if set"""
        if self.status_callback:
            self.status_callback(status, step_info)

    def load_steps(self, steps):
        """Load steps for execution - optimized for minimal memory usage"""
        self.steps = steps
        self.current_step_index = 0
        self.step_results = []
        self.start_time = None
        self.end_time = None
        self.logger.info(f"Loaded {len(steps)} steps for execution", category="execution")

    def start_execution(self):
        """Start execution in a separate thread"""
        if self.is_running:
            self.logger.warning("Execution already running", category="execution")
            return False

        if not self.steps:
            self.logger.warning("No steps loaded", category="execution")
            return False

        # Reset state
        self.is_running = True
        self.is_paused = False
        self.stop_event.clear()
        self.pause_event.set()
        self.current_step_index = 0
        self.step_results = []
        self.start_time = time.time()

        # Pass execution engine reference to mock hardware for sensor waiting functions
        self.hardware.set_execution_engine_reference(self)

        # Start execution thread
        self.execution_thread = threading.Thread(target=self._execution_loop, daemon=False)
        self.execution_thread.start()

        # Start safety monitoring thread
        self.safety_monitor_stop.clear()
        self.safety_monitor_thread = threading.Thread(target=self._safety_monitor_loop, daemon=False)
        self.safety_monitor_thread.start()

        self.logger.info("Execution started with real-time safety monitoring", category="execution")
        self._update_status("started")
        return True

    def pause_execution(self):
        """Pause execution"""
        if not self.is_running or self.is_paused:
            self.logger.warning("Cannot pause - not running or already paused", category="execution")
            return False

        self.is_paused = True
        self.pause_event.clear()
        self.logger.info("Execution paused", category="execution")
        self._update_status("paused")
        return True

    def resume_execution(self):
        """Resume execution"""
        if not self.is_running or not self.is_paused:
            self.logger.warning("Cannot resume - not running or not paused", category="execution")
            return False

        # Flush all sensor buffers when manually resuming (in case paused due to safety)
        self.hardware.flush_all_sensor_buffers()

        self.is_paused = False
        self.pause_event.set()
        self.logger.info("Execution resumed", category="execution")
        self._update_status("resumed")
        return True

    def stop_execution(self):
        """Stop execution"""
        if not self.is_running:
            self.logger.warning("Execution not running", category="execution")
            return False

        self.stop_event.set()
        self.pause_event.set()  # Ensure thread can proceed to check stop event

        # Stop safety monitoring
        self.safety_monitor_stop.set()

        # Wait for threads to finish (with timeout)
        if self.execution_thread and self.execution_thread.is_alive():
            self.execution_thread.join(timeout=timing_settings.get("thread_join_timeout_execution", 2.0))
        if self.safety_monitor_thread and self.safety_monitor_thread.is_alive():
            self.safety_monitor_thread.join(timeout=timing_settings.get("thread_join_timeout_safety", 1.0))

        self.is_running = False
        self.is_paused = False
        self.logger.info("Execution stopped - safety monitoring disabled", category="execution")
        self._update_status("stopped")
        return True

    def reset_execution(self):
        """Reset execution to beginning - fully reset all state"""
        if self.is_running:
            self.logger.warning("Cannot reset while running - stop execution first", category="execution")
            return False

        # Reset execution state
        self.current_step_index = 0
        self.step_results = []
        self.start_time = None
        self.end_time = None
        self.is_paused = False
        self.is_running = False

        # Reset threading events to initial state
        self.stop_event.clear()
        self.pause_event.set()  # Not paused initially
        self.safety_monitor_stop.set()  # Stop any lingering safety monitor

        # Reset operation tracking
        self.current_operation_type = None
        self.in_transition = False

        # Clean up threads if they're still around
        if self.execution_thread and self.execution_thread.is_alive():
            self.logger.warning("Warning: Execution thread still alive during reset - waiting for cleanup", category="execution")
            self.execution_thread.join(timeout=1.0)
        if self.safety_monitor_thread and self.safety_monitor_thread.is_alive():
            self.logger.warning("Warning: Safety monitor thread still alive during reset - waiting for cleanup", category="execution")
            self.safety_monitor_thread.join(timeout=1.0)

        self.execution_thread = None
        self.safety_monitor_thread = None

        self.logger.success("Execution fully reset - all state cleared, ready to start", category="execution")
        return True

    def step_forward(self):
        """Move to next step (manual navigation)"""
        if self.is_running and not self.is_paused:
            self.logger.warning("Cannot navigate manually while execution is running", category="execution")
            return False

        if self.current_step_index < len(self.steps) - 1:
            self.current_step_index += 1
            self.logger.debug(f"Moved to step {self.current_step_index}/{len(self.steps)}", category="execution")
            return True
        else:
            self.logger.info("Already at last step", category="execution")
            return False

    def step_backward(self):
        """Move to previous step (manual navigation)"""
        if self.is_running and not self.is_paused:
            self.logger.warning("Cannot navigate manually while execution is running", category="execution")
            return False

        if self.current_step_index > 0:
            self.current_step_index -= 1
            self.logger.debug(f"Moved to step {self.current_step_index}/{len(self.steps)}", category="execution")
            return True
        else:
            self.logger.info("Already at first step", category="execution")
            return False

    def go_to_step(self, step_index):
        """Go to specific step (manual navigation)"""
        if self.is_running and not self.is_paused:
            self.logger.warning("Cannot navigate manually while execution is running", category="execution")
            return False

        if 0 <= step_index < len(self.steps):
            self.current_step_index = step_index
            self.logger.debug(f"Moved to step {self.current_step_index}/{len(self.steps)}", category="execution")
            return True
        else:
            self.logger.warning(f"Invalid step index: {step_index}. Valid range: 0-{len(self.steps) - 1}", category="execution")
            return False

    def execute_current_step(self):
        """Execute current step manually (for step-by-step operation)"""
        if self.is_running:
            self.logger.warning("Cannot execute manually while automatic execution is running", category="execution")
            return None

        if self.current_step_index >= len(self.steps):
            self.logger.info("No more steps to execute", category="execution")
            return None

        step = self.steps[self.current_step_index]

        # Safety check for manual execution too
        try:
            check_step_safety(step)
        except SafetyViolation as e:
            self.logger.error(f"SAFETY VIOLATION: Cannot execute step manually!", category="execution")
            self.logger.error(f"Step: {step.get('description', 'Unknown')}", category="execution")
            self.logger.error(f"Safety issue: {e.message}", category="execution")

            # Update status with safety error
            self._update_status("safety_violation", {
                'step': step,
                'violation_message': e.message,
                'safety_code': e.safety_code
            })

            return {
                'success': False,
                'error': 'Safety violation',
                'safety_violation': True,
                'violation_message': e.message,
                'safety_code': e.safety_code
            }

        result = self._execute_step(step)

        # Store result
        self.step_results.append({
            'step_index': self.current_step_index,
            'step': step,
            'result': result,
            'timestamp': time.time()
        })

        self.logger.info(f"Executed step {self.current_step_index}/{len(self.steps)} manually", category="execution")
        return result

    def _execution_loop(self):
        """Main execution loop - runs in separate thread"""
        try:
            while self.current_step_index < len(self.steps) and not self.stop_event.is_set():
                # Check for pause
                self.logger.debug(f"EXECUTION LOOP: Step {self.current_step_index + 1}/{len(self.steps)} - Checking pause state", category="execution")
                self.pause_event.wait()
                self.logger.debug(f"    Execution not paused - proceeding with step", category="execution")

                # Check for stop after pause
                if self.stop_event.is_set():
                    self.logger.debug(f"    Stop event detected - breaking execution loop", category="execution")
                    break

                # Execute current step
                step = self.steps[self.current_step_index]
                self.logger.info(f"EXECUTING STEP {self.current_step_index + 1}: {step['operation']} - {step['description']}", category="execution")

                # Track current step description for safety monitoring
                self.current_step_description = step.get('description', '')

                # Detect transition but don't update operation type to 'rows' yet
                temp_operation_type = self._detect_operation_type_from_step(step)
                previous_operation = self.current_operation_type

                self.logger.debug(f"TRANSITION CHECK: previous='{previous_operation}', detected='{temp_operation_type}'", category="execution")

                # Handle transition from lines to rows operations IMMEDIATELY
                if previous_operation == 'lines' and temp_operation_type == 'rows':
                    self.logger.info("OPERATION TRANSITION: Lines → Rows detected", category="execution")
                    self.logger.debug(f"TRANSITION STEP: {step.get('description', '')}", category="execution")
                    self.logger.debug(f"STEP OPERATION: {step.get('operation', '')}", category="execution")
                    self.logger.debug(f"PREVIOUS OP: {previous_operation}, DETECTED OP: {temp_operation_type}", category="execution")

                    # CRITICAL: Set transition flag BEFORE any safety checks can run
                    self.in_transition = True
                    self.logger.info("TRANSITION FLAG SET IMMEDIATELY - ALL SAFETY CHECKS BYPASSED", category="execution")

                    try:
                        transition_result = self._handle_lines_to_rows_transition()
                        self.logger.debug(f"TRANSITION RESULT: {transition_result}", category="execution")
                        if not transition_result:
                            # Transition failed - stop execution
                            self.logger.error("TRANSITION FAILED - Breaking execution loop", category="execution")
                            self.in_transition = False  # Clear flag on failure
                            break
                    except Exception as e:
                        self.logger.error(f"TRANSITION EXCEPTION: {e}", category="execution")
                        self.in_transition = False  # Clear flag on exception
                        break
                    # After successful transition, update operation type to 'rows' and continue
                    self.current_operation_type = 'rows'
                    self.logger.success("TRANSITION COMPLETED - Operation type updated to ROWS - Continuing with triggering step", category="execution")

                # Update operation type for non-transition steps
                if not (previous_operation == 'lines' and temp_operation_type == 'rows'):
                    # Normal operation type update (no transition)
                    self._update_current_operation_type(step)

                # Notify step execution started (for operation tracking)
                self._update_status("step_executing", {
                    'description': step.get('description', ''),
                    'step_index': self.current_step_index,
                    'total_steps': len(self.steps)
                })

                step_result = self._execute_step(step)

                # Check if step execution resulted in safety violation
                if step_result and step_result.get('safety_violation'):
                    # Safety violation occurred - stop execution immediately
                    self.logger.error("EXECUTION EMERGENCY STOP: Safety violation detected!", category="execution")
                    self.logger.error(f"   Violation: {step_result.get('violation_message', 'Unknown safety issue')}", category="execution")

                    # Emergency stop - set stop event immediately
                    self.stop_event.set()
                    self.is_running = False
                    self.is_paused = False

                    # Update status with emergency stop
                    self._update_status("emergency_stop", {
                        'violation_message': step_result.get('violation_message', ''),
                        'safety_code': step_result.get('safety_code', ''),
                        'step': step
                    })

                    break

                # Notify step execution completed (for immediate position updates)
                self._update_status("step_completed", {
                    'description': step.get('description', ''),
                    'step_index': self.current_step_index,
                    'total_steps': len(self.steps),
                    'result': step_result
                })

                # Store result
                self.step_results.append({
                    'step_index': self.current_step_index,
                    'step': step,
                    'result': step_result,
                    'timestamp': time.time()
                })

                # Force canvas position update after each step
                if hasattr(self, 'canvas_manager') and self.canvas_manager:
                    self.canvas_manager.update_position_display()

                # Move to next step FIRST, then update status with completed step index
                completed_step_index = self.current_step_index
                self.current_step_index += 1
                self.logger.debug(f"STEP ADVANCE: {completed_step_index + 1} → {self.current_step_index + 1}", category="execution")

                # Update progress - use current index which now points to next step
                progress = (self.current_step_index) / len(self.steps) * 100
                self._update_status("executing", {
                    'step_index': self.current_step_index,
                    'total_steps': len(self.steps),
                    'progress': progress,
                    'step_description': step.get('description', ''),
                    'result': step_result
                })

                # Check what the next step will be
                if self.current_step_index < len(self.steps):
                    next_step = self.steps[self.current_step_index]
                    self.logger.debug(f"    Next step: {next_step['operation']} - {next_step['description']}", category="execution")

                    # If next step is move_y, it should execute immediately
                    if next_step['operation'] == 'move_y':
                        self.logger.debug(f"    Next step is move_y - should execute automatically without waiting", category="execution")
                else:
                    self.logger.debug(f"    All steps completed", category="execution")

                # Small delay to prevent overwhelming the system
                time.sleep(timing_settings.get("execution_loop_delay", 0.05))

            # Execution completed
            self.end_time = time.time()
            self.is_running = False
            self.is_paused = False

            if self.stop_event.is_set():
                self.logger.info("Execution stopped by user", category="execution")
                self._update_status("stopped")
            else:
                self.logger.success("Execution completed successfully", category="execution")
                self._update_status("completed")

        except Exception as e:
            self.logger.error(f"Execution error: {e}", category="execution")
            self.is_running = False
            self.is_paused = False
            self._update_status("error", {'error': str(e)})

    def _execute_step(self, step):
        """Execute a single step with safety validation"""
        operation = step['operation']
        parameters = step.get('parameters', {})
        description = step.get('description', '')

        self.logger.info(f"Executing: {description}", category="execution")

        # SAFETY CHECK: Validate step safety before execution (skip during transitions)
        if not self.in_transition:
            try:
                check_step_safety(step)
            except SafetyViolation as e:
                self.logger.error(f"SAFETY VIOLATION DETECTED!", category="execution")
                self.logger.error(f"Step blocked: {description}", category="execution")
                self.logger.error(f"Safety violation: {e.message}", category="execution")

                # Don't call stop_execution() here as it causes thread join issues
                # The execution loop will handle the safety violation result

                # Update status with safety error
                self._update_status("safety_violation", {
                    'step': step,
                    'violation_message': e.message,
                    'safety_code': e.safety_code
                })

                return {
                    'success': False,
                    'error': 'Safety violation',
                    'safety_violation': True,
                    'violation_message': e.message,
                    'safety_code': e.safety_code
                }
        else:
            self.logger.debug(f"TRANSITION: Skipping safety check for step during transition: {description[:50]}...", category="execution")

        try:
            if operation == 'move_x':
                target_x = parameters['position']
                # Use instant movement (no animation)
                self.hardware.move_x(target_x)

                # Update GUI position display if available
                if hasattr(self, 'canvas_manager') and self.canvas_manager:
                    self.canvas_manager.update_position_display()

                return {'success': True, 'position': target_x}

            elif operation == 'move_y':
                target_y = parameters['position']
                # Use instant movement (no animation)
                self.hardware.move_y(target_y)

                # Update GUI position display if available
                if hasattr(self, 'canvas_manager') and self.canvas_manager:
                    self.canvas_manager.update_position_display()

                return {'success': True, 'position': target_y}

            elif operation == 'move_position':
                # Move to position with offsets (for repeat patterns)
                x_offset = parameters.get('x_offset', 0.0)
                y_offset = parameters.get('y_offset', 0.0)

                # Calculate target position from current base position + offsets
                current_x = self.hardware.get_current_x()
                current_y = self.hardware.get_current_y()
                target_x = current_x + x_offset
                target_y = current_y + y_offset

                # Use instant movement (no animation)
                self.hardware.move_x(target_x)
                self.hardware.move_y(target_y)

                # Update GUI position display if available
                if hasattr(self, 'canvas_manager') and self.canvas_manager:
                    self.canvas_manager.update_position_display()

                return {'success': True, 'position': (target_x, target_y)}

            elif operation == 'wait_sensor':
                sensor = parameters['sensor']

                # Wait for MANUAL sensor trigger - do not auto-trigger
                self.logger.info(f"Waiting for MANUAL {sensor} sensor trigger...", category="execution")

                # Notify GUI of sensor wait (for visual feedback)
                self._update_status("waiting_sensor", {'sensor': sensor})

                # Wait for manual sensor trigger
                if sensor == 'x':
                    result = self.hardware.wait_for_x_sensor()
                elif sensor == 'y':
                    result = self.hardware.wait_for_y_sensor()
                elif sensor == 'x_left':
                    result = self.hardware.wait_for_x_left_sensor()
                elif sensor == 'x_right':
                    result = self.hardware.wait_for_x_right_sensor()
                elif sensor == 'y_top':
                    result = self.hardware.wait_for_y_top_sensor()
                elif sensor == 'y_bottom':
                    result = self.hardware.wait_for_y_bottom_sensor()
                else:
                    return {'success': False, 'error': f'Unknown sensor: {sensor}'}

                # Update GUI position display if available
                if hasattr(self, 'canvas_manager') and self.canvas_manager:
                    self.canvas_manager.update_position_display()

                return {'success': True, 'sensor_result': result}

            elif operation == 'tool_action':
                tool = parameters['tool']
                action = parameters['action']

                # Map tool actions to hardware functions
                # NOTE: row_marker tool actions do NOT affect the limit switch state
                # The limit switch is ONLY controlled by user via toggle button
                tool_functions = {
                    'line_marker': {'down': self.hardware.line_marker_down, 'up': self.hardware.line_marker_up},
                    'line_cutter': {'down': self.hardware.line_cutter_down, 'up': self.hardware.line_cutter_up},
                    'row_marker': {'down': self._row_marker_tool_down, 'up': self._row_marker_tool_up},
                    'row_cutter': {'down': self.hardware.row_cutter_down, 'up': self.hardware.row_cutter_up},
                    'line_motor_piston': {'down': self.hardware.line_motor_piston_down, 'up': self.hardware.line_motor_piston_up}
                }

                if tool in tool_functions and action in tool_functions[tool]:
                    tool_functions[tool][action]()
                    self.logger.success(f"Tool action completed: {tool} {action}", category="execution")

                    # Special handling for line marker close - should trigger automatic move to next line
                    if tool == 'line_marker' and action == 'up':
                        self.logger.debug(f"LINE MARKER CLOSED - next step should be automatic move to next line", category="execution")

                    return {'success': True, 'tool': tool, 'action': action}
                else:
                    return {'success': False, 'error': f'Unknown tool/action: {tool}/{action}'}

            elif operation == 'tool_positioning':
                action = parameters['action']

                if action == 'lift_line_tools':
                    self.hardware.lift_line_tools()
                elif action == 'lower_line_tools':
                    self.hardware.lower_line_tools()
                elif action == 'move_line_tools_to_top':
                    self.hardware.move_line_tools_to_top()
                else:
                    return {'success': False, 'error': f'Unknown positioning action: {action}'}

                return {'success': True, 'action': action}

            elif operation == 'program_start':
                self.logger.info(f"=== Starting Program {parameters['program_number']}: {parameters['program_name']} ===", category="execution")
                return {'success': True, 'program_info': parameters}

            elif operation == 'workflow_separator':
                self.logger.info(f"=== {description} ===", category="execution")
                return {'success': True}

            elif operation == 'program_complete':
                self.logger.success(f"=== Program Complete: {parameters['program_name']} ===", category="execution")
                return {'success': True, 'program_info': parameters}

            else:
                result = {'success': False, 'error': f'Unknown operation: {operation}'}

        except Exception as e:
            result = {'success': False, 'error': str(e)}

        # Call operation callback if set
        if self.operation_callback:
            try:
                self.operation_callback(step, result)
            except Exception as e:
                self.logger.warning(f"Warning: Operation callback failed: {e}", category="execution")

        return result

    def _row_marker_tool_down(self):
        """Lower the row marker tool for marking"""
        self.logger.debug("Row marker tool: DOWN (marking position)", category="execution")
        self.hardware.row_marker_down()

    def _row_marker_tool_up(self):
        """Raise the row marker tool after marking"""
        self.logger.debug("Row marker tool: UP (raised position)", category="execution")
        self.hardware.row_marker_up()

    def _update_current_operation_type(self, step, allow_rows_transition=True):
        """Update the current operation type based on step description for safety monitoring"""
        description = step.get('description', '').lower()
        operation = step.get('operation', '').lower()

        # Store previous operation type for transition detection
        previous_operation = self.current_operation_type

        # Detect operation type from both operation field and description
        if (operation in ['move_y'] or
            any(keyword in description for keyword in ['lines', 'line_', 'line ', 'move_y', 'y_'])):
            if 'rows' not in description:  # Make sure it's not a rows operation
                self.current_operation_type = 'lines'
        elif (operation in ['move_x'] or
              any(keyword in description for keyword in ['rows', 'row_', 'move_x', 'x_'])):
            if 'lines' not in description and 'line' not in description:  # Make sure it's not a lines operation
                # Only update to 'rows' if transition is allowed (after dialog completion)
                if allow_rows_transition:
                    self.current_operation_type = 'rows'
                # If transition not allowed, keep previous operation type for now
        else:
            # Keep previous operation type for ambiguous steps
            pass

        if self.current_operation_type:
            self.logger.debug(f"SAFETY MONITOR: Current operation type = {self.current_operation_type.upper()}", category="execution")

        # Return previous operation for transition detection
        return previous_operation

    def _detect_operation_type_from_step(self, step):
        """Detect operation type from step without updating current_operation_type"""
        description = step.get('description', '').lower()
        operation = step.get('operation', '').lower()

        self.logger.debug(f"TRANSITION DETECTION: operation='{operation}', description='{description[:50]}...'", category="execution")

        # Check both operation field and description for lines operations
        if (operation in ['move_y'] or
            any(keyword in description for keyword in ['lines', 'line_', 'line ', 'move_y', 'y_'])):
            if 'rows' not in description:
                self.logger.debug(f"   → Detected as LINES operation", category="execution")
                return 'lines'

        # Check both operation field and description for rows operations
        elif (operation in ['move_x'] or
              any(keyword in description for keyword in ['rows', 'row_', 'move_x', 'x_'])):
            if 'lines' not in description and 'line' not in description:
                self.logger.debug(f"   → Detected as ROWS operation", category="execution")
                return 'rows'

        # Return current operation type if step type is ambiguous
        self.logger.debug(f"   → Ambiguous step, keeping current: {self.current_operation_type}", category="execution")
        return self.current_operation_type

    def _safety_monitor_loop(self):
        """Real-time safety monitoring loop - runs in separate thread"""
        self.logger.info("Real-time safety monitoring started", category="execution")

        try:
            while not self.safety_monitor_stop.is_set():
                # Monitor safety during execution (running + not paused) OR during safety recovery (paused due to violation)
                if self.is_running and self.current_operation_type:

                    # Skip safety monitoring during transitions
                    if self.in_transition:
                        self.logger.debug("Skipping safety monitor during lines→rows transition...", category="execution")
                        time.sleep(timing_settings.get("transition_monitor_interval", 0.5))
                        continue

                    # Skip safety monitoring during setup steps
                    if hasattr(self, 'current_step_description'):
                        from core.safety_system import safety_system
                        if safety_system._is_setup_movement(self.current_step_description):
                            self.logger.debug(f"Skipping safety monitor for setup step: {self.current_step_description[:50]}...", category="execution")
                            time.sleep(timing_settings.get("safety_check_interval", 0.1))
                            continue

                    # Check safety based on current operation type
                    try:
                        row_motor_limit_switch = self.hardware.get_row_motor_limit_switch()

                        safety_violation = False
                        violation_message = ""

                        # DEBUG: Show current monitoring state (less frequent)
                        # self.logger.debug(f"Safety Monitor: Operation={self.current_operation_type}, Programmed={row_marker_programmed.upper()}, Physical={row_motor_limit_switch.upper()}", category="execution")

                        if self.current_operation_type == 'lines':
                            # LINES OPERATIONS: Two safety checks
                            # 1. Row marker MUST be UP (door closed)
                            # 2. Line motor piston must be DOWN (Y motor assembly lowered)
                            line_motor_piston = self.hardware.get_line_motor_piston_state()

                            # Check 1: Row marker down during lines operations
                            if row_motor_limit_switch == "down":
                                safety_violation = True
                                violation_message = (
                                    f"LINES OPERATION EMERGENCY STOP!\n"
                                    f"   Row marker changed to DOWN during lines operation\n"
                                    f"   State: {row_motor_limit_switch.upper()}\n"
                                    f"   IMMEDIATE ACTION: Close the rows door (set marker UP)"
                                )

                            # Check 2: Line motor piston UP during operations
                            # EXCEPTION: Piston can be UP if rows motor (X-axis) is at position 0
                            elif line_motor_piston == "up":
                                current_x = self.hardware.get_current_x()

                                # Only trigger violation if X motor is NOT at position 0
                                if current_x != 0:
                                    safety_violation = True
                                    violation_message = (
                                        f"LINE MOTOR PISTON SAFETY VIOLATION!\n"
                                        f"   Line motor piston is UP during lines operation\n"
                                        f"   Piston state: {line_motor_piston.upper()}\n"
                                        f"   Rows motor position: {current_x:.1f}cm (must be at 0cm for safe piston operation)\n"
                                        f"   RULE VIOLATED: Line motor piston can only be UP when rows motor is at 0cm\n"
                                        f"   IMMEDIATE ACTION: Move rows motor to 0cm OR lower line motor piston"
                                    )

                        elif self.current_operation_type == 'rows':
                            # ROWS OPERATIONS: Three safety checks
                            # 1. Door can only be CLOSED (limit switch DOWN) when line motor piston is DOWN
                            # 2. Row motor limit switch must be DOWN during rows operations
                            # 3. Line motor piston must be DOWN (Y motor assembly lowered)
                            line_motor_piston = self.hardware.get_line_motor_piston_state()
                            row_motor_limit_switch = self.hardware.get_row_motor_limit_switch()

                            # Check 1: Door closed while line motor piston UP
                            if row_motor_limit_switch == "down" and line_motor_piston == "up":
                                safety_violation = True
                                violation_message = (
                                    f"ROWS MOTOR DOOR SAFETY VIOLATION!\n"
                                    f"   Door CLOSED (limit switch DOWN) while line motor piston is UP\n"
                                    f"   Line motor piston: {line_motor_piston.upper()} (must be DOWN to close door)\n"
                                    f"   Limit switch: {row_motor_limit_switch.upper()}\n"
                                    f"   IMMEDIATE ACTION: Open the rows motor door (set limit switch to OFF)"
                                )

                            # Check 2: Row motor limit switch UP during rows operations
                            elif row_motor_limit_switch == "up":
                                safety_violation = True
                                violation_message = (
                                    f"ROWS OPERATION SAFETY VIOLATION!\n"
                                    f"   Row motor limit switch is UP during rows operation\n"
                                    f"   Limit switch state: {row_motor_limit_switch.upper()}\n"
                                    f"   RULE VIOLATED: Row motor door must be CLOSED during rows operations\n"
                                    f"   IMMEDIATE ACTION: Close the rows motor door (set limit switch to DOWN)"
                                )

                            # Check 3: Line motor piston UP during operations
                            elif line_motor_piston == "up":
                                safety_violation = True
                                violation_message = (
                                    f"LINE MOTOR PISTON SAFETY VIOLATION!\n"
                                    f"   Line motor piston is UP during rows operation\n"
                                    f"   Piston state: {line_motor_piston.upper()}\n"
                                    f"   RULE VIOLATED: Line motor piston must be DOWN during operations\n"
                                    f"   IMMEDIATE ACTION: Lower line motor piston (Y motor assembly must be DOWN)"
                                )

                        if safety_violation:
                            self.logger.error("REAL-TIME SAFETY VIOLATION DETECTED!", category="execution")
                            self.logger.error(violation_message, category="execution")

                            # PAUSE execution instead of stopping completely
                            if not self.is_paused:  # Only pause if not already paused
                                self.is_paused = True
                                self.pause_event.clear()

                                # Update status with emergency stop
                                self._update_status("emergency_stop", {
                                    'violation_message': violation_message,
                                    'safety_code': f"{self.current_operation_type.upper()}_DOOR_VIOLATION",
                                    'monitor_type': 'real_time'
                                })

                        # Check for safety violation recovery (when paused due to violation)
                        elif self.is_paused:
                            # Check if previous violation has been resolved
                            violation_resolved = False

                            if self.current_operation_type == 'lines':
                                # LINES: Check limit switch, line motor piston, and X position
                                line_motor_piston = self.hardware.get_line_motor_piston_state()
                                current_x = self.hardware.get_current_x()

                                # Violation resolved if:
                                # 1. Limit switch UP AND
                                # 2. (Piston DOWN OR X motor at 0)
                                if row_motor_limit_switch == "up" and (line_motor_piston == "down" or current_x == 0):
                                    violation_resolved = True
                                    if line_motor_piston == "down":
                                        self.logger.success("LINES SAFETY VIOLATION RESOLVED: Door open and line motor piston down", category="execution")
                                    else:
                                        self.logger.success(f"LINES SAFETY VIOLATION RESOLVED: Door open and rows motor at 0cm (piston UP allowed)", category="execution")

                            elif self.current_operation_type == 'rows':
                                # ROWS: Check door, limit switch, and line motor piston
                                line_motor_piston = self.hardware.get_line_motor_piston_state()

                                # Violation resolved if limit switch DOWN AND line motor piston DOWN
                                if row_motor_limit_switch == "down" and line_motor_piston == "down":
                                    violation_resolved = True
                                    self.logger.success("ROWS SAFETY VIOLATION RESOLVED: Door closed and line motor piston down", category="execution")

                            if violation_resolved:
                                # Flush all sensor buffers to ignore triggers that happened during pause
                                self.hardware.flush_all_sensor_buffers()

                                # Auto-resume execution
                                self.is_paused = False
                                self.pause_event.set()

                                # Update status to show recovery
                                self._update_status("safety_recovered", {
                                    'message': f'{self.current_operation_type.title()} operation safety violation resolved - resuming execution',
                                    'operation_type': self.current_operation_type
                                })

                                self.logger.info(f"AUTO-RESUMING {self.current_operation_type.upper()} EXECUTION", category="execution")

                    except Exception as e:
                        self.logger.warning(f"Safety monitor error: {e}", category="execution")

                # Check every 100ms for real-time monitoring
                time.sleep(timing_settings.get("safety_check_interval", 0.1))

        except Exception as e:
            self.logger.error(f"Safety monitoring thread error: {e}", category="execution")

        self.logger.info("Real-time safety monitoring stopped", category="execution")

    def _handle_lines_to_rows_transition(self):
        """
        Handle transition from lines operations to rows operations
        Show auto-dismissing alert that waits for row marker DOWN
        """
        try:
            self.logger.debug("TRANSITION: Starting _handle_lines_to_rows_transition", category="execution")

            # Transition flag is already set in main execution loop
            self.logger.debug("TRANSITION: Safety monitoring already paused by transition flag", category="execution")

            # Check if rows motor door is already CLOSED (limit switch ON)
            # Only check limit switch, NOT marker piston state
            limit_switch_state = self.hardware.get_row_motor_limit_switch()
            self.logger.debug(f"TRANSITION: Current rows motor door limit switch: {limit_switch_state}", category="execution")

            if limit_switch_state == "down":
                self.logger.success("Rows motor door already CLOSED (limit switch ON) - proceeding with rows operations", category="execution")
                self.in_transition = False  # Clear transition flag
                return True

            self.logger.info("TRANSITION PAUSE: Waiting for rows motor door to be CLOSED (toggle limit switch button)", category="execution")
            self.logger.debug("TRANSITION: Setting execution to paused state", category="execution")

            # Pause execution temporarily
            self.is_paused = True
            self.pause_event.clear()

            self.logger.debug("TRANSITION: Calling _update_status with transition_alert", category="execution")
            # Show transitional alert through status callback
            self._update_status("transition_alert", {
                'from_operation': 'lines',
                'to_operation': 'rows',
                'message': 'Lines operations complete. Please CLOSE ROWS MOTOR DOOR (toggle limit switch button to ON) to continue with rows operations.',
                'current_limit_switch': limit_switch_state
            })

            self.logger.debug("TRANSITION: Calling _wait_for_row_marker_down", category="execution")
            # Wait for row marker to be set DOWN with auto-monitoring
            result = self._wait_for_row_marker_down()
            self.logger.debug(f"TRANSITION: _wait_for_row_marker_down returned: {result}", category="execution")
            return result

        except Exception as e:
            self.logger.error(f"TRANSITION EXCEPTION in _handle_lines_to_rows_transition: {e}", category="execution")
            import traceback
            traceback.print_exc()
            self.in_transition = False  # Clear flag on error
            return False

    def _wait_for_row_marker_down(self):
        """
        Wait for rows motor door to be CLOSED (limit switch ON) with real-time monitoring
        Auto-dismiss alert and resume execution when condition is met
        """
        import time

        self.logger.info("Monitoring rows motor door - waiting for CLOSED position (limit switch ON)...", category="execution")

        while not self.stop_event.is_set():
            # Check ONLY limit switch state (motor door sensor)
            # Marker piston state is independent and controlled by program
            limit_switch_state = self.hardware.get_row_motor_limit_switch()

            # Debug output to verify monitoring is running (less frequent)
            # self.logger.debug(f"Monitoring: Limit switch={limit_switch_state.upper()}", category="execution")

            if limit_switch_state == "down":
                self.logger.success("Rows motor door CLOSED (limit switch ON) - verifying stable position...", category="execution")

                # Wait a short time to ensure the position is stable
                time.sleep(timing_settings.get("row_marker_stable_delay", 0.2))

                # Double-check the limit switch is still ON
                limit_switch_state_stable = self.hardware.get_row_motor_limit_switch()

                if limit_switch_state_stable == "down":
                    self.logger.success("Rows motor door limit switch stable - auto-resuming execution", category="execution")

                    # Clear transition flag to resume safety monitoring
                    self.in_transition = False
                    self.logger.debug("TRANSITION: Resuming safety monitoring for rows operations", category="execution")

                    # Update operation type to rows BEFORE position update
                    self.current_operation_type = 'rows'
                    self.logger.debug("TRANSITION: Set operation type to 'rows'", category="execution")

                    # CRITICAL: Find and execute the first move_x step immediately to position motor
                    # This ensures the visual shows the motor at the correct position before resuming
                    self.logger.debug(f"TRANSITION: Looking for first move_x step after current position {self.current_step_index}", category="execution")

                    # Find the first move_x step after the current position
                    first_move_x_step = None
                    for idx in range(self.current_step_index, min(self.current_step_index + 5, len(self.steps))):
                        step = self.steps[idx]
                        if step.get('operation') == 'move_x':
                            first_move_x_step = step
                            self.logger.debug(f"   Found move_x step at index {idx}: {step.get('description')}", category="execution")
                            break

                    # Execute the move_x immediately to position the motor
                    if first_move_x_step:
                        target_x = first_move_x_step.get('parameters', {}).get('position', 0)
                        self.logger.debug(f"TRANSITION: Immediately moving X motor to {target_x}cm", category="execution")
                        self.hardware.move_x(target_x)
                        self.logger.success(f"TRANSITION: X motor now at {self.hardware.get_current_x()}cm", category="execution")

                    # Force clear sensor override and update position display
                    if hasattr(self, 'canvas_manager') and self.canvas_manager:
                        self.logger.debug("TRANSITION: Setting canvas motor_operation_mode to 'rows'", category="execution")
                        self.canvas_manager.set_motor_operation_mode("rows")

                        self.logger.debug("TRANSITION: Clearing sensor override", category="execution")
                        self.canvas_manager.sensor_override_active = False
                        if hasattr(self.canvas_manager, 'sensor_override_timer') and self.canvas_manager.sensor_override_timer:
                            import tkinter as tk
                            # Safe way to get root without circular import
                            if hasattr(self.canvas_manager, 'main_app') and hasattr(self.canvas_manager.main_app, 'root'):
                                self.canvas_manager.main_app.root.after_cancel(self.canvas_manager.sensor_override_timer)
                                self.canvas_manager.sensor_override_timer = None

                        self.logger.debug("TRANSITION: Forcing position display update with new X position", category="execution")
                        # Force multiple updates to ensure canvas refreshes with new position
                        self.canvas_manager.update_position_display()
                        self.logger.success("Position display updated after transition - X motor should show at target position", category="execution")

                    # Auto-dismiss alert and resume execution
                    self._update_status("transition_complete", {
                        'message': 'Rows motor door CLOSED - resuming rows operations'
                    })

                    # Resume execution automatically
                    self.is_paused = False
                    self.pause_event.set()
                    return True
                else:
                    self.logger.warning("Row marker position unstable - continuing to wait...", category="execution")
                    continue

            # Update status with current limit switch state (for GUI updates)
            self._update_status("transition_waiting", {
                'limit_switch_state': limit_switch_state
            })

            # Check every 500ms for responsive monitoring (increased from 200ms for less spam)
            time.sleep(timing_settings.get("transition_monitor_interval", 0.5))

        # Execution was stopped during transition
        self.logger.info("Execution stopped during lines→rows transition", category="execution")
        self.in_transition = False  # Clear transition flag
        return False

    def get_execution_status(self):
        """Get current execution status"""
        return {
            'is_running': self.is_running,
            'is_paused': self.is_paused,
            'current_step': self.current_step_index,
            'total_steps': len(self.steps),
            'progress': (self.current_step_index / len(self.steps) * 100) if self.steps else 0,
            'start_time': self.start_time,
            'elapsed_time': time.time() - self.start_time if self.start_time else 0,
            'steps_completed': len(self.step_results),
            'current_step_description': self.steps[self.current_step_index]['description']
                                      if self.current_step_index < len(self.steps) else None
        }

    def get_step_results(self):
        """Get results of completed steps"""
        return self.step_results

    def get_execution_summary(self):
        """Get execution summary"""
        if not self.step_results:
            return None

        successful_steps = sum(1 for result in self.step_results if result['result'].get('success', False))
        failed_steps = len(self.step_results) - successful_steps

        total_time = self.end_time - self.start_time if self.end_time and self.start_time else 0

        return {
            'total_steps': len(self.steps),
            'completed_steps': len(self.step_results),
            'successful_steps': successful_steps,
            'failed_steps': failed_steps,
            'execution_time': total_time,
            'average_step_time': total_time / len(self.step_results) if self.step_results else 0
        }

# Convenience functions for simple usage
def execute_steps_sync(steps, status_callback=None):
    """Execute steps synchronously (blocking) - for simple scripts"""
    engine = ExecutionEngine()
    if status_callback:
        engine.set_status_callback(status_callback)

    engine.load_steps(steps)
    engine.start_execution()

    # Wait for completion
    while engine.is_running:
        time.sleep(0.1)

    return engine.get_execution_summary()

def create_simple_engine():
    """Create a simple execution engine for basic usage"""
    return ExecutionEngine()

if __name__ == "__main__":
    # Test with simple steps
    test_steps = [
        {'operation': 'move_x', 'parameters': {'position': 25.0}, 'description': 'Move to X position 25cm'},
        {'operation': 'move_y', 'parameters': {'position': 50.0}, 'description': 'Move to Y position 50cm'},
        {'operation': 'tool_action', 'parameters': {'tool': 'line_marker', 'action': 'down'}, 'description': 'Lower line marker'},
        {'operation': 'tool_action', 'parameters': {'tool': 'line_marker', 'action': 'up'}, 'description': 'Raise line marker'},
    ]

    # Initialize logger for test execution
    test_logger = get_logger()
    test_logger.info("=== EXECUTION ENGINE TEST ===", category="execution")

    def test_callback(status, info=None):
        if status == "executing" and info:
            progress = info.get('progress', 0)
            description = info.get('step_description', '')
            test_logger.info(f"Progress: {progress:.1f}% - {description}", category="execution")

    # Test synchronous execution
    test_logger.info("Testing synchronous execution:", category="execution")
    summary = execute_steps_sync(test_steps, test_callback)

    if summary:
        test_logger.info(f"Execution Summary:", category="execution")
        test_logger.info(f"  Total steps: {summary['total_steps']}", category="execution")
        test_logger.info(f"  Successful: {summary['successful_steps']}", category="execution")
        test_logger.info(f"  Failed: {summary['failed_steps']}", category="execution")
        test_logger.info(f"  Execution time: {summary['execution_time']:.2f}s", category="execution")

    test_logger.success("Execution engine test complete!", category="execution")