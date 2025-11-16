#!/usr/bin/env python3

"""
GRBL Command Library
====================

Structured command definitions for GRBL 1.1 CNC control.
Use this module to generate G-code commands and create GUI interfaces.

Usage:
    from hardware.grbl_commands import MOTION_COMMANDS, SYSTEM_COMMANDS, generate_gcode

    # Get command info
    cmd = MOTION_COMMANDS['G0']
    # cmd['description'] can be accessed programmatically

    # Generate G-code
    gcode = generate_gcode('G0', X=50, Y=35)
"""

import sys
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

# Add parent directory to path for logger import when running as main
if __name__ == '__main__':
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.logger import get_logger


@dataclass
class GCodeCommand:
    """G-code command definition"""
    code: str
    name: str
    description: str
    category: str
    parameters: List[str]
    example: str
    modal_group: Optional[str] = None
    is_modal: bool = True


# ============================================================================
# MOTION COMMANDS
# ============================================================================

MOTION_COMMANDS = {
    'G0': {
        'code': 'G0',
        'name': 'Rapid Positioning',
        'description': 'Move to position at maximum rapid rate (no cutting)',
        'category': 'Motion',
        'parameters': ['X', 'Y', 'Z'],
        'example': 'G0 X50 Y35',
        'modal_group': 'Motion',
        'is_modal': True,
        'usage': 'Fast positioning when not cutting'
    },
    'G1': {
        'code': 'G1',
        'name': 'Linear Interpolation',
        'description': 'Move to position at specified feed rate',
        'category': 'Motion',
        'parameters': ['X', 'Y', 'Z', 'F'],
        'example': 'G1 X50 Y35 F1000',
        'modal_group': 'Motion',
        'is_modal': True,
        'usage': 'Controlled movement for cutting/marking'
    },
    'G2': {
        'code': 'G2',
        'name': 'Clockwise Arc',
        'description': 'Move in a clockwise arc',
        'category': 'Motion',
        'parameters': ['X', 'Y', 'I', 'J', 'R', 'F'],
        'example': 'G2 X10 Y10 I5 J0 F500',
        'modal_group': 'Motion',
        'is_modal': True,
        'usage': 'Create circular paths (clockwise)'
    },
    'G3': {
        'code': 'G3',
        'name': 'Counter-Clockwise Arc',
        'description': 'Move in a counter-clockwise arc',
        'category': 'Motion',
        'parameters': ['X', 'Y', 'I', 'J', 'R', 'F'],
        'example': 'G3 X10 Y10 I5 J0 F500',
        'modal_group': 'Motion',
        'is_modal': True,
        'usage': 'Create circular paths (counter-clockwise)'
    },
    'G38.2': {
        'code': 'G38.2',
        'name': 'Probe Toward (Error)',
        'description': 'Probe toward workpiece, error on contact',
        'category': 'Motion',
        'parameters': ['X', 'Y', 'Z', 'F'],
        'example': 'G38.2 Z-10 F100',
        'modal_group': 'Motion',
        'is_modal': True,
        'usage': 'Tool length measurement, probing'
    },
    'G38.3': {
        'code': 'G38.3',
        'name': 'Probe Toward (No Error)',
        'description': 'Probe toward workpiece, no error on contact',
        'category': 'Motion',
        'parameters': ['X', 'Y', 'Z', 'F'],
        'example': 'G38.3 Z-10 F100',
        'modal_group': 'Motion',
        'is_modal': True,
        'usage': 'Safe probing without error'
    },
    'G38.4': {
        'code': 'G38.4',
        'name': 'Probe Away (Error)',
        'description': 'Probe away from workpiece, error on loss',
        'category': 'Motion',
        'parameters': ['X', 'Y', 'Z', 'F'],
        'example': 'G38.4 Z10 F100',
        'modal_group': 'Motion',
        'is_modal': True,
        'usage': 'Probe away with error checking'
    },
    'G38.5': {
        'code': 'G38.5',
        'name': 'Probe Away (No Error)',
        'description': 'Probe away from workpiece, no error',
        'category': 'Motion',
        'parameters': ['X', 'Y', 'Z', 'F'],
        'example': 'G38.5 Z10 F100',
        'modal_group': 'Motion',
        'is_modal': True,
        'usage': 'Safe probe away'
    },
    'G80': {
        'code': 'G80',
        'name': 'Cancel Motion Mode',
        'description': 'Cancel active motion mode',
        'category': 'Motion',
        'parameters': [],
        'example': 'G80',
        'modal_group': 'Motion',
        'is_modal': True,
        'usage': 'Stop motion mode'
    }
}


# ============================================================================
# WORK COORDINATE SYSTEMS
# ============================================================================

COORDINATE_COMMANDS = {
    'G54': {
        'code': 'G54',
        'name': 'Work Coordinate System 1',
        'description': 'Select work coordinate system 1 (default)',
        'category': 'Coordinates',
        'parameters': [],
        'example': 'G54',
        'modal_group': 'Coordinate',
        'is_modal': True
    },
    'G55': {
        'code': 'G55',
        'name': 'Work Coordinate System 2',
        'description': 'Select work coordinate system 2',
        'category': 'Coordinates',
        'parameters': [],
        'example': 'G55',
        'modal_group': 'Coordinate',
        'is_modal': True
    },
    'G56': {
        'code': 'G56',
        'name': 'Work Coordinate System 3',
        'description': 'Select work coordinate system 3',
        'category': 'Coordinates',
        'parameters': [],
        'example': 'G56',
        'modal_group': 'Coordinate',
        'is_modal': True
    },
    'G57': {
        'code': 'G57',
        'name': 'Work Coordinate System 4',
        'description': 'Select work coordinate system 4',
        'category': 'Coordinates',
        'parameters': [],
        'example': 'G57',
        'modal_group': 'Coordinate',
        'is_modal': True
    },
    'G58': {
        'code': 'G58',
        'name': 'Work Coordinate System 5',
        'description': 'Select work coordinate system 5',
        'category': 'Coordinates',
        'parameters': [],
        'example': 'G58',
        'modal_group': 'Coordinate',
        'is_modal': True
    },
    'G59': {
        'code': 'G59',
        'name': 'Work Coordinate System 6',
        'description': 'Select work coordinate system 6',
        'category': 'Coordinates',
        'parameters': [],
        'example': 'G59',
        'modal_group': 'Coordinate',
        'is_modal': True
    },
    'G10_L2': {
        'code': 'G10 L2',
        'name': 'Set Work Coordinate Offset',
        'description': 'Set work coordinate system offset to values',
        'category': 'Coordinates',
        'parameters': ['P', 'X', 'Y', 'Z'],
        'example': 'G10 L2 P1 X0 Y0',
        'modal_group': 'Non-Modal',
        'is_modal': False,
        'usage': 'P1-P6 for G54-G59'
    },
    'G10_L20': {
        'code': 'G10 L20',
        'name': 'Set Work Coordinate by Position',
        'description': 'Set work coordinate so current position becomes value',
        'category': 'Coordinates',
        'parameters': ['P', 'X', 'Y', 'Z'],
        'example': 'G10 L20 P1 X0 Y0',
        'modal_group': 'Non-Modal',
        'is_modal': False,
        'usage': 'Zero work coordinate at current position'
    },
    'G28': {
        'code': 'G28',
        'name': 'Go to Predefined Position 1',
        'description': 'Move to stored position 1',
        'category': 'Coordinates',
        'parameters': ['X', 'Y', 'Z'],
        'example': 'G28',
        'modal_group': 'Non-Modal',
        'is_modal': False
    },
    'G28.1': {
        'code': 'G28.1',
        'name': 'Set Predefined Position 1',
        'description': 'Save current position as position 1',
        'category': 'Coordinates',
        'parameters': [],
        'example': 'G28.1',
        'modal_group': 'Non-Modal',
        'is_modal': False
    },
    'G30': {
        'code': 'G30',
        'name': 'Go to Predefined Position 2',
        'description': 'Move to stored position 2',
        'category': 'Coordinates',
        'parameters': ['X', 'Y', 'Z'],
        'example': 'G30',
        'modal_group': 'Non-Modal',
        'is_modal': False
    },
    'G30.1': {
        'code': 'G30.1',
        'name': 'Set Predefined Position 2',
        'description': 'Save current position as position 2',
        'category': 'Coordinates',
        'parameters': [],
        'example': 'G30.1',
        'modal_group': 'Non-Modal',
        'is_modal': False
    },
    'G53': {
        'code': 'G53',
        'name': 'Machine Coordinate Move',
        'description': 'Move in absolute machine coordinates',
        'category': 'Coordinates',
        'parameters': ['X', 'Y', 'Z'],
        'example': 'G53 G0 X0 Y0',
        'modal_group': 'Non-Modal',
        'is_modal': False,
        'usage': 'Must be on same line as motion command'
    },
    'G92': {
        'code': 'G92',
        'name': 'Set Work Coordinate Offset',
        'description': 'Set temporary coordinate offset',
        'category': 'Coordinates',
        'parameters': ['X', 'Y', 'Z'],
        'example': 'G92 X0 Y0',
        'modal_group': 'Non-Modal',
        'is_modal': False,
        'usage': 'Non-persistent, resets on power cycle'
    },
    'G92.1': {
        'code': 'G92.1',
        'name': 'Clear G92 Offset',
        'description': 'Remove G92 coordinate offset',
        'category': 'Coordinates',
        'parameters': [],
        'example': 'G92.1',
        'modal_group': 'Non-Modal',
        'is_modal': False
    }
}


# ============================================================================
# DISTANCE AND FEED RATE MODES
# ============================================================================

MODE_COMMANDS = {
    'G90': {
        'code': 'G90',
        'name': 'Absolute Distance Mode',
        'description': 'All positions are absolute (from work zero)',
        'category': 'Distance',
        'parameters': [],
        'example': 'G90',
        'modal_group': 'Distance',
        'is_modal': True
    },
    'G91': {
        'code': 'G91',
        'name': 'Incremental Distance Mode',
        'description': 'All positions are relative (from current position)',
        'category': 'Distance',
        'parameters': [],
        'example': 'G91',
        'modal_group': 'Distance',
        'is_modal': True
    },
    'G93': {
        'code': 'G93',
        'name': 'Inverse Time Feed Mode',
        'description': 'Feed rate is 1/time to complete move',
        'category': 'Feed Rate',
        'parameters': [],
        'example': 'G93',
        'modal_group': 'Feed Rate',
        'is_modal': True
    },
    'G94': {
        'code': 'G94',
        'name': 'Units Per Minute Mode',
        'description': 'Feed rate in units per minute (default)',
        'category': 'Feed Rate',
        'parameters': [],
        'example': 'G94',
        'modal_group': 'Feed Rate',
        'is_modal': True
    }
}


# ============================================================================
# UNITS AND PLANE SELECTION
# ============================================================================

UNIT_COMMANDS = {
    'G20': {
        'code': 'G20',
        'name': 'Inches',
        'description': 'Set units to inches',
        'category': 'Units',
        'parameters': [],
        'example': 'G20',
        'modal_group': 'Units',
        'is_modal': True
    },
    'G21': {
        'code': 'G21',
        'name': 'Millimeters',
        'description': 'Set units to millimeters (default)',
        'category': 'Units',
        'parameters': [],
        'example': 'G21',
        'modal_group': 'Units',
        'is_modal': True
    },
    'G17': {
        'code': 'G17',
        'name': 'XY Plane',
        'description': 'Select XY plane for arcs (default)',
        'category': 'Plane',
        'parameters': [],
        'example': 'G17',
        'modal_group': 'Plane',
        'is_modal': True
    },
    'G18': {
        'code': 'G18',
        'name': 'XZ Plane',
        'description': 'Select XZ plane for arcs',
        'category': 'Plane',
        'parameters': [],
        'example': 'G18',
        'modal_group': 'Plane',
        'is_modal': True
    },
    'G19': {
        'code': 'G19',
        'name': 'YZ Plane',
        'description': 'Select YZ plane for arcs',
        'category': 'Plane',
        'parameters': [],
        'example': 'G19',
        'modal_group': 'Plane',
        'is_modal': True
    }
}


# ============================================================================
# SPINDLE (TOOL) COMMANDS
# ============================================================================

SPINDLE_COMMANDS = {
    'M3': {
        'code': 'M3',
        'name': 'Spindle On (CW)',
        'description': 'Start spindle clockwise',
        'category': 'Spindle',
        'parameters': ['S'],
        'example': 'M3 S1000',
        'modal_group': 'Spindle',
        'is_modal': True
    },
    'M4': {
        'code': 'M4',
        'name': 'Spindle On (CCW)',
        'description': 'Start spindle counter-clockwise',
        'category': 'Spindle',
        'parameters': ['S'],
        'example': 'M4 S1000',
        'modal_group': 'Spindle',
        'is_modal': True
    },
    'M5': {
        'code': 'M5',
        'name': 'Spindle Off',
        'description': 'Stop spindle',
        'category': 'Spindle',
        'parameters': [],
        'example': 'M5',
        'modal_group': 'Spindle',
        'is_modal': True
    }
}


# ============================================================================
# COOLANT COMMANDS
# ============================================================================

COOLANT_COMMANDS = {
    'M7': {
        'code': 'M7',
        'name': 'Mist Coolant On',
        'description': 'Enable mist coolant',
        'category': 'Coolant',
        'parameters': [],
        'example': 'M7',
        'modal_group': 'Coolant',
        'is_modal': True
    },
    'M8': {
        'code': 'M8',
        'name': 'Flood Coolant On',
        'description': 'Enable flood coolant',
        'category': 'Coolant',
        'parameters': [],
        'example': 'M8',
        'modal_group': 'Coolant',
        'is_modal': True
    },
    'M9': {
        'code': 'M9',
        'name': 'Coolant Off',
        'description': 'Disable all coolant',
        'category': 'Coolant',
        'parameters': [],
        'example': 'M9',
        'modal_group': 'Coolant',
        'is_modal': True
    }
}


# ============================================================================
# PROGRAM CONTROL
# ============================================================================

PROGRAM_COMMANDS = {
    'M0': {
        'code': 'M0',
        'name': 'Program Pause',
        'description': 'Pause program (requires cycle start)',
        'category': 'Program',
        'parameters': [],
        'example': 'M0',
        'modal_group': 'Program',
        'is_modal': False
    },
    'M1': {
        'code': 'M1',
        'name': 'Optional Pause',
        'description': 'Pause if optional stop enabled',
        'category': 'Program',
        'parameters': [],
        'example': 'M1',
        'modal_group': 'Program',
        'is_modal': False
    },
    'M2': {
        'code': 'M2',
        'name': 'Program End',
        'description': 'End program and reset',
        'category': 'Program',
        'parameters': [],
        'example': 'M2',
        'modal_group': 'Program',
        'is_modal': False
    },
    'M30': {
        'code': 'M30',
        'name': 'Program End & Rewind',
        'description': 'End program and rewind',
        'category': 'Program',
        'parameters': [],
        'example': 'M30',
        'modal_group': 'Program',
        'is_modal': False
    },
    'G4': {
        'code': 'G4',
        'name': 'Dwell/Pause',
        'description': 'Pause for specified time',
        'category': 'Program',
        'parameters': ['P'],
        'example': 'G4 P2.5',
        'modal_group': 'Non-Modal',
        'is_modal': False,
        'usage': 'P = seconds'
    }
}


# ============================================================================
# GRBL SYSTEM COMMANDS
# ============================================================================

SYSTEM_COMMANDS = {
    '$$': {
        'code': '$$',
        'name': 'View Settings',
        'description': 'Display all GRBL settings',
        'category': 'System',
        'parameters': [],
        'example': '$$',
        'response': '$0=10\n$1=25\n...'
    },
    '$#': {
        'code': '$#',
        'name': 'View Offsets',
        'description': 'Display coordinate system offsets',
        'category': 'System',
        'parameters': [],
        'example': '$#',
        'response': '[G54:0.000,0.000,0.000]'
    },
    '$G': {
        'code': '$G',
        'name': 'View Parser State',
        'description': 'Display current G-code modal state',
        'category': 'System',
        'parameters': [],
        'example': '$G',
        'response': '[GC:G0 G54 G17 G21 G90 G94 M5 M9 T0 F0 S0]'
    },
    '$I': {
        'code': '$I',
        'name': 'View Build Info',
        'description': 'Display GRBL version',
        'category': 'System',
        'parameters': [],
        'example': '$I',
        'response': '[VER:1.1h.20190825:]'
    },
    '$N': {
        'code': '$N',
        'name': 'View Startup Blocks',
        'description': 'Display startup G-code',
        'category': 'System',
        'parameters': [],
        'example': '$N'
    },
    '$X': {
        'code': '$X',
        'name': 'Unlock/Kill Alarm',
        'description': 'Clear alarm lock state',
        'category': 'System',
        'parameters': [],
        'example': '$X',
        'usage': 'Required after homing alarm'
    },
    '$H': {
        'code': '$H',
        'name': 'Run Homing',
        'description': 'Execute homing cycle',
        'category': 'System',
        'parameters': [],
        'example': '$H',
        'usage': 'May take 10-30 seconds'
    },
    '$C': {
        'code': '$C',
        'name': 'Check Mode',
        'description': 'Enable G-code check mode (no motion)',
        'category': 'System',
        'parameters': [],
        'example': '$C',
        'usage': 'Exit with Ctrl-X'
    },
    '$RST=$': {
        'code': '$RST=$',
        'name': 'Reset Settings',
        'description': 'Reset GRBL to factory defaults',
        'category': 'System',
        'parameters': [],
        'example': '$RST=$',
        'usage': 'WARNING: Erases all settings'
    },
    '$RST=#': {
        'code': '$RST=#',
        'name': 'Reset Offsets',
        'description': 'Reset all coordinate offsets',
        'category': 'System',
        'parameters': [],
        'example': '$RST=#'
    },
    '$SLP': {
        'code': '$SLP',
        'name': 'Sleep Mode',
        'description': 'Enter low power mode',
        'category': 'System',
        'parameters': [],
        'example': '$SLP'
    }
}


# ============================================================================
# REALTIME COMMANDS
# ============================================================================

REALTIME_COMMANDS = {
    '?': {
        'code': '?',
        'name': 'Status Query',
        'description': 'Request machine status',
        'category': 'Realtime',
        'char': '?',
        'hex': '0x3F',
        'response': '<Idle|MPos:0.000,0.000,0.000|WPos:0.000,0.000,0.000>'
    },
    '~': {
        'code': '~',
        'name': 'Cycle Start/Resume',
        'description': 'Resume from feed hold',
        'category': 'Realtime',
        'char': '~',
        'hex': '0x7E'
    },
    '!': {
        'code': '!',
        'name': 'Feed Hold',
        'description': 'Pause all motion',
        'category': 'Realtime',
        'char': '!',
        'hex': '0x21'
    },
    'CTRL_X': {
        'code': 'Ctrl-X',
        'name': 'Soft Reset',
        'description': 'Reset GRBL (emergency stop)',
        'category': 'Realtime',
        'char': '\x18',
        'hex': '0x18'
    },
    'JOG_CANCEL': {
        'code': 'Jog Cancel',
        'name': 'Cancel Jog',
        'description': 'Cancel all jog motions',
        'category': 'Realtime',
        'char': '\x85',
        'hex': '0x85'
    }
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def generate_gcode(command: str, **params) -> str:
    """
    Generate G-code command string with parameters.

    Args:
        command: G-code command (e.g., 'G0', 'G1', 'M3')
        **params: Command parameters (e.g., X=50, Y=35, F=1000)

    Returns:
        Formatted G-code string

    Example:
        >>> generate_gcode('G0', X=50, Y=35)
        'G0 X50 Y35'
        >>> generate_gcode('G1', X=100, Y=50, F=1000)
        'G1 X100 Y50 F1000'
    """
    parts = [command]

    # Add parameters in standard order
    param_order = ['X', 'Y', 'Z', 'I', 'J', 'K', 'R', 'P', 'F', 'S']

    for param in param_order:
        if param in params:
            value = params[param]
            if isinstance(value, float):
                parts.append(f"{param}{value:.3f}")
            else:
                parts.append(f"{param}{value}")

    # Add any remaining parameters
    for param, value in params.items():
        if param not in param_order:
            if isinstance(value, float):
                parts.append(f"{param}{value:.3f}")
            else:
                parts.append(f"{param}{value}")

    return ' '.join(parts)


def generate_jog_command(axis: str, distance: float, feed_rate: int,
                        absolute: bool = False, machine_coords: bool = False) -> str:
    """
    Generate GRBL jog command.

    Args:
        axis: Axis to jog ('X', 'Y', or 'Z')
        distance: Distance to jog (in current units)
        feed_rate: Feed rate (mm/min or inch/min)
        absolute: Use absolute positioning (default: incremental)
        machine_coords: Use machine coordinates (default: work coords)

    Returns:
        GRBL jog command string

    Example:
        >>> generate_jog_command('X', 10, 500)
        '$J=G91 X10.0 F500'
        >>> generate_jog_command('Y', 5, 1000, absolute=True)
        '$J=G90 Y5.0 F1000'
    """
    parts = ['$J=']

    # Distance mode
    if absolute:
        parts.append('G90')
    else:
        parts.append('G91')

    # Machine coordinates
    if machine_coords:
        parts.append('G53')

    # Axis and distance
    parts.append(f'{axis}{distance:.3f}')

    # Feed rate (required)
    parts.append(f'F{feed_rate}')

    return ' '.join(parts)


def get_commands_by_category(category: str) -> Dict[str, Dict]:
    """
    Get all commands in a specific category.

    Args:
        category: Command category

    Returns:
        Dictionary of commands in category
    """
    all_commands = {}
    all_commands.update(MOTION_COMMANDS)
    all_commands.update(COORDINATE_COMMANDS)
    all_commands.update(MODE_COMMANDS)
    all_commands.update(UNIT_COMMANDS)
    all_commands.update(SPINDLE_COMMANDS)
    all_commands.update(COOLANT_COMMANDS)
    all_commands.update(PROGRAM_COMMANDS)
    all_commands.update(SYSTEM_COMMANDS)
    all_commands.update(REALTIME_COMMANDS)

    return {
        code: cmd for code, cmd in all_commands.items()
        if cmd.get('category') == category
    }


def get_all_commands() -> Dict[str, Dict]:
    """Get all GRBL commands."""
    all_commands = {}
    all_commands.update(MOTION_COMMANDS)
    all_commands.update(COORDINATE_COMMANDS)
    all_commands.update(MODE_COMMANDS)
    all_commands.update(UNIT_COMMANDS)
    all_commands.update(SPINDLE_COMMANDS)
    all_commands.update(COOLANT_COMMANDS)
    all_commands.update(PROGRAM_COMMANDS)
    all_commands.update(SYSTEM_COMMANDS)
    all_commands.update(REALTIME_COMMANDS)
    return all_commands


def get_categories() -> List[str]:
    """Get list of all command categories."""
    return [
        'Motion',
        'Coordinates',
        'Distance',
        'Feed Rate',
        'Units',
        'Plane',
        'Spindle',
        'Coolant',
        'Program',
        'System',
        'Realtime'
    ]


# ============================================================================
# COMMON COMMAND SEQUENCES
# ============================================================================

COMMAND_SEQUENCES = {
    'initialize': {
        'name': 'Initialize Machine',
        'description': 'Initialize GRBL to standard settings',
        'commands': [
            'G21',  # Millimeters
            'G90',  # Absolute positioning
            'G54',  # Work coordinate system 1
            'G17',  # XY plane
        ]
    },
    'home': {
        'name': 'Home Machine',
        'description': 'Home all axes',
        'commands': ['$H']
    },
    'zero_current': {
        'name': 'Zero at Current Position',
        'description': 'Set current position as work zero',
        'commands': ['G10 L20 P1 X0 Y0']
    },
    'go_zero': {
        'name': 'Go to Work Zero',
        'description': 'Move to work coordinate zero',
        'commands': ['G90 G0 X0 Y0']
    },
    'unlock': {
        'name': 'Unlock Machine',
        'description': 'Clear alarm state',
        'commands': ['$X']
    },
    'emergency_stop': {
        'name': 'Emergency Stop',
        'description': 'Immediate stop and reset',
        'commands': ['!', '\x18']  # Feed hold then soft reset
    }
}


# ============================================================================
# GUI PRESET POSITIONS
# ============================================================================

PRESET_POSITIONS = {
    'origin': {'name': 'Origin', 'X': 0, 'Y': 0},
    'center': {'name': 'Center', 'X': 50, 'Y': 35},
    'top_left': {'name': 'Top Left', 'X': 0, 'Y': 0},
    'top_right': {'name': 'Top Right', 'X': 100, 'Y': 0},
    'bottom_left': {'name': 'Bottom Left', 'X': 0, 'Y': 70},
    'bottom_right': {'name': 'Bottom Right', 'X': 100, 'Y': 70},
}


if __name__ == '__main__':
    """Test command generation"""
    logger = get_logger()

    logger.info("GRBL Command Library Test", category="grbl")
    logger.info("=" * 60, category="grbl")

    # Test G-code generation
    logger.info("\nG-code Generation:", category="grbl")
    logger.info(f"  {generate_gcode('G0', X=50, Y=35)}", category="grbl")
    logger.info(f"  {generate_gcode('G1', X=100, Y=50, F=1000)}", category="grbl")
    logger.info(f"  {generate_gcode('G2', X=10, Y=10, I=5, J=0, F=500)}", category="grbl")

    # Test jog commands
    logger.info("\nJog Commands:", category="grbl")
    logger.info(f"  {generate_jog_command('X', 10, 500)}", category="grbl")
    logger.info(f"  {generate_jog_command('Y', -5, 1000)}", category="grbl")
    logger.info(f"  {generate_jog_command('X', 50, 1000, absolute=True)}", category="grbl")

    # List categories
    logger.info("\nCommand Categories:", category="grbl")
    for category in get_categories():
        commands = get_commands_by_category(category)
        logger.info(f"  {category}: {len(commands)} commands", category="grbl")

    # Show some commands
    logger.info("\nSample Commands:", category="grbl")
    for code, cmd in list(MOTION_COMMANDS.items())[:3]:
        logger.info(f"  {code}: {cmd['name']}", category="grbl")
        logger.info(f"    Description: {cmd['description']}", category="grbl")
        logger.info(f"    Example: {cmd['example']}", category="grbl")

    logger.info("\n" + "=" * 60, category="grbl")
