#!/usr/bin/env python3

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import time
import os
import json

# Import translation function
from core.translations import t, t_title

# Import our modules
from core.csv_parser import CSVParser
from core.step_generator import generate_complete_program_steps, get_step_count_summary
from core.execution_engine import ExecutionEngine
from core.machine_state import MachineState, get_state_manager
from hardware.interfaces.hardware_factory import get_hardware_interface

# Import GUI components
from gui.panels.program_panel import ProgramPanel
from gui.panels.center_panel import CenterPanel
from gui.panels.controls_panel import ControlsPanel
from gui.panels.hardware_status_panel import HardwareStatusPanel
from gui.panels.hardware_settings_panel import HardwareSettingsPanel
from gui.canvas.canvas_manager import CanvasManager
from gui.execution.execution_controller import ExecutionController
from core.logger import get_logger


class ScratchDeskGUI:
    """Main GUI application class"""

    def __init__(self, root):
        self.root = root
        self.root.tk.call('tk', 'appname', 'scratch-desk')
        self.root.title(t_title("Scratch Desk Control System"))
        self.root.geometry("1500x1000")
        self.root.minsize(1100, 750)
        self.root.resizable(True, True)
        self.logger = get_logger()

        # Maximize window (uses wlrctl on labwc where state('zoomed') is a no-op)
        from gui.wayland_focus import maximize_window
        maximize_window(self.root)

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

        # Initialize analytics collector
        from core.analytics import get_analytics_collector
        self.analytics_collector = get_analytics_collector()

        # Start email report scheduler (daemon thread, only if configured)
        from core.email_reporter import get_email_reporter
        self._email_reporter = get_email_reporter()
        self._email_reporter.start_scheduler()

        # Connect canvas manager to execution engine for GUI updates
        self.execution_engine.canvas_manager = self.canvas_manager

        # Set execution engine reference in hardware for sensor positioning
        self.hardware.set_execution_engine_reference(self.execution_engine)

        # Check if we're using real hardware - if so, we need to run homing first
        # Don't try to move motors before homing on real hardware
        from hardware.implementations.real.real_hardware import RealHardware
        self.is_real_hardware = isinstance(self.hardware, RealHardware)

        # Track whether homing was completed successfully (real hardware only)
        # Programs CANNOT run on real hardware until this is True
        self.homing_completed = not self.is_real_hardware  # Mock mode is always "homed"

        # Open air pressure valve on startup (air flows to pistons)
        self.hardware.air_pressure_valve_down()

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

        # Force focus on startup (Wayland/labwc doesn't always focus new windows)
        self._force_window_focus(self.root)

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
                messagebox.showerror(t_title("CSV Validation Errors"),
                                   t("Found {count} validation errors:\n{errors}", count=len(errors), errors=error_msg))

            if programs:
                self.programs = programs
                self.current_file = file_path
                self.program_panel.update_program_list()
                if programs:
                    self.program_panel.select_program(0)
            else:
                messagebox.showerror(t_title("Error"), t("No valid programs found in {file}", file=file_path))

    def create_main_layout(self):
        """Create the main window layout - responsive RTL design"""
        # Create main frames with responsive sizing (RTL layout)
        self.controls_frame = tk.Frame(self.root, bg='lightblue')
        self.center_frame = tk.Frame(self.root, bg='white')
        self.program_frame = tk.Frame(self.root, bg='lightgray', width=280)
        self.program_frame.pack_propagate(False)  # Prevent children from expanding the frame

        # Configure responsive column and row weights - RTL layout
        self.root.grid_rowconfigure(0, weight=1)  # Single row spans full height
        self.root.grid_columnconfigure(0, minsize=180, weight=1)  # Controls panel (left in RTL)
        self.root.grid_columnconfigure(1, minsize=500, weight=5)  # Center: larger weight for canvas
        self.root.grid_columnconfigure(2, minsize=220, weight=0)  # Program panel (right in RTL) - fixed width

        # Grid frames for RTL layout - controls on left, program params on right
        self.controls_frame.grid(row=0, column=0, sticky="nsew", padx=(5,3), pady=5)
        self.center_frame.grid(row=0, column=1, sticky="nsew", padx=3, pady=5)
        self.program_frame.grid(row=0, column=2, sticky="nsew", padx=(3,5), pady=5)

    def create_panels(self):
        """Create and initialize all GUI panels"""
        self.program_panel = ProgramPanel(self, self.program_frame)
        # Create center panel - store reference immediately for canvas setup checks
        self.center_panel = CenterPanel(self, self.center_frame)

        # Create hardware status panel frame in center (below canvas)
        center_bottom_frame = tk.Frame(self.center_frame, bg='#2C3E50')
        center_bottom_frame.pack(fill=tk.X, expand=False, pady=(5, 0))

        # Controls frame contains settings and control panel
        controls_settings_frame = tk.Frame(self.controls_frame, bg='#E8F4F8')
        controls_settings_frame.pack(fill=tk.X, expand=False)

        controls_top_frame = tk.Frame(self.controls_frame, bg='lightblue')
        controls_top_frame.pack(fill=tk.BOTH, expand=True)

        self.hardware_settings_panel = HardwareSettingsPanel(self, controls_settings_frame)

        # Homing button - allows user to trigger homing at any time
        homing_btn_frame = tk.Frame(self.controls_frame, bg='#2980B9', pady=2)
        homing_btn_frame.pack(fill=tk.X, padx=5, pady=(3, 1))
        self.homing_btn = tk.Button(
            homing_btn_frame,
            text=t("Run Homing"),
            command=self._run_homing,
            font=('Arial', 11, 'bold'),
            bg='#2980B9',
            fg='white',
            activebackground='#2471A3',
            activeforeground='white',
            relief=tk.RAISED,
            cursor='hand2',
            pady=6
        )
        self.homing_btn.pack(fill=tk.X, padx=2, pady=2)

        # Admin Tool button - prominent, between settings and controls
        admin_btn_frame = tk.Frame(self.controls_frame, bg='#8E44AD', pady=2)
        admin_btn_frame.pack(fill=tk.X, padx=5, pady=(1, 3))
        self.admin_tool_btn = tk.Button(
            admin_btn_frame,
            text=t("Admin Tool"),
            command=self._open_admin_tool,
            font=('Arial', 11, 'bold'),
            bg='#8E44AD',
            fg='white',
            activebackground='#7D3C98',
            activeforeground='white',
            relief=tk.RAISED,
            cursor='hand2',
            pady=6
        )
        self.admin_tool_btn.pack(fill=tk.X, padx=2, pady=2)

        self.controls_panel = ControlsPanel(self, controls_top_frame)
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
        if hasattr(self, 'controls_panel'):
            self.controls_panel.set_controls_enabled(False)

    def _enable_controls(self):
        """Re-enable controls after operation completes"""
        if hasattr(self, 'controls_panel'):
            self.controls_panel.set_controls_enabled(True)

    def _run_startup_homing(self):
        """Run homing sequence on startup when using real hardware"""
        self.logger.info("Real hardware detected - starting homing sequence", category="gui")

        # Ask user to confirm homing
        if not messagebox.askyesno(
            t_title("Homing Required"),
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
                t_title("Warning"),
                t("Machine was NOT homed.\n\n"
                  "You must run homing before running any program.\n"
                  "Use the homing button to run homing.")
            )
            return

        self._execute_homing_with_retry()

    def _execute_homing_with_retry(self):
        """Execute homing sequence with retry option on failure"""
        from gui.dialogs.homing_dialog import HomingProgressDialog

        while True:
            # Set machine state to homing
            self.state_manager.set_state(MachineState.HOMING)

            # Show homing dialog
            homing_dialog = HomingProgressDialog(self.root, self.hardware)
            homing_success, homing_error = homing_dialog.show()

            if homing_success:
                self.homing_completed = True
                self.state_manager.set_state(MachineState.IDLE)
                self.logger.info("Homing completed successfully", category="gui")
                self.canvas_manager.update_position_display()
                return

            # Homing failed - offer retry
            self.state_manager.set_state(MachineState.ERROR, homing_error)
            self.logger.error(f"Homing failed: {homing_error}", category="gui")

            # Show failure dialog with "Try Again" option
            retry = messagebox.askyesno(
                t_title("Homing Failed"),
                t("Homing failed!\n\nError: {error}\n\n"
                  "Try again?", error=homing_error)
            )
            if not retry:
                return

    def _run_homing(self):
        """Run homing sequence triggered by user button"""
        # Don't allow homing if execution is running
        if self.execution_engine.is_running:
            messagebox.showwarning(
                t_title("Cannot Home"),
                t("Cannot run homing while a program is executing.\nStop execution first.")
            )
            return

        # Confirm with user
        if not messagebox.askyesno(
            t_title("Run Homing"),
            t("This will run the homing sequence.\n\n"
              "Make sure the machine is clear and ready.\n\n"
              "Run homing now?")
        ):
            return

        self._execute_homing_with_retry()

    def _open_admin_tool(self):
        """Open admin tool after password verification"""
        # Load password fresh from file (not cached) so changes take effect immediately
        fresh_settings = self.load_settings()
        admin_password = fresh_settings.get('admin', {}).get('password', '')

        # Prompt for password
        dialog = tk.Toplevel(self.root)
        dialog.title(t_title("Admin Login"))
        dialog.geometry("300x150")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.lift()
        dialog.grab_set()

        # Center the dialog on the main window
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 150
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 75
        dialog.geometry(f"300x150+{x}+{y}")

        tk.Label(dialog, text=t("Enter admin password:"), font=('Arial', 11), fg='black', bg='white').pack(pady=(20, 5))
        password_entry = tk.Entry(dialog, show="*", font=('Arial', 12), width=20, bg='white', fg='black')
        password_entry.pack(pady=5)
        password_entry.focus_set()

        error_label = tk.Label(dialog, text="", fg='red', bg='white', font=('Arial', 9))
        error_label.pack()

        def try_login(event=None):
            if password_entry.get() == admin_password:
                dialog.grab_release()
                dialog.destroy()
                # Launch admin tool immediately — no force_focus_return here
                # since admin window opens right away and takes focus itself
                self.root.after(100, self._launch_admin_tool)
            else:
                error_label.config(text=t("Wrong password"))
                password_entry.delete(0, tk.END)

        def _cancel_login():
            dialog.grab_release()
            dialog.destroy()
            from gui.wayland_focus import force_focus_return
            force_focus_return(self.root)

        password_entry.bind("<Return>", try_login)

        dialog.configure(bg='white')
        btn_frame = tk.Frame(dialog, bg='white')
        btn_frame.pack(pady=5)
        tk.Button(btn_frame, text=t("Cancel"), command=_cancel_login, width=10, fg='black').pack(side=tk.RIGHT, padx=5)
        tk.Button(btn_frame, text=t("Login"), command=try_login, width=10,
                  bg='#8E44AD', fg='white').pack(side=tk.RIGHT, padx=5)

    def _force_window_focus(self, window):
        """Force window focus — delegates to wayland_focus utility"""
        from gui.wayland_focus import force_focus
        force_focus(window, app_id='scratch-desk')

    def _launch_admin_tool(self):
        """Launch admin tool window with shared hardware"""
        from admin.admin_app import AdminToolGUI
        from gui.wayland_focus import force_focus, force_focus_return, _HAS_WLRCTL, _wlrctl_focus_title

        admin_window = tk.Toplevel(self.root)
        # NOTE: no transient() — on labwc, transient child Toplevels can't be
        # independently focused by the compositor via wlrctl.
        AdminToolGUI(admin_window, hardware=self.hardware, launched_from_app=True,
                     on_settings_changed=self._on_settings_changed,
                     can_change_settings=self._can_change_settings)

        # Aggressive focus: -topmost temporarily + wlrctl title matching.
        # The patched Toplevel.__init__ already schedules app_id focus at <Map>
        # and title focus at +250ms. We add extra attempts here because the
        # admin window competes with VS Code for compositor focus.
        admin_window.attributes('-topmost', True)
        admin_window.lift()
        admin_window.focus_force()

        admin_title = admin_window.title()

        if _HAS_WLRCTL and admin_title:
            # Multiple wlrctl title-focus attempts at staggered intervals
            for delay in (150, 400, 700):
                admin_window.after(delay, lambda t=admin_title: _wlrctl_focus_title(t))

        # Remove -topmost once focus is established
        def _settle():
            if admin_window.winfo_exists():
                admin_window.attributes('-topmost', False)
        admin_window.after(800, _settle)

        # Wrap close handler to return focus to main window
        def _on_admin_close():
            try:
                admin_window.destroy()
            except Exception:
                pass
            force_focus_return(self.root)

        admin_window.protocol("WM_DELETE_WINDOW", _on_admin_close)

    def _can_change_settings(self):
        """Check if settings can be changed right now.
        Returns (allowed, reason) tuple."""
        engine = self.execution_engine
        if engine.is_running:
            return False, t("Cannot change settings while program is running")
        if hasattr(self, 'controls_panel') and self.controls_panel._stopped_mid_execution:
            return False, t("Cannot change settings while program is stopped mid-execution. Reset first")
        return True, ""

    def _on_settings_changed(self):
        """Called by admin tool when settings are saved — reload and refresh UI"""
        self.settings = self.load_settings()

        # Update module-level paper offsets in step_generator
        import core.step_generator as sg
        sg.PAPER_OFFSET_X, sg.PAPER_OFFSET_Y = sg._load_paper_offsets()

        # Full canvas redraw — redraws grid, start point marker, sensors, etc.
        self.canvas_manager.setup_canvas()
        # Redraw program-specific paper area and work lines on top
        if self.current_program:
            self.canvas_manager.update_canvas_paper_area()
            # Regenerate steps with new offsets
            if hasattr(self, 'controls_panel'):
                self.controls_panel.generate_steps()

    def perform_emergency_stop(self):
        """Emergency stop - immediately halt all motors and retract pistons to safe state"""
        self.logger.error("EMERGENCY STOP activated", category="gui")

        # 1. Immediately stop motors (GRBL feed hold "!")
        self.hardware.emergency_stop()

        # 2. Stop execution engine if running
        if self.execution_engine.is_running:
            self.execution_engine.stop_execution()

        # 3. Retract all pistons to safe defaults (air pressure still on so pistons can move)
        self.hardware.line_marker_piston_up()
        self.hardware.line_cutter_piston_up()
        self.hardware.line_motor_piston_down()  # DOWN is default for line motor
        self.hardware.row_marker_piston_up()
        self.hardware.row_cutter_piston_up()

        # 4. Close air pressure valve AFTER pistons retract (they need air to operate)
        self.hardware.air_pressure_valve_up()

        # 5. Update GUI
        self.operation_label.config(text=t("⚠ EMERGENCY STOP - System stopped"), fg='red')
        if hasattr(self, 'controls_panel'):
            self.controls_panel.run_btn.config(state=tk.DISABLED)
            self.controls_panel.pause_btn.config(state=tk.DISABLED)
            self.controls_panel.stop_btn.config(state=tk.DISABLED)
            self.controls_panel.reset_btn.config(state=tk.NORMAL)

    def on_execution_status(self, status, info=None):
        """Handle execution status updates - thread-safe via root.after"""
        # Schedule on main thread since this is called from execution thread
        self.root.after(0, lambda s=status, i=info: self.execution_controller.on_execution_status(s, i))