#!/usr/bin/env python3

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import time
import os
import json

# Import translation function
from core.translations import t

# Import our modules
from core.csv_parser import CSVParser
from core.step_generator import generate_complete_program_steps, get_step_count_summary
from core.execution_engine import ExecutionEngine
from core.machine_state import MachineState, get_state_manager
from hardware.interfaces.hardware_factory import get_hardware_interface

# Import GUI components
from gui.panels.left_panel import LeftPanel
from gui.panels.center_panel import CenterPanel
from gui.panels.right_panel import RightPanel
from gui.panels.hardware_status_panel import HardwareStatusPanel
from gui.panels.hardware_settings_panel import HardwareSettingsPanel
from gui.canvas.canvas_manager import CanvasManager
from gui.execution.execution_controller import ExecutionController
from core.logger import get_logger


class ScratchDeskGUI:
    """Main GUI application class"""

    def __init__(self, root):
        self.root = root
        self.root.title(t("Scratch Desk Control System"))
        self.root.geometry("1500x1000")
        self.root.minsize(1400, 950)
        self.root.resizable(True, True)
        self.logger = get_logger()

        # Try to maximize window if possible
        try:
            self.root.state('zoomed')  # Windows/Linux maximize
        except tk.TclError:
            try:
                self.root.attributes('-zoomed', True)  # Alternative maximize
            except tk.TclError:
                pass  # Fall back to normal size

        # Initialize hardware interface
        self.hardware = get_hardware_interface()

        # Initialize machine state manager
        self.state_manager = get_state_manager()
        self.state_manager.add_observer(self._on_machine_state_changed)

        # Load settings
        self.settings = self.load_settings()

        # Data storage
        self.programs = []
        self.current_program = None
        self.steps = []
        self.csv_parser = CSVParser()
        self.execution_engine = ExecutionEngine()
        self.current_file = None

        # GUI state
        self.operation_states = {
            'lines': {},      # Track line marking states: {1: 'pending', 2: 'completed', ...}
            'cuts': {},       # Track cutting states: {'top'/'bottom'/'left'/'right': 'pending'/'completed'}
            'pages': {}       # Track page states: {0: 'pending', 1: 'completed', ...}
        }

        # Canvas and drawing objects
        self.work_line_objects = {}  # Store line objects for dynamic updates
        self.canvas_objects = {}  # Store canvas objects for efficient updates
        self.canvas = None

        # Load canvas settings from settings.json (will be used by canvas_setup)
        sim_settings = self.settings.get("simulation", {})
        gui_settings = self.settings.get("gui_settings", {})

        # Scale and offset will be calculated dynamically by center_panel based on actual canvas size
        # Initialize with placeholder values - will be overwritten by responsive scaling
        self.offset_x = 50
        self.offset_y = 50
        self.scale_x = 5.0
        self.scale_y = 5.0
        self.grid_spacing = sim_settings.get("grid_spacing", 20)

        # Canvas dimensions will be set by center panel based on actual window size
        # Initialize with placeholder values - will be overwritten immediately
        self.canvas_width = 900
        self.canvas_height = 700
        self.actual_canvas_width = 900
        self.actual_canvas_height = 700

        # Position tracking
        self.position_update_scheduled = False

        # Initialize GUI components
        self.canvas_manager = CanvasManager(self)
        self.execution_controller = ExecutionController(self)

        # Create main layout and panels
        self.create_main_layout()
        self.create_panels()

        # Set up execution engine callback
        self.execution_engine.set_status_callback(self.on_execution_status)

        # Connect canvas manager to execution engine for GUI updates
        self.execution_engine.canvas_manager = self.canvas_manager

        # Set execution engine reference in hardware for sensor positioning
        self.hardware.set_execution_engine_reference(self.execution_engine)

        # Check if we're using real hardware - if so, we need to run homing first
        # Don't try to move motors before homing on real hardware
        from hardware.implementations.real.real_hardware import RealHardware
        self.is_real_hardware = isinstance(self.hardware, RealHardware)

        if not self.is_real_hardware:
            # Simulation mode - can move directly
            self.hardware.move_x(0.0)  # Rows motor home position
            self.hardware.move_y(0.0)  # Lines motor home position
            self.canvas_manager.update_position_display()

        # Start position update timer
        self.schedule_position_update()

        # Initial load
        self.load_csv_file_by_path("data/sample_programs.csv")

        # If using real hardware, schedule homing after GUI is fully loaded
        if self.is_real_hardware:
            self.root.after(500, self._run_startup_homing)

    def load_settings(self):
        """Load settings from config/settings.json"""
        try:
            with open('config/settings.json', 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {
                "gui_settings": {
                    "auto_load_csv": "sample_programs.csv",
                    "canvas_margin_left": 60,
                    "canvas_margin_right": 30,
                    "canvas_margin_top": 40,
                    "canvas_margin_bottom": 50,
                    "canvas_min_scale": 3.5
                },
                "simulation": {
                    "grid_spacing": 20,
                    "show_grid": True,
                    "max_display_x": 120,
                    "max_display_y": 80
                }
            }

    def load_csv_file_by_path(self, file_path):
        """Load CSV file by path"""
        if os.path.exists(file_path):
            programs, errors = self.csv_parser.load_programs_from_csv(file_path)

            if errors:
                error_msg = "\n".join(errors[:5])
                if len(errors) > 5:
                    error_msg += f"\n" + t("... and {count} more errors", count=len(errors) - 5)
                messagebox.showerror(t("CSV Validation Errors"),
                                   t("Found {count} validation errors:\n{errors}", count=len(errors), errors=error_msg))

            if programs:
                self.programs = programs
                self.current_file = file_path
                self.left_panel.update_program_list()
                if programs:
                    self.left_panel.select_program(0)
            else:
                messagebox.showerror(t("Error"), t("No valid programs found in {file}", file=file_path))

    def create_main_layout(self):
        """Create the main window layout - responsive design"""
        # Create main frames with responsive sizing
        self.left_frame = tk.Frame(self.root, bg='lightgray')
        self.center_frame = tk.Frame(self.root, bg='white')
        self.right_frame = tk.Frame(self.root, bg='lightblue')

        # Configure responsive column and row weights - single row spanning full height
        self.root.grid_rowconfigure(0, weight=1)  # Single row spans full height
        self.root.grid_columnconfigure(0, minsize=250, weight=1)  # Left: min 250px
        self.root.grid_columnconfigure(1, minsize=920, weight=4)  # Center: larger weight for canvas
        self.root.grid_columnconfigure(2, minsize=200, weight=1)  # Right: reduced to 200px min

        # Grid frames for responsive layout - all in single row
        self.left_frame.grid(row=0, column=0, sticky="nsew", padx=(5,3), pady=5)
        self.center_frame.grid(row=0, column=1, sticky="nsew", padx=3, pady=5)
        self.right_frame.grid(row=0, column=2, sticky="nsew", padx=(3,5), pady=5)

    def create_panels(self):
        """Create and initialize all GUI panels"""
        self.left_panel = LeftPanel(self, self.left_frame)
        # Create center panel - store reference immediately for canvas setup checks
        self.center_panel = CenterPanel(self, self.center_frame)

        # Create hardware status panel frame in center (below canvas)
        center_bottom_frame = tk.Frame(self.center_frame, bg='#2C3E50')
        center_bottom_frame.pack(fill=tk.X, expand=False, pady=(5, 0))

        # Right frame now contains settings and control panel
        # Create container frames in right panel
        right_settings_frame = tk.Frame(self.right_frame, bg='#E8F4F8')
        right_settings_frame.pack(fill=tk.X, expand=False)

        right_top_frame = tk.Frame(self.right_frame, bg='lightblue')
        right_top_frame.pack(fill=tk.BOTH, expand=True)

        self.hardware_settings_panel = HardwareSettingsPanel(self, right_settings_frame)
        self.right_panel = RightPanel(self, right_top_frame)
        self.hardware_status_panel = HardwareStatusPanel(self, center_bottom_frame)

        # NOW finalize canvas setup after all panels are created and laid out
        self.logger.debug("All panels created, calling finalize_canvas_setup()", category="gui")
        self.center_panel.finalize_canvas_setup()

    def schedule_position_update(self):
        """Schedule regular position updates"""
        # Skip updates during sensitive operations
        if self.state_manager.state not in [MachineState.HOMING, MachineState.SWITCHING_MODE]:
            self.canvas_manager.update_position_display()
        self.root.after(500, self.schedule_position_update)  # Update every 500ms

    def _on_machine_state_changed(self, old_state: MachineState, new_state: MachineState):
        """Handle machine state changes"""
        self.logger.debug(f"Machine state changed: {old_state.value} -> {new_state.value}", category="gui")

        # Update UI based on state
        if new_state == MachineState.HOMING:
            self._disable_controls_during_operation()
        elif new_state == MachineState.SWITCHING_MODE:
            self._disable_controls_during_operation()
        elif new_state == MachineState.IDLE:
            self._enable_controls()
        elif new_state == MachineState.ERROR:
            self._enable_controls()
            # Status panel will show error state

    def _disable_controls_during_operation(self):
        """Disable controls during homing or mode switching"""
        # Disable execution controls in right panel
        if hasattr(self, 'right_panel'):
            self.right_panel.set_controls_enabled(False)

    def _enable_controls(self):
        """Re-enable controls after operation completes"""
        # Re-enable execution controls in right panel
        if hasattr(self, 'right_panel'):
            self.right_panel.set_controls_enabled(True)

    def _run_startup_homing(self):
        """Run homing sequence on startup when using real hardware"""
        from tkinter import messagebox
        from gui.dialogs.homing_dialog import HomingProgressDialog

        self.logger.info("Real hardware detected - starting homing sequence", category="gui")

        # Ask user to confirm homing
        if not messagebox.askyesno(
            t("Homing Required"),
            t("Real hardware mode is active.\n\n"
              "The machine needs to be homed before operation.\n"
              "This will:\n"
              "1. Apply GRBL configuration\n"
              "2. Check door is open\n"
              "3. Lift line motor pistons\n"
              "4. Run GRBL homing ($H)\n"
              "5. Reset work coordinates\n"
              "6. Lower line motor pistons\n\n"
              "Make sure the machine is clear and ready.\n\n"
              "Run homing now?")
        ):
            self.logger.warning("User skipped startup homing - machine not homed", category="gui")
            messagebox.showwarning(
                t("Warning"),
                t("Machine was NOT homed.\n\n"
                  "You can run homing later from the Hardware Test GUI\n"
                  "or by switching hardware modes in the settings panel.")
            )
            return

        # Set machine state to homing
        self.state_manager.set_state(MachineState.HOMING)

        # Show homing dialog
        homing_dialog = HomingProgressDialog(self.root, self.hardware)
        homing_success, homing_error = homing_dialog.show()

        if homing_success:
            self.state_manager.set_state(MachineState.IDLE)
            self.logger.info("Startup homing completed successfully", category="gui")
            # Update position display after homing
            self.canvas_manager.update_position_display()
        else:
            self.state_manager.set_state(MachineState.ERROR, homing_error)
            self.logger.error(f"Startup homing failed: {homing_error}", category="gui")

    def on_execution_status(self, status, info=None):
        """Handle execution status updates"""
        self.execution_controller.on_execution_status(status, info)