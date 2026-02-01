import tkinter as tk
from tkinter import ttk, messagebox
import json
import serial.tools.list_ports
from core.logger import get_logger
from core.translations import t
from core.machine_state import MachineState, get_state_manager


class HardwareSettingsPanel:
    """Panel for hardware mode and port configuration"""

    def __init__(self, main_app, parent_frame):
        self.main_app = main_app
        self.parent_frame = parent_frame
        self.settings_file = "config/settings.json"
        self.logger = get_logger()

        # Create main frame
        self.frame = tk.LabelFrame(
            parent_frame,
            text=t("⚙️ Hardware Settings"),
            font=('Arial', 10, 'bold'),
            bg='#E8F4F8',
            fg='black',
            padx=10,
            pady=5
        )
        self.frame.pack(fill=tk.X, padx=5, pady=5)

        # Load current settings
        self.load_settings()

        # Create UI elements (order matters - status_label must exist before refresh_ports)
        self.create_mode_selector()
        self.create_status_display()
        self.create_port_selector()
        self.create_action_buttons()

        # Update initial state
        self.update_ui_state()

    def load_settings(self):
        """Load settings from settings.json"""
        try:
            with open(self.settings_file, 'r') as f:
                self.settings = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.settings = {}

        self.hardware_config = self.settings.get("hardware_config", {})
        self.use_real_hardware = self.hardware_config.get("use_real_hardware", False)
        self.arduino_config = self.hardware_config.get("arduino_grbl", {})
        self.current_port = self.arduino_config.get("serial_port", "/dev/ttyACM0")

    def create_mode_selector(self):
        """Create hardware mode selection radio buttons"""
        mode_frame = tk.Frame(self.frame, bg='#E8F4F8')
        mode_frame.pack(fill=tk.X, pady=(0, 5))

        # Mode label
        tk.Label(
            mode_frame,
            text=t("Hardware Mode:"),
            font=('Arial', 9, 'bold'),
            bg='#E8F4F8',
            fg='black'
        ).pack(side=tk.LEFT, padx=(0, 10))

        # Radio buttons
        self.mode_var = tk.StringVar(value="simulation" if not self.use_real_hardware else "real")

        self.sim_radio = tk.Radiobutton(
            mode_frame,
            text=t("🖥️ Simulation"),
            variable=self.mode_var,
            value="simulation",
            command=self.on_mode_changed,
            font=('Arial', 9),
            bg='#E8F4F8',
            fg='black',
            activebackground='#D0E8F0'
        )
        self.sim_radio.pack(side=tk.LEFT, padx=5)

        self.real_radio = tk.Radiobutton(
            mode_frame,
            text=t("🔧 Real Hardware"),
            variable=self.mode_var,
            value="real",
            command=self.on_mode_changed,
            font=('Arial', 9),
            bg='#E8F4F8',
            fg='black',
            activebackground='#D0E8F0',
            state=tk.DISABLED  # Initially disabled until port is selected
        )
        self.real_radio.pack(side=tk.LEFT, padx=5)

    def create_port_selector(self):
        """Create Arduino port selection dropdown"""
        port_frame = tk.Frame(self.frame, bg='#E8F4F8')
        port_frame.pack(fill=tk.X, pady=(0, 5))

        # Port label
        tk.Label(
            port_frame,
            text=t("Arduino Port:"),
            font=('Arial', 9, 'bold'),
            bg='#E8F4F8',
            fg='black'
        ).pack(side=tk.LEFT, padx=(0, 10))

        # Port dropdown
        self.port_var = tk.StringVar(value=self.current_port)
        self.port_dropdown = ttk.Combobox(
            port_frame,
            textvariable=self.port_var,
            font=('Arial', 9),
            state='readonly',
            width=20
        )
        self.port_dropdown.pack(side=tk.LEFT, padx=5)
        self.port_dropdown.bind('<<ComboboxSelected>>', self.on_port_selected)

        # Refresh button
        self.refresh_btn = tk.Button(
            port_frame,
            text="🔄",
            command=self.refresh_ports,
            font=('Arial', 9),
            bg='#3498DB',
            fg='white',
            relief=tk.RAISED,
            width=3,
            cursor='hand2'
        )
        self.refresh_btn.pack(side=tk.LEFT, padx=5)

        # Initial port detection
        self.refresh_ports()

    def create_status_display(self):
        """Create status display area"""
        status_frame = tk.Frame(self.frame, bg='#E8F4F8')
        status_frame.pack(fill=tk.X, pady=(0, 5))

        self.status_label = tk.Label(
            status_frame,
            text=t("● Simulation Mode Active"),
            font=('Arial', 9),
            bg='#E8F4F8',
            fg='#27AE60'
        )
        self.status_label.pack(side=tk.LEFT)

    def create_action_buttons(self):
        """Create action buttons"""
        button_frame = tk.Frame(self.frame, bg='#E8F4F8')
        button_frame.pack(fill=tk.X, pady=(5, 0))

        # Apply button
        self.apply_btn = tk.Button(
            button_frame,
            text=t("✓ Apply Settings"),
            command=self.apply_settings,
            font=('Arial', 9, 'bold'),
            bg='#27AE60',
            fg='white',
            relief=tk.RAISED,
            cursor='hand2',
            padx=10,
            pady=3
        )
        self.apply_btn.pack(side=tk.LEFT, padx=5)

        # Save button
        self.save_btn = tk.Button(
            button_frame,
            text=t("💾 Save to Config"),
            command=self.save_settings,
            font=('Arial', 9),
            bg='#3498DB',
            fg='white',
            relief=tk.RAISED,
            cursor='hand2',
            padx=10,
            pady=3
        )
        self.save_btn.pack(side=tk.LEFT, padx=5)

        # Initially disable buttons (no changes yet)
        self.apply_btn.config(state=tk.DISABLED)
        self.save_btn.config(state=tk.DISABLED)

    def refresh_ports(self):
        """Detect and refresh available serial ports"""
        self.logger.debug(" Scanning for serial ports...", category="gui")

        # Get list of available ports
        ports = serial.tools.list_ports.comports()
        port_list = []

        for port in ports:
            port_desc = f"{port.device} - {port.description}"
            port_list.append(port.device)
            self.logger.debug(f" Found: {port_desc}", category="gui")

        if not port_list:
            port_list = [t("No ports detected")]
            self.logger.debug(" No serial ports found", category="gui")

        # Update dropdown
        self.port_dropdown['values'] = port_list

        # Select current port if it exists in the list
        if self.current_port in port_list:
            self.port_var.set(self.current_port)
        elif port_list and port_list[0] != t("No ports detected"):
            self.port_var.set(port_list[0])
        else:
            self.port_var.set(t("No ports detected"))

        # Update UI state
        self.update_ui_state()

        self.logger.info(f" Port scan complete. {len(port_list)} port(s) available.", category="gui")

    def on_mode_changed(self):
        """Handle mode selection change"""
        mode = self.mode_var.get()
        self.logger.debug(f" Mode changed to: {mode}", category="gui")

        # Enable apply/save buttons when changes are made
        self.apply_btn.config(state=tk.NORMAL)
        self.save_btn.config(state=tk.NORMAL)

        self.update_ui_state()

    def on_port_selected(self, event=None):
        """Handle port selection change"""
        selected_port = self.port_var.get()
        self.logger.debug(f"🔌 Port selected: {selected_port}", category="gui")

        # Enable apply/save buttons when changes are made
        self.apply_btn.config(state=tk.NORMAL)
        self.save_btn.config(state=tk.NORMAL)

        self.update_ui_state()

    def update_ui_state(self):
        """Update UI state based on selections"""
        selected_port = self.port_var.get()
        mode = self.mode_var.get()

        # Enable real hardware mode only if a valid port is selected
        if selected_port and selected_port != t("No ports detected"):
            self.real_radio.config(state=tk.NORMAL)
            port_valid = True
        else:
            self.real_radio.config(state=tk.DISABLED)
            # Force simulation mode if no valid port
            if mode == "real":
                self.mode_var.set("simulation")
            port_valid = False

        # Update status label
        if mode == "simulation":
            self.status_label.config(
                text=t("● Simulation Mode Active"),
                fg='#27AE60'
            )
        elif mode == "real" and port_valid:
            self.status_label.config(
                text=t("● Real Hardware Mode - Port: {port}", port=selected_port),
                fg='#E67E22'
            )
        else:
            self.status_label.config(
                text=t("⚠️ Select a valid port to enable Real Hardware Mode"),
                fg='#E74C3C'
            )

    def apply_settings(self):
        """Apply settings with hot-swap (no restart required)"""
        mode = self.mode_var.get()
        selected_port = self.port_var.get()
        use_real = (mode == "real")

        self.logger.debug(f"\n{'='*60}", category="gui")
        self.logger.info("APPLYING HARDWARE SETTINGS (HOT-SWAP)", category="gui")
        self.logger.debug(f"{'='*60}", category="gui")
        self.logger.debug(f"Mode: {mode.upper()}", category="gui")
        self.logger.debug(f"Port: {selected_port}", category="gui")

        # Check if mode is actually changing
        from hardware.implementations.real.real_hardware import RealHardware
        current_is_real = isinstance(self.main_app.hardware, RealHardware)

        if use_real == current_is_real:
            messagebox.showinfo(
                t("No Change"),
                t("Hardware mode unchanged. Already in {mode} mode.",
                  mode=t("Real Hardware") if use_real else t("Simulation"))
            )
            self.apply_btn.config(state=tk.DISABLED)
            return

        # Check if safe to switch
        can_switch, reason = self._can_switch_mode()
        if not can_switch:
            messagebox.showwarning(t("Cannot Switch"), reason)
            return

        # Confirm the switch
        if use_real:
            if not messagebox.askyesno(
                t("Switch to Real Hardware"),
                t("This will:\n"
                  "1. Switch to real hardware mode\n"
                  "2. Connect to Arduino/GPIO\n"
                  "3. Run homing sequence\n\n"
                  "Make sure the machine is clear and ready.\n\n"
                  "Continue?")
            ):
                return
        else:
            if not messagebox.askyesno(
                t("Switch to Simulation"),
                t("Switch to simulation mode?\n\n"
                  "This will disconnect from real hardware.")
            ):
                return

        # Update settings.json first
        self._update_settings_file(use_real, selected_port)

        # Perform the hot-swap
        self._perform_hardware_switch(use_real, selected_port)

    def _can_switch_mode(self):
        """Check if it's safe to switch hardware mode"""
        state_manager = get_state_manager()
        can_switch, reason = state_manager.can_switch_mode()

        if not can_switch:
            return False, t(reason)

        # Also check execution engine
        if hasattr(self.main_app, 'execution_engine'):
            if self.main_app.execution_engine.is_running:
                return False, t("Cannot switch while execution is in progress")

        return True, ""

    def _update_settings_file(self, use_real, selected_port):
        """Update settings.json with new hardware configuration"""
        if "hardware_config" not in self.settings:
            self.settings["hardware_config"] = {}

        self.settings["hardware_config"]["use_real_hardware"] = use_real

        if "arduino_grbl" not in self.settings["hardware_config"]:
            self.settings["hardware_config"]["arduino_grbl"] = {}

        self.settings["hardware_config"]["arduino_grbl"]["serial_port"] = selected_port

        # Write to file
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
            self.logger.info(f"Settings saved to {self.settings_file}", category="gui")
        except Exception as e:
            self.logger.error(f"Error saving settings: {e}", category="gui")

    def _perform_hardware_switch(self, use_real, port):
        """Perform the actual hardware switch"""
        from hardware.interfaces.hardware_factory import switch_hardware_mode
        from gui.dialogs.homing_dialog import HomingProgressDialog

        state_manager = get_state_manager()

        # Set machine state to switching
        state_manager.set_state(MachineState.SWITCHING_MODE)

        # Disable UI during switch
        self._set_ui_enabled(False)
        self.status_label.config(
            text=t("Switching hardware mode..."),
            fg='#9B59B6'  # Purple
        )
        self.main_app.root.update()

        try:
            # Switch hardware
            new_hardware, success, error = switch_hardware_mode(use_real)

            if not success:
                state_manager.set_state(MachineState.ERROR, error)
                messagebox.showerror(
                    t("Hardware Switch Failed"),
                    t("Failed to switch hardware:\n\n{error}", error=error)
                )
                self._set_ui_enabled(True)
                self.update_ui_state()
                return

            # Update all references
            self._update_hardware_references(new_hardware)

            # If switching to real hardware, run homing
            if use_real:
                state_manager.set_state(MachineState.HOMING)

                # Show homing dialog
                homing_dialog = HomingProgressDialog(self.main_app.root, new_hardware)
                homing_success, homing_error = homing_dialog.show()

                if not homing_success:
                    state_manager.set_state(MachineState.ERROR, homing_error)
                    # Hardware is connected but homing failed
                    # Keep real hardware mode but in error state
                    self._set_ui_enabled(True)
                    self.update_ui_state()
                    return

            # Success
            state_manager.set_state(MachineState.IDLE)

            self.logger.info(f"Hardware switched to {'Real' if use_real else 'Simulation'} mode", category="gui")

            messagebox.showinfo(
                t("Hardware Switched"),
                t("Successfully switched to {mode} mode.",
                  mode=t("Real Hardware") if use_real else t("Simulation"))
            )

        except Exception as e:
            state_manager.set_state(MachineState.ERROR, str(e))
            self.logger.error(f"Hardware switch error: {e}", category="gui")
            messagebox.showerror(t("Error"), str(e))
        finally:
            self._set_ui_enabled(True)
            self.apply_btn.config(state=tk.DISABLED)
            self.update_ui_state()

    def _update_hardware_references(self, new_hardware):
        """Update all hardware references throughout the application"""
        self.logger.debug("Updating hardware references...", category="gui")

        # Update main app
        self.main_app.hardware = new_hardware

        # Update execution engine
        if hasattr(self.main_app, 'execution_engine'):
            self.main_app.execution_engine.hardware = new_hardware

        # Update hardware status panel
        if hasattr(self.main_app, 'hardware_status_panel'):
            self.main_app.hardware_status_panel.hardware = new_hardware

        # Update right panel (test controls)
        if hasattr(self.main_app, 'right_panel'):
            self.main_app.right_panel.refresh_hardware_reference()

        # Set execution engine reference in hardware for sensor positioning
        if hasattr(new_hardware, 'set_execution_engine_reference'):
            new_hardware.set_execution_engine_reference(self.main_app.execution_engine)

        # Update canvas manager if it has a hardware reference
        if hasattr(self.main_app, 'canvas_manager'):
            if hasattr(self.main_app.canvas_manager, 'hardware'):
                self.main_app.canvas_manager.hardware = new_hardware

        self.logger.debug("Hardware references updated", category="gui")

    def _set_ui_enabled(self, enabled):
        """Enable or disable UI elements during switch"""
        state = tk.NORMAL if enabled else tk.DISABLED
        self.sim_radio.config(state=state)
        self.real_radio.config(state=state)
        self.port_dropdown.config(state='readonly' if enabled else tk.DISABLED)
        self.refresh_btn.config(state=state)
        self.save_btn.config(state=state)

    def save_settings(self):
        """Save settings to settings.json file (for next app launch)"""
        mode = self.mode_var.get()
        selected_port = self.port_var.get()

        self.logger.debug(f"\n{'='*60}", category="gui")
        self.logger.debug("SAVING HARDWARE SETTINGS TO CONFIG", category="gui")
        self.logger.debug(f"{'='*60}", category="gui")
        self.logger.debug(f"Mode: {mode.upper()}", category="gui")
        self.logger.debug(f"Port: {selected_port}", category="gui")

        # Update settings
        use_real = (mode == "real")

        if "hardware_config" not in self.settings:
            self.settings["hardware_config"] = {}

        self.settings["hardware_config"]["use_real_hardware"] = use_real

        if "arduino_grbl" not in self.settings["hardware_config"]:
            self.settings["hardware_config"]["arduino_grbl"] = {}

        self.settings["hardware_config"]["arduino_grbl"]["serial_port"] = selected_port

        # Write to file
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
            self.logger.info(f"Settings saved to {self.settings_file}", category="gui")
            self.logger.debug(f"{'='*60}\n", category="gui")

            # Show success message
            messagebox.showinfo(
                t("Settings Saved"),
                t("Hardware settings saved to config:\n\n"
                  "Mode: {mode}\n"
                  "Port: {port}\n\n"
                  "Use 'Apply Settings' to switch now,\n"
                  "or settings will be used on next app launch.",
                  mode=mode.upper(),
                  port=selected_port)
            )

            # Keep apply enabled but disable save
            self.save_btn.config(state=tk.DISABLED)

        except Exception as e:
            self.logger.error(f"Error saving settings: {e}", category="gui")
            messagebox.showerror(
                t("Save Error"),
                t("Failed to save settings:\n{error}", error=e)
            )

    def get_current_config(self):
        """Get current hardware configuration"""
        return {
            'mode': self.mode_var.get(),
            'port': self.port_var.get(),
            'use_real_hardware': self.mode_var.get() == "real"
        }