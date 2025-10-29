#!/usr/bin/env python3

"""
Safety System for CNC Scratch Desk Control
Prevents dangerous operations that could damage the hardware
"""

from mock_hardware import (
    get_row_marker_state, get_row_motor_limit_switch,
    get_line_marker_state, get_line_cutter_state,
    get_current_x, get_current_y
)

class SafetyViolation(Exception):
    """Exception raised when a safety condition is violated"""
    def __init__(self, message, safety_code=None):
        super().__init__(message)
        self.safety_code = safety_code
        self.message = message

class SafetySystem:
    """Hardware safety system to prevent dangerous operations"""
    
    def __init__(self):
        self.safety_enabled = True
        self.violations_log = []
    
    def enable_safety(self):
        """Enable safety checks"""
        self.safety_enabled = True
        print("🛡️  Safety system ENABLED")
    
    def disable_safety(self):
        """Disable safety checks (WARNING: Use only for debugging)"""
        self.safety_enabled = False
        print("⚠️  WARNING: Safety system DISABLED!")
    
    def check_y_axis_movement_safety(self, target_y=None):
        """
        Check if Y-axis movement is safe
        
        SAFETY RULE: Lines axis (Y-axis) cannot move if row marker is DOWN
        Reason: Row marker lies across the lines axis when down
        """
        if not self.safety_enabled:
            return True
        
        # Check both programmed state and actual limit switch state
        row_marker_programmed = get_row_marker_state()  # Programmed position
        row_marker_limit = get_row_motor_limit_switch()  # Actual position from limit switch
        
        # Safety violation if either shows DOWN position
        if row_marker_programmed == "down" or row_marker_limit == "down":
            current_y = get_current_y()
            target_info = f" to {target_y}cm" if target_y is not None else ""
            
            violation_msg = (
                f"🚨 SAFETY VIOLATION: Cannot move Y-axis{target_info}!\n"
                f"   Reason: Row marker is DOWN and blocks the lines axis\n"
                f"   Current Y position: {current_y}cm\n"
                f"   Row marker programmed state: {row_marker_programmed.upper()}\n"
                f"   Row marker actual position: {row_marker_limit.upper()}\n"
                f"   ACTION REQUIRED: Raise the row marker before Y-axis movement"
            )
            
            self.log_violation("Y_AXIS_BLOCKED", violation_msg)
            raise SafetyViolation(violation_msg, "Y_AXIS_BLOCKED")
        
        return True
    
    def check_x_axis_movement_safety(self, target_x=None):
        """
        Check if X-axis movement is safe
        Currently no restrictions, but structure for future safety rules
        """
        if not self.safety_enabled:
            return True
        
        # No current restrictions on X-axis movement
        # This method exists for future safety rules
        return True
    
    def check_tool_operation_safety(self, tool, action):
        """
        Check if tool operation is safe
        Future: Add rules for tool conflicts
        """
        if not self.safety_enabled:
            return True
        
        # No current restrictions on tool operations
        # This method exists for future safety rules
        return True
    
    def check_step_safety(self, step):
        """
        Check safety for any step before execution
        
        Args:
            step: Step dictionary with operation, parameters, description
            
        Raises:
            SafetyViolation: If step would violate safety rules
        """
        if not self.safety_enabled:
            return True
        
        operation = step.get('operation', '')
        parameters = step.get('parameters', {})
        description = step.get('description', '')
        
        try:
            # SAFETY INTERLOCK: Check operation type and enforce door position rules
            if operation == 'move_y':
                # Distinguish between setup movements and actual operations
                if self._is_setup_movement(description):
                    # Setup movements are allowed regardless of door position
                    print(f"🔧 SETUP MOVEMENT: {description[:50]}... (allowed)")
                else:
                    # LINES OPERATIONS: Row marker MUST be UP (door closed)
                    self.check_lines_operation_safety(description)
                target_y = parameters.get('position')
                self.check_y_axis_movement_safety(target_y)
                
            elif operation == 'move_position':
                # Check if Y offset would cause Y movement
                y_offset = parameters.get('y_offset', 0.0)
                if y_offset != 0.0:
                    # LINES OPERATIONS: Row marker MUST be UP (door closed)  
                    self.check_lines_operation_safety(description)
                    current_y = get_current_y()
                    target_y = current_y + y_offset
                    self.check_y_axis_movement_safety(target_y)
                
                # Check X movement for rows operations
                x_offset = parameters.get('x_offset', 0.0)
                if x_offset != 0.0:
                    # ROWS OPERATIONS: Row marker MUST be DOWN (door open)
                    self.check_rows_operation_safety(description)
                    current_x = get_current_x()
                    target_x = current_x + x_offset
                    self.check_x_axis_movement_safety(target_x)
                    
            elif operation == 'move_x':
                # Distinguish between setup movements and actual operations
                if self._is_setup_movement(description):
                    # Setup movements are allowed regardless of door position
                    print(f"🔧 SETUP MOVEMENT: {description[:50]}... (allowed)")
                else:
                    # ROWS OPERATIONS: Row marker MUST be DOWN (door open)
                    self.check_rows_operation_safety(description)
                target_x = parameters.get('position')
                self.check_x_axis_movement_safety(target_x)
                
            elif operation == 'tool_action':
                tool = parameters.get('tool', '')
                action = parameters.get('action', '')
                
                # Check tool-specific safety rules
                if 'line_' in tool:
                    # LINES TOOLS: Row marker MUST be UP (door closed)
                    self.check_lines_operation_safety(description)
                elif 'row_' in tool:
                    # ROWS TOOLS: Row marker MUST be DOWN (door open)
                    self.check_rows_operation_safety(description)
                    
                self.check_tool_operation_safety(tool, action)
                
            elif operation == 'wait_sensor':
                # Sensor waits also need safety checks based on context
                if 'x_' in parameters.get('sensor', ''):
                    # X sensors used in lines operations - need door closed
                    self.check_lines_operation_safety(description)
                elif 'y_' in parameters.get('sensor', ''):
                    # Y sensors used in rows operations - need door open
                    self.check_rows_operation_safety(description)
                
            # Other operations (tool_positioning, etc.) are currently safe
            
            return True
            
        except SafetyViolation:
            # Re-raise safety violations
            raise
        except Exception as e:
            # Log unexpected errors but don't block execution
            print(f"⚠️  Warning: Safety check error for {operation}: {e}")
            return True
    
    def check_lines_operation_safety(self, description=""):
        """
        Check safety for LINES operations - row marker MUST be UP (door closed)
        
        SAFETY RULE: During lines operations, the row marker must be UP
        Reason: Lines motor operates with door closed for safety
        """
        if not self.safety_enabled:
            return True
        
        # Check both programmed state and actual limit switch state
        row_marker_programmed = get_row_marker_state()  # Programmed position
        row_marker_actual = get_row_motor_limit_switch()  # Actual position from limit switch
        
        # Safety violation if either shows DOWN position during lines operation
        if row_marker_programmed == "down" or row_marker_actual == "down":
            violation_msg = (
                f"🚨 LINES OPERATION SAFETY VIOLATION!\n"
                f"   Operation: {description}\n"
                f"   RULE VIOLATED: Row marker must be UP during lines operations\n"
                f"   Row marker programmed state: {row_marker_programmed.upper()}\n"
                f"   Row marker actual position: {row_marker_actual.upper()}\n"
                f"   ⚠️  IMMEDIATE ACTION REQUIRED: Close the rows door (set marker UP)\n"
                f"   🛡️  Lines motor movement BLOCKED to prevent damage"
            )
            
            self.log_violation("LINES_DOOR_OPEN", violation_msg)
            raise SafetyViolation(violation_msg, "LINES_DOOR_OPEN")
        
        return True
    
    def check_rows_operation_safety(self, description=""):
        """
        Check safety for ROWS operations - two safety rules:
        1. Door can only be CLOSED when Y motor is at position 0
        2. Line marker must be DOWN during rows operations

        SAFETY RULES:
        - Rows motor door can only be closed (limit switch DOWN) when Y motor is at 0
        - Line marker must be DOWN during rows operations
        Reason: Closing door with Y motor not at home position or line marker UP could cause collision/damage
        """
        if not self.safety_enabled:
            return True

        # Check actual limit switch state (door position sensor) and line marker state
        from mock_hardware import get_current_y, get_line_marker_state, get_row_motor_limit_switch
        row_marker_limit = get_row_motor_limit_switch()  # Actual position from limit switch
        current_y = get_current_y()  # Current Y motor position

        # Safety violation 1: Door is CLOSED (limit switch DOWN) and Y motor is NOT at position 0
        if row_marker_limit == "down" and current_y != 0:
            violation_msg = (
                f"🚨 ROWS MOTOR DOOR SAFETY VIOLATION!\n"
                f"   Operation: {description}\n"
                f"   RULE VIOLATED: Door can only be closed when lines motor (Y-axis) is at position 0\n"
                f"   Current Y position: {current_y:.1f}cm (must be 0cm to close door)\n"
                f"   Limit switch state: {row_marker_limit.upper()} (CLOSED)\n"
                f"   ⚠️  IMMEDIATE ACTION REQUIRED: Open the rows motor door (set limit switch to OFF)\n"
                f"   🛡️  Rows motor movement BLOCKED - door closed while motor not at home"
            )

            self.log_violation("ROWS_DOOR_CLOSED", violation_msg)
            raise SafetyViolation(violation_msg, "ROWS_DOOR_CLOSED")
        return True
    
    def _is_setup_movement(self, description):
        """
        Determine if a movement is a setup operation that should bypass safety checks
        
        Setup movements are positioning operations that prepare motors for actual work.
        These are allowed regardless of door position.
        """
        description_lower = description.lower()
        
        # Setup movement indicators
        setup_indicators = [
            'home position',
            'ensure',
            'move rows motor to home',
            'move lines motor to home', 
            'complete:',
            'init:',
            'position for repeat'
        ]
        
        return any(indicator in description_lower for indicator in setup_indicators)
    
    def log_violation(self, safety_code, message):
        """Log safety violation for debugging"""
        import time
        violation = {
            'timestamp': time.time(),
            'safety_code': safety_code,
            'message': message
        }
        self.violations_log.append(violation)
        
        # Keep only last 100 violations
        if len(self.violations_log) > 100:
            self.violations_log = self.violations_log[-100:]
    
    def get_violations_log(self):
        """Get recent safety violations"""
        return self.violations_log.copy()
    
    def clear_violations_log(self):
        """Clear violations log"""
        self.violations_log.clear()
    
    def get_safety_status(self):
        """Get current safety system status"""
        return {
            'enabled': self.safety_enabled,
            'recent_violations': len(self.violations_log),
            'row_marker_programmed': get_row_marker_state(),
            'row_marker_limit_switch': get_row_motor_limit_switch(),
            'current_position': {'x': get_current_x(), 'y': get_current_y()}
        }

# Global safety system instance
safety_system = SafetySystem()

def check_step_safety(step):
    """Convenience function to check step safety"""
    return safety_system.check_step_safety(step)

def get_safety_status():
    """Convenience function to get safety status"""
    return safety_system.get_safety_status()

def enable_safety():
    """Convenience function to enable safety"""
    return safety_system.enable_safety()

def disable_safety():
    """Convenience function to disable safety (DEBUG ONLY)"""
    return safety_system.disable_safety()

if __name__ == "__main__":
    print("Safety System Test")
    print("=" * 30)
    
    # Test safety status
    status = get_safety_status()
    print(f"Safety enabled: {status['enabled']}")
    print(f"Row marker limit_switch programmed: {status['row_marker_limit_switch']}")

    print(f"Current position: X={status['current_position']['x']}, Y={status['current_position']['y']}")
    
    # Test Y-axis movement with row marker up (should be safe)
    test_step_safe = {
        'operation': 'move_y',
        'parameters': {'position': 25.0},
        'description': 'Test Y movement with row marker up'
    }
    
    try:
        check_step_safety(test_step_safe)
        print("✓ Y-axis movement with row marker UP: SAFE")
    except SafetyViolation as e:
        print(f"✗ Safety violation: {e}")
    
    # Simulate row marker down and test Y-axis movement (should be unsafe)
    print("\nSimulating row marker DOWN...")
    from mock_hardware import set_row_marker_limit_switch
    set_row_marker_limit_switch("down")
    
    test_step_unsafe = {
        'operation': 'move_y', 
        'parameters': {'position': 30.0},
        'description': 'Test Y movement with row marker down'
    }
    
    try:
        check_step_safety(test_step_unsafe)
        print("✗ Y-axis movement with row marker DOWN: Should have been blocked!")
    except SafetyViolation as e:
        print("✓ Y-axis movement with row marker DOWN: Correctly blocked")
        print(f"   Violation: {e.safety_code}")
    
    print("\n✅ Safety system test completed!")