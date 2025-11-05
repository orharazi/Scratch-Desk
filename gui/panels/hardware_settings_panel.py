import tkinter as tk
from tkinter import ttk
import json
import serial.tools.list_ports


class HardwareSettingsPanel:
    """Panel for hardware mode and port configuration"""

    def __init__(self, main_app, parent_frame):
        self.main_app = main_app
        self.parent_frame = parent_frame
        self.settings_file = "config/settings.json"

        # Create main frame
        self.frame = tk.LabelFrame(
            parent_frame,
            text="⚙️ Hardware Settings",
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
            text="Hardware Mode:",
            font=('Arial', 9, 'bold'),
            bg='#E8F4F8',
            fg='black'
        ).pack(side=tk.LEFT, padx=(0, 10))

        # Radio buttons
        self.mode_var = tk.StringVar(value="simulation" if not self.use_real_hardware else "real")

        self.sim_radio = tk.Radiobutton(
            mode_frame,
            text="🖥️ Simulation",
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
            text="🔧 Real Hardware",
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
            text="Arduino Port:",
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
            text="● Simulation Mode Active",
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
            text="✓ Apply Settings",
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
            text="💾 Save to Config",
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
        print("🔍 Scanning for serial ports...")

        # Get list of available ports
        ports = serial.tools.list_ports.comports()
        port_list = []

        for port in ports:
            port_desc = f"{port.device} - {port.description}"
            port_list.append(port.device)
            print(f"   Found: {port_desc}")

        if not port_list:
            port_list = ["No ports detected"]
            print("   ⚠️ No serial ports found")

        # Update dropdown
        self.port_dropdown['values'] = port_list

        # Select current port if it exists in the list
        if self.current_port in port_list:
            self.port_var.set(self.current_port)
        elif port_list and port_list[0] != "No ports detected":
            self.port_var.set(port_list[0])
        else:
            self.port_var.set("No ports detected")

        # Update UI state
        self.update_ui_state()

        print(f"✅ Port scan complete. {len(port_list)} port(s) available.")

    def on_mode_changed(self):
        """Handle mode selection change"""
        mode = self.mode_var.get()
        print(f"🔄 Mode changed to: {mode}")

        # Enable apply/save buttons when changes are made
        self.apply_btn.config(state=tk.NORMAL)
        self.save_btn.config(state=tk.NORMAL)

        self.update_ui_state()

    def on_port_selected(self, event=None):
        """Handle port selection change"""
        selected_port = self.port_var.get()
        print(f"🔌 Port selected: {selected_port}")

        # Enable apply/save buttons when changes are made
        self.apply_btn.config(state=tk.NORMAL)
        self.save_btn.config(state=tk.NORMAL)

        self.update_ui_state()

    def update_ui_state(self):
        """Update UI state based on selections"""
        selected_port = self.port_var.get()
        mode = self.mode_var.get()

        # Enable real hardware mode only if a valid port is selected
        if selected_port and selected_port != "No ports detected":
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
                text="● Simulation Mode Active",
                fg='#27AE60'
            )
        elif mode == "real" and port_valid:
            self.status_label.config(
                text=f"● Real Hardware Mode - Port: {selected_port}",
                fg='#E67E22'
            )
        else:
            self.status_label.config(
                text="⚠️ Select a valid port to enable Real Hardware Mode",
                fg='#E74C3C'
            )

    def apply_settings(self):
        """Apply settings to current session (requires restart)"""
        mode = self.mode_var.get()
        selected_port = self.port_var.get()

        print(f"\n{'='*60}")
        print("⚙️ APPLYING HARDWARE SETTINGS")
        print(f"{'='*60}")
        print(f"Mode: {mode.upper()}")
        print(f"Port: {selected_port}")

        # Update settings in memory
        use_real = (mode == "real")

        if "hardware_config" not in self.settings:
            self.settings["hardware_config"] = {}

        self.settings["hardware_config"]["use_real_hardware"] = use_real

        if "arduino_grbl" not in self.settings["hardware_config"]:
            self.settings["hardware_config"]["arduino_grbl"] = {}

        self.settings["hardware_config"]["arduino_grbl"]["serial_port"] = selected_port

        print(f"✅ Settings updated in memory")
        print(f"⚠️ RESTART APPLICATION to apply hardware changes")
        print(f"{'='*60}\n")

        # Show info message
        from tkinter import messagebox
        messagebox.showinfo(
            "Settings Applied",
            f"Hardware settings updated:\n\n"
            f"Mode: {mode.upper()}\n"
            f"Port: {selected_port}\n\n"
            f"⚠️ Please RESTART the application\n"
            f"to switch hardware modes."
        )

        # Disable buttons after applying
        self.apply_btn.config(state=tk.DISABLED)

    def save_settings(self):
        """Save settings to settings.json file"""
        mode = self.mode_var.get()
        selected_port = self.port_var.get()

        print(f"\n{'='*60}")
        print("💾 SAVING HARDWARE SETTINGS TO CONFIG")
        print(f"{'='*60}")
        print(f"Mode: {mode.upper()}")
        print(f"Port: {selected_port}")

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
            print(f"✅ Settings saved to {self.settings_file}")
            print(f"⚠️ RESTART APPLICATION to apply hardware changes")
            print(f"{'='*60}\n")

            # Show success message
            from tkinter import messagebox
            messagebox.showinfo(
                "Settings Saved",
                f"Hardware settings saved to config:\n\n"
                f"Mode: {mode.upper()}\n"
                f"Port: {selected_port}\n\n"
                f"⚠️ Please RESTART the application\n"
                f"to switch hardware modes."
            )

            # Disable buttons after saving
            self.apply_btn.config(state=tk.DISABLED)
            self.save_btn.config(state=tk.DISABLED)

        except Exception as e:
            print(f"❌ Error saving settings: {e}")
            from tkinter import messagebox
            messagebox.showerror(
                "Save Error",
                f"Failed to save settings:\n{e}"
            )

    def get_current_config(self):
        """Get current hardware configuration"""
        return {
            'mode': self.mode_var.get(),
            'port': self.port_var.get(),
            'use_real_hardware': self.mode_var.get() == "real"
        }
