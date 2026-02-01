#!/usr/bin/env python3

"""
Safety System for CNC Scratch Desk Control
Prevents dangerous operations that could damage the hardware

This module loads safety rules from config/safety_rules.json and evaluates them
dynamically, allowing rules to be added/modified via the admin tool.
"""

import json
import os
import time
from hardware.interfaces.hardware_factory import get_hardware_interface
from core.logger import get_logger


class SafetyViolation(Exception):
    """Exception raised when a safety condition is violated"""
    def __init__(self, message, safety_code=None):
        super().__init__(message)
        self.safety_code = safety_code
        self.message = message


class SafetyRulesManager:
    """Manages loading and evaluation of safety rules from JSON config"""

    RULES_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'safety_rules.json')

    def __init__(self, hardware):
        self.hardware = hardware
        self.rules_data = {}
        self.rules = []
        self.logger = get_logger()
        self.load_rules()

    def load_rules(self):
        """Load safety rules from JSON file"""
        try:
            if os.path.exists(self.RULES_FILE):
                with open(self.RULES_FILE, 'r', encoding='utf-8') as f:
                    self.rules_data = json.load(f)
                self.rules = self.rules_data.get("rules", [])
                self.logger.debug(f"Loaded {len(self.rules)} safety rules from {self.RULES_FILE}", category="safety")
            else:
                self.logger.warning(f"Safety rules file not found: {self.RULES_FILE}", category="safety")
                self.rules_data = {"global_enabled": True, "rules": []}
                self.rules = []
        except Exception as e:
            self.logger.error(f"Error loading safety rules: {e}", category="safety")
            self.rules_data = {"global_enabled": True, "rules": []}
            self.rules = []

    def reload_rules(self):
        """Reload rules from file (called when rules are updated)"""
        self.load_rules()

    def is_globally_enabled(self):
        """Check if safety system is globally enabled"""
        return self.rules_data.get("global_enabled", True)

    def get_hardware_state(self):
        """Get current hardware state for condition evaluation"""
        return {
            # Piston states
            "pistons": {
                "row_marker": self.hardware.get_row_marker_state(),
                "row_cutter": self.hardware.get_row_cutter_state(),
                "line_marker": self.hardware.get_line_marker_state(),
                "line_cutter": self.hardware.get_line_cutter_state(),
                "line_motor": self.hardware.get_line_motor_piston_state(),
            },
            # Sensor states
            "sensors": {
                "row_motor_limit_switch": self.hardware.get_row_motor_limit_switch(),
                # Add more sensors as needed
            },
            # Positions
            "positions": {
                "x_position": self.hardware.get_current_x(),
                "y_position": self.hardware.get_current_y(),
            }
        }

    def evaluate_condition(self, condition, state):
        """Evaluate a single condition against current hardware state"""
        cond_type = condition.get("type", "")
        source = condition.get("source", "")
        operator = condition.get("operator", "")
        expected_value = condition.get("value")

        # Get actual value based on condition type
        actual_value = None

        if cond_type == "piston":
            actual_value = state["pistons"].get(source)
        elif cond_type == "sensor":
            actual_value = state["sensors"].get(source)
        elif cond_type == "position":
            actual_value = state["positions"].get(source)

        # Debug logging for condition evaluation
        self.logger.debug(
            f"Safety condition: {cond_type}.{source} {operator} {expected_value} | Actual: {actual_value}",
            category="safety"
        )

        if actual_value is None:
            # Unknown source - condition not met
            self.logger.debug(f"  -> Unknown source '{source}', condition NOT met", category="safety")
            return False

        # Evaluate operator
        result = False
        if operator == "equals":
            # Handle numeric comparison
            if isinstance(expected_value, (int, float)):
                try:
                    result = float(actual_value) == float(expected_value)
                except (ValueError, TypeError):
                    result = str(actual_value).lower() == str(expected_value).lower()
            else:
                result = str(actual_value).lower() == str(expected_value).lower()
        elif operator == "not_equals":
            if isinstance(expected_value, (int, float)):
                try:
                    result = float(actual_value) != float(expected_value)
                except (ValueError, TypeError):
                    result = str(actual_value).lower() != str(expected_value).lower()
            else:
                result = str(actual_value).lower() != str(expected_value).lower()
        elif operator == "greater_than":
            try:
                result = float(actual_value) > float(expected_value)
            except (ValueError, TypeError):
                result = False
        elif operator == "less_than":
            try:
                result = float(actual_value) < float(expected_value)
            except (ValueError, TypeError):
                result = False

        self.logger.debug(f"  -> Condition result: {result}", category="safety")
        return result

    def evaluate_conditions(self, conditions, state):
        """Evaluate a conditions block (can be nested with AND/OR)"""
        if not conditions:
            return False

        operator = conditions.get("operator", "AND")
        items = conditions.get("items", [])

        if not items:
            return False

        results = []
        for item in items:
            if "operator" in item and "items" in item:
                # Nested condition group
                result = self.evaluate_conditions(item, state)
            else:
                # Simple condition
                result = self.evaluate_condition(item, state)
            results.append(result)

        # Apply logical operator
        if operator == "AND":
            return all(results)
        elif operator == "OR":
            return any(results)

        return False

    def check_operation_blocked(self, rule, operation, tool=None, is_setup=False):
        """Check if an operation is blocked by this rule"""
        blocked_ops = rule.get("blocked_operations", [])

        for block in blocked_ops:
            block_op = block.get("operation", "")

            # Check if operation matches
            if block_op != operation:
                continue

            # Check if setup movements are excluded
            if is_setup and block.get("exclude_setup", False):
                continue

            # For tool_action, check if specific tool is blocked
            if operation == "tool_action":
                blocked_tools = block.get("tools", [])
                if blocked_tools and tool:
                    if tool not in blocked_tools:
                        continue

            # Operation is blocked by this rule
            return True

        return False

    def evaluate_rules(self, step, is_setup=False):
        """
        Evaluate all enabled rules against a step

        Returns: (is_safe, violation) tuple
        - is_safe: True if step is safe, False if blocked
        - violation: SafetyViolation exception if blocked, None if safe
        """
        if not self.is_globally_enabled():
            return True, None

        # Reload rules to pick up any changes from admin tool
        self.load_rules()

        operation = step.get("operation", "")
        parameters = step.get("parameters", {})
        description = step.get("description", "")

        # Get tool for tool_action operations
        tool = parameters.get("tool") if operation == "tool_action" else None

        # Get current hardware state
        state = self.get_hardware_state()

        # Debug: Log step and hardware state
        self.logger.debug(f"Safety check for operation: {operation}", category="safety")
        self.logger.debug(f"  Hardware state - Pistons: {state['pistons']}", category="safety")
        self.logger.debug(f"  Hardware state - Sensors: {state['sensors']}", category="safety")

        # Sort rules by priority (lower number = higher priority)
        sorted_rules = sorted(self.rules, key=lambda r: r.get("priority", 50))

        for rule in sorted_rules:
            # Skip disabled rules
            if not rule.get("enabled", True):
                continue

            rule_name = rule.get("name", rule.get("id", "Unknown"))
            self.logger.debug(f"Evaluating rule: {rule_name}", category="safety")

            # Check if this rule's conditions are met (violation conditions)
            conditions = rule.get("conditions", {})
            conditions_met = self.evaluate_conditions(conditions, state)

            if not conditions_met:
                # Conditions not met - rule doesn't apply
                self.logger.debug(f"  -> Rule conditions NOT met, skipping", category="safety")
                continue

            self.logger.debug(f"  -> Rule conditions MET! Checking blocked operations...", category="safety")

            # Conditions are met - check if this operation is blocked
            if self.check_operation_blocked(rule, operation, tool, is_setup):
                # Create violation
                rule_name = rule.get("name", rule.get("id", "Unknown"))
                message = rule.get("message", f"Operation blocked by rule: {rule_name}")

                violation_msg = (
                    f"🚨 SAFETY VIOLATION: {rule_name}\n"
                    f"   Operation: {operation}\n"
                    f"   Description: {description}\n"
                    f"   Rule message: {message}"
                )

                # Note: Logging is done by the caller to avoid repeated logs during wait-and-retry
                return False, SafetyViolation(violation_msg, rule.get("id"))

        return True, None


class SafetySystem:
    """Hardware safety system to prevent dangerous operations"""

    def __init__(self):
        self.safety_enabled = True
        self.violations_log = []
        # Get hardware interface via factory
        self.hardware = get_hardware_interface()
        self.logger = get_logger()
        # Initialize rules manager
        self.rules_manager = SafetyRulesManager(self.hardware)

    def enable_safety(self):
        """Enable safety checks"""
        self.safety_enabled = True
        self.logger.info("Safety system ENABLED", category="safety")

    def disable_safety(self):
        """Disable safety checks (WARNING: Use only for debugging)"""
        self.safety_enabled = False
        self.logger.warning("Safety system DISABLED!", category="safety")

    def reload_rules(self):
        """Reload safety rules from file"""
        self.rules_manager.reload_rules()

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

        description = step.get('description', '')
        is_setup = self._is_setup_movement(description)

        # Evaluate all rules from JSON config
        is_safe, violation = self.rules_manager.evaluate_rules(step, is_setup)

        if not is_safe and violation:
            self.log_violation(violation.safety_code, violation.message)
            raise violation

        return True

    def log_violation(self, safety_code, message):
        """Log safety violation for debugging"""
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
            'global_enabled': self.rules_manager.is_globally_enabled(),
            'rules_count': len(self.rules_manager.rules),
            'recent_violations': len(self.violations_log),
            'row_marker_programmed': self.hardware.get_row_marker_state(),
            'row_marker_limit_switch': self.hardware.get_row_motor_limit_switch(),
            'current_position': {'x': self.hardware.get_current_x(), 'y': self.hardware.get_current_y()}
        }


# Global safety system instance
safety_system = SafetySystem()

# Module-level logger for standalone functions and main
module_logger = get_logger()


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


def reload_rules():
    """Convenience function to reload safety rules"""
    return safety_system.reload_rules()


if __name__ == "__main__":
    module_logger.info("Safety System Test", category="safety")
    module_logger.info("=" * 30, category="safety")

    # Test safety status
    status = get_safety_status()
    module_logger.debug(f"Safety enabled: {status['enabled']}", category="safety")
    module_logger.debug(f"Global enabled: {status['global_enabled']}", category="safety")
    module_logger.debug(f"Rules loaded: {status['rules_count']}", category="safety")
    module_logger.debug(f"Row marker limit_switch: {status['row_marker_limit_switch']}", category="safety")
    module_logger.debug(f"Current position: X={status['current_position']['x']}, Y={status['current_position']['y']}", category="safety")

    # Test Y-axis movement
    test_step = {
        'operation': 'move_y',
        'parameters': {'position': 25.0},
        'description': 'Test Y movement'
    }

    try:
        check_step_safety(test_step)
        module_logger.debug("Y-axis movement: SAFE", category="safety")
    except SafetyViolation as e:
        module_logger.warning(f"Safety violation: {e.safety_code}", category="safety")

    module_logger.info("Safety system test completed!", category="safety")
