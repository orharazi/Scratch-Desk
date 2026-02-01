#!/usr/bin/env python3
"""
Safety Rules Tab for Admin Tool
===============================

Provides CRUD interface for managing safety rules:
- View all safety rules
- Enable/disable individual rules
- Create new rules
- Edit existing rules
- Delete custom rules (system rules can only be disabled)
- View violations log
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
import os
from datetime import datetime


# Known values for different condition types
PISTON_VALUES = ["up", "down"]
SENSOR_BOOLEAN_VALUES = ["true", "false"]
SENSOR_POSITION_VALUES = ["up", "down"]  # For position sensors like row_motor_limit_switch

# Operation descriptions
OPERATION_DESCRIPTIONS = {
    "move_x": "Move X-axis (rows motor) - horizontal movement",
    "move_y": "Move Y-axis (lines motor) - vertical movement",
    "tool_action": "Tool operations (pistons up/down)",
    "wait_sensor": "Wait for sensor trigger"
}

# Available tools for tool_action operations
AVAILABLE_TOOLS = [
    "line_marker",
    "line_cutter",
    "line_motor",
    "row_marker",
    "row_cutter"
]


class SafetyTab:
    """Safety Rules Management Tab"""

    RULES_FILE = "config/safety_rules.json"

    def __init__(self, parent_frame, admin_app):
        self.frame = parent_frame
        self.app = admin_app
        self.rules_data = None
        self.selected_rule_id = None

        # Load rules
        self.load_rules()

        # Create UI
        self.create_ui()

        # Start update loop
        self.update_status()

    def load_rules(self):
        """Load safety rules from JSON file"""
        try:
            if os.path.exists(self.RULES_FILE):
                with open(self.RULES_FILE, 'r', encoding='utf-8') as f:
                    self.rules_data = json.load(f)
            else:
                # Create default structure
                self.rules_data = {
                    "version": "1.0.0",
                    "global_enabled": True,
                    "rules": [],
                    "available_tools": AVAILABLE_TOOLS
                }
        except Exception as e:
            self.rules_data = {"version": "1.0.0", "global_enabled": True, "rules": []}
            print(f"Error loading safety rules: {e}")

    def save_rules(self):
        """Save safety rules to JSON file"""
        try:
            self.rules_data["last_modified"] = datetime.now().isoformat()
            with open(self.RULES_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.rules_data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save rules: {e}")
            return False

    def create_ui(self):
        """Create the Safety Rules tab UI"""
        # Configure grid
        self.frame.columnconfigure(0, weight=1)
        self.frame.columnconfigure(1, weight=1)
        self.frame.rowconfigure(1, weight=1)

        # Top bar with global controls
        self.create_top_controls()

        # Left side - Rules list
        self.create_rules_list()

        # Right side - Rule details and violations
        self.create_details_panel()

    def create_top_controls(self):
        """Create top control bar"""
        top_frame = ttk.Frame(self.frame)
        top_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=5, pady=5)

        # Global safety toggle
        self.global_enabled_var = tk.BooleanVar(value=self.rules_data.get("global_enabled", True))

        ttk.Label(top_frame, text="Global Safety:", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(0, 5))

        self.global_toggle = ttk.Checkbutton(
            top_frame,
            text="Enabled",
            variable=self.global_enabled_var,
            command=self.toggle_global_safety
        )
        self.global_toggle.pack(side=tk.LEFT, padx=5)

        # Status indicator
        self.global_status_label = ttk.Label(top_frame, text="", font=("Arial", 10))
        self.global_status_label.pack(side=tk.LEFT, padx=10)

        # Spacer
        ttk.Frame(top_frame).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Action buttons
        ttk.Button(top_frame, text="+ Add Rule", command=self.add_rule).pack(side=tk.RIGHT, padx=2)
        ttk.Button(top_frame, text="Import", command=self.import_rules).pack(side=tk.RIGHT, padx=2)
        ttk.Button(top_frame, text="Export", command=self.export_rules).pack(side=tk.RIGHT, padx=2)
        ttk.Button(top_frame, text="Refresh", command=self.refresh_rules).pack(side=tk.RIGHT, padx=2)

    def create_rules_list(self):
        """Create rules list panel"""
        left_frame = ttk.LabelFrame(self.frame, text="Safety Rules", padding="5")
        left_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        left_frame.rowconfigure(0, weight=1)
        left_frame.columnconfigure(0, weight=1)

        # Create treeview for rules
        columns = ("enabled", "name", "severity", "type")
        self.rules_tree = ttk.Treeview(left_frame, columns=columns, show="headings", height=15)

        self.rules_tree.heading("enabled", text="On")
        self.rules_tree.heading("name", text="Rule Name")
        self.rules_tree.heading("severity", text="Severity")
        self.rules_tree.heading("type", text="Type")

        self.rules_tree.column("enabled", width=40, anchor="center")
        self.rules_tree.column("name", width=250)
        self.rules_tree.column("severity", width=80, anchor="center")
        self.rules_tree.column("type", width=80, anchor="center")

        # Scrollbar
        scrollbar = ttk.Scrollbar(left_frame, orient="vertical", command=self.rules_tree.yview)
        self.rules_tree.configure(yscrollcommand=scrollbar.set)

        self.rules_tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        # Bind selection
        self.rules_tree.bind("<<TreeviewSelect>>", self.on_rule_selected)
        self.rules_tree.bind("<Double-1>", self.on_rule_double_click)

        # Button frame
        btn_frame = ttk.Frame(left_frame)
        btn_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(5, 0))

        self.edit_btn = ttk.Button(btn_frame, text="Edit", command=self.edit_rule, state="disabled")
        self.edit_btn.pack(side=tk.LEFT, padx=2)

        self.delete_btn = ttk.Button(btn_frame, text="Delete", command=self.delete_rule, state="disabled")
        self.delete_btn.pack(side=tk.LEFT, padx=2)

        self.toggle_btn = ttk.Button(btn_frame, text="Enable/Disable", command=self.toggle_rule, state="disabled")
        self.toggle_btn.pack(side=tk.LEFT, padx=2)

        # Populate rules
        self.populate_rules_list()

    def create_details_panel(self):
        """Create rule details and violations panel"""
        right_frame = ttk.Frame(self.frame)
        right_frame.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)
        right_frame.rowconfigure(0, weight=1)
        right_frame.rowconfigure(1, weight=1)
        right_frame.columnconfigure(0, weight=1)

        # Rule details
        details_frame = ttk.LabelFrame(right_frame, text="Rule Details", padding="10")
        details_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 5))
        details_frame.columnconfigure(1, weight=1)

        # Detail labels
        row = 0
        ttk.Label(details_frame, text="ID:", font=("Arial", 9, "bold")).grid(row=row, column=0, sticky="w", pady=2)
        self.detail_id = ttk.Label(details_frame, text="-")
        self.detail_id.grid(row=row, column=1, sticky="w", pady=2)

        row += 1
        ttk.Label(details_frame, text="Name:", font=("Arial", 9, "bold")).grid(row=row, column=0, sticky="w", pady=2)
        self.detail_name = ttk.Label(details_frame, text="-")
        self.detail_name.grid(row=row, column=1, sticky="w", pady=2)

        row += 1
        ttk.Label(details_frame, text="Status:", font=("Arial", 9, "bold")).grid(row=row, column=0, sticky="w", pady=2)
        self.detail_status = ttk.Label(details_frame, text="-")
        self.detail_status.grid(row=row, column=1, sticky="w", pady=2)

        row += 1
        ttk.Label(details_frame, text="Priority:", font=("Arial", 9, "bold")).grid(row=row, column=0, sticky="w", pady=2)
        self.detail_priority = ttk.Label(details_frame, text="-")
        self.detail_priority.grid(row=row, column=1, sticky="w", pady=2)

        row += 1
        ttk.Label(details_frame, text="Severity:", font=("Arial", 9, "bold")).grid(row=row, column=0, sticky="w", pady=2)
        self.detail_severity = ttk.Label(details_frame, text="-")
        self.detail_severity.grid(row=row, column=1, sticky="w", pady=2)

        row += 1
        ttk.Label(details_frame, text="Description:", font=("Arial", 9, "bold")).grid(row=row, column=0, sticky="nw", pady=2)
        self.detail_description = ttk.Label(details_frame, text="-", wraplength=300)
        self.detail_description.grid(row=row, column=1, sticky="w", pady=2)

        row += 1
        ttk.Label(details_frame, text="Conditions:", font=("Arial", 9, "bold")).grid(row=row, column=0, sticky="nw", pady=2)
        # Use Text widget for multiline conditions display
        self.detail_conditions = tk.Text(details_frame, height=5, width=35, wrap=tk.WORD,
                                         font=("Consolas", 9), bg="#f5f5f5", relief="flat",
                                         state="disabled")
        self.detail_conditions.grid(row=row, column=1, sticky="w", pady=2)

        row += 1
        ttk.Label(details_frame, text="Blocks:", font=("Arial", 9, "bold")).grid(row=row, column=0, sticky="nw", pady=2)
        # Use Text widget for multiline blocks display
        self.detail_blocks = tk.Text(details_frame, height=3, width=35, wrap=tk.WORD,
                                     font=("Consolas", 9), bg="#f5f5f5", relief="flat",
                                     state="disabled")
        self.detail_blocks.grid(row=row, column=1, sticky="w", pady=2)

        # Violations log
        violations_frame = ttk.LabelFrame(right_frame, text="Recent Violations", padding="5")
        violations_frame.grid(row=1, column=0, sticky="nsew")
        violations_frame.rowconfigure(0, weight=1)
        violations_frame.columnconfigure(0, weight=1)

        self.violations_text = scrolledtext.ScrolledText(
            violations_frame, height=10, width=40,
            font=("Courier", 9), bg="#2D2D2D", fg="white"
        )
        self.violations_text.grid(row=0, column=0, sticky="nsew")

        # Configure tags
        self.violations_text.tag_config("critical", foreground="#E74C3C")
        self.violations_text.tag_config("warning", foreground="#F39C12")
        self.violations_text.tag_config("timestamp", foreground="#95A5A6")

        # Clear violations button
        ttk.Button(violations_frame, text="Clear Log", command=self.clear_violations).grid(row=1, column=0, sticky="e", pady=(5, 0))

    def populate_rules_list(self):
        """Populate the rules treeview"""
        # Clear existing items
        for item in self.rules_tree.get_children():
            self.rules_tree.delete(item)

        # Add rules
        for rule in self.rules_data.get("rules", []):
            enabled_text = "Yes" if rule.get("enabled", True) else "No"
            rule_type = "System" if rule.get("is_system_rule", False) else "Custom"
            severity = rule.get("severity", "info").capitalize()

            self.rules_tree.insert("", "end", iid=rule["id"], values=(
                enabled_text,
                rule.get("name", rule["id"]),
                severity,
                rule_type
            ))

    def on_rule_selected(self, event):
        """Handle rule selection"""
        selection = self.rules_tree.selection()
        if selection:
            self.selected_rule_id = selection[0]
            self.update_details_panel()

            # Enable/disable buttons based on selection
            rule = self.get_rule_by_id(self.selected_rule_id)
            if rule:
                self.edit_btn.config(state="normal")
                self.toggle_btn.config(state="normal")
                # Only allow delete for non-system rules
                if rule.get("is_system_rule", False):
                    self.delete_btn.config(state="disabled")
                else:
                    self.delete_btn.config(state="normal")
        else:
            self.selected_rule_id = None
            self.clear_details_panel()
            self.edit_btn.config(state="disabled")
            self.delete_btn.config(state="disabled")
            self.toggle_btn.config(state="disabled")

    def on_rule_double_click(self, event):
        """Handle double-click to edit rule"""
        if self.selected_rule_id:
            self.edit_rule()

    def get_rule_by_id(self, rule_id):
        """Get rule by ID"""
        for rule in self.rules_data.get("rules", []):
            if rule["id"] == rule_id:
                return rule
        return None

    def update_details_panel(self):
        """Update the details panel with selected rule info"""
        rule = self.get_rule_by_id(self.selected_rule_id)
        if not rule:
            self.clear_details_panel()
            return

        self.detail_id.config(text=rule.get("id", "-"))
        self.detail_name.config(text=rule.get("name", "-"))

        # Status with color
        if rule.get("enabled", True):
            self.detail_status.config(text="Enabled", foreground="green")
        else:
            self.detail_status.config(text="Disabled", foreground="red")

        self.detail_priority.config(text=str(rule.get("priority", "-")))
        self.detail_severity.config(text=rule.get("severity", "-").capitalize())
        self.detail_description.config(text=rule.get("description", "-"))

        # Format conditions - use Text widget
        conditions = rule.get("conditions", {})
        cond_text = self.format_conditions(conditions)
        self.detail_conditions.config(state="normal")
        self.detail_conditions.delete("1.0", tk.END)
        self.detail_conditions.insert("1.0", cond_text)
        self.detail_conditions.config(state="disabled")

        # Format blocked operations with tools - use Text widget
        blocks = rule.get("blocked_operations", [])
        blocks_text = self.format_blocked_operations(blocks)
        self.detail_blocks.config(state="normal")
        self.detail_blocks.delete("1.0", tk.END)
        self.detail_blocks.insert("1.0", blocks_text or "None")
        self.detail_blocks.config(state="disabled")

    def format_conditions(self, conditions, indent=0):
        """Format conditions for display in a readable way"""
        if not conditions:
            return "No conditions"

        operator = conditions.get("operator", "AND")
        items = conditions.get("items", [])

        if not items:
            return "No conditions"

        # Operator symbols
        op_symbol = "AND" if operator == "AND" else "OR"

        lines = []
        prefix = "  " * indent

        for i, item in enumerate(items):
            if "operator" in item and "items" in item:
                # Nested condition group
                nested = self.format_conditions(item, indent + 1)
                lines.append(f"{prefix}({nested})")
            else:
                # Simple condition - make it readable
                cond_type = item.get("type", "unknown")
                source = item.get("source", "?")
                op = item.get("operator", "?")
                value = item.get("value", "?")

                # Friendly operator names
                op_display = {
                    "equals": "=",
                    "not_equals": "!=",
                    "greater_than": ">",
                    "less_than": "<"
                }.get(op, op)

                # Format based on type
                if cond_type == "piston":
                    lines.append(f"{prefix}Piston '{source}' {op_display} {value}")
                elif cond_type == "sensor":
                    lines.append(f"{prefix}Sensor '{source}' {op_display} {value}")
                elif cond_type == "position":
                    lines.append(f"{prefix}Position '{source}' {op_display} {value}")
                else:
                    lines.append(f"{prefix}{source} {op_display} {value}")

            # Add operator between items (not after last)
            if i < len(items) - 1:
                lines.append(f"{prefix}  {op_symbol}")

        return "\n".join(lines)

    def format_blocked_operations(self, blocks):
        """Format blocked operations for display, including tools"""
        if not blocks:
            return "None"

        lines = []
        for block in blocks:
            op = block.get("operation", "")
            tools = block.get("tools", [])
            exclude_setup = block.get("exclude_setup", False)

            # Get friendly operation name
            op_desc = OPERATION_DESCRIPTIONS.get(op, op)

            if op == "tool_action" and tools:
                tools_str = ", ".join(tools)
                line = f"• {op}: {tools_str}"
            else:
                line = f"• {op}"

            if exclude_setup:
                line += " (except setup)"

            lines.append(line)

        return "\n".join(lines)

    def clear_details_panel(self):
        """Clear the details panel"""
        self.detail_id.config(text="-")
        self.detail_name.config(text="-")
        self.detail_status.config(text="-", foreground="black")
        self.detail_priority.config(text="-")
        self.detail_severity.config(text="-")
        self.detail_description.config(text="-")

        # Clear Text widgets
        self.detail_conditions.config(state="normal")
        self.detail_conditions.delete("1.0", tk.END)
        self.detail_conditions.insert("1.0", "-")
        self.detail_conditions.config(state="disabled")

        self.detail_blocks.config(state="normal")
        self.detail_blocks.delete("1.0", tk.END)
        self.detail_blocks.insert("1.0", "-")
        self.detail_blocks.config(state="disabled")

    def toggle_global_safety(self):
        """Toggle global safety system"""
        enabled = self.global_enabled_var.get()
        self.rules_data["global_enabled"] = enabled

        if not enabled:
            if not messagebox.askyesno(
                "Disable Safety",
                "WARNING: Disabling the safety system can lead to hardware damage!\n\n"
                "Are you sure you want to disable safety checks?"
            ):
                self.global_enabled_var.set(True)
                self.rules_data["global_enabled"] = True
                return

        self.save_rules()
        self.update_status()

        if hasattr(self.app, 'log'):
            status = "ENABLED" if enabled else "DISABLED"
            self.app.log("WARNING" if not enabled else "INFO", f"Global safety system {status}")

    def toggle_rule(self):
        """Toggle selected rule enabled/disabled"""
        if not self.selected_rule_id:
            return

        rule = self.get_rule_by_id(self.selected_rule_id)
        if rule:
            rule["enabled"] = not rule.get("enabled", True)
            self.save_rules()
            self.populate_rules_list()
            # Re-select the rule
            self.rules_tree.selection_set(self.selected_rule_id)
            self.update_details_panel()

    def add_rule(self):
        """Open dialog to add new rule"""
        self.open_rule_editor(None)

    def edit_rule(self):
        """Open dialog to edit selected rule"""
        if self.selected_rule_id:
            rule = self.get_rule_by_id(self.selected_rule_id)
            if rule:
                self.open_rule_editor(rule)

    def delete_rule(self):
        """Delete selected rule"""
        if not self.selected_rule_id:
            return

        rule = self.get_rule_by_id(self.selected_rule_id)
        if not rule:
            return

        if rule.get("is_system_rule", False):
            messagebox.showwarning("Cannot Delete", "System rules cannot be deleted. You can only disable them.")
            return

        if messagebox.askyesno("Delete Rule", f"Delete rule '{rule.get('name', self.selected_rule_id)}'?"):
            self.rules_data["rules"] = [r for r in self.rules_data["rules"] if r["id"] != self.selected_rule_id]
            self.save_rules()
            self.populate_rules_list()
            self.clear_details_panel()

    def open_rule_editor(self, rule):
        """Open rule editor dialog"""
        dialog = RuleEditorDialog(self.frame, rule, self.rules_data.get("available_sources", {}),
                                   self.rules_data.get("available_tools", AVAILABLE_TOOLS))
        self.frame.wait_window(dialog.dialog)

        if dialog.result:
            if rule:
                # Update existing rule
                for i, r in enumerate(self.rules_data["rules"]):
                    if r["id"] == rule["id"]:
                        self.rules_data["rules"][i] = dialog.result
                        break
            else:
                # Add new rule
                self.rules_data["rules"].append(dialog.result)

            self.save_rules()
            self.populate_rules_list()

    def refresh_rules(self):
        """Reload rules from file"""
        self.load_rules()
        self.populate_rules_list()
        self.update_status()

    def import_rules(self):
        """Import rules from file"""
        from tkinter import filedialog

        filename = filedialog.askopenfilename(
            title="Import Safety Rules",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    imported = json.load(f)

                if "rules" in imported:
                    # Merge or replace?
                    if messagebox.askyesno("Import Rules", "Merge with existing rules? (No = Replace all)"):
                        # Merge
                        existing_ids = {r["id"] for r in self.rules_data["rules"]}
                        for rule in imported["rules"]:
                            if rule["id"] not in existing_ids:
                                self.rules_data["rules"].append(rule)
                    else:
                        # Replace
                        self.rules_data["rules"] = imported["rules"]

                    self.save_rules()
                    self.populate_rules_list()
                    messagebox.showinfo("Success", "Rules imported successfully")
                else:
                    messagebox.showerror("Error", "Invalid rules file format")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to import rules: {e}")

    def export_rules(self):
        """Export rules to file"""
        from tkinter import filedialog

        filename = filedialog.asksaveasfilename(
            title="Export Safety Rules",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile="safety_rules_export.json"
        )

        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(self.rules_data, f, indent=2, ensure_ascii=False)
                messagebox.showinfo("Success", f"Rules exported to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export rules: {e}")

    def clear_violations(self):
        """Clear violations log"""
        self.violations_text.delete(1.0, tk.END)

        # Also clear from safety system if available
        if hasattr(self.app, 'hardware') and self.app.hardware:
            try:
                from core.safety_system import safety_system
                safety_system.clear_violations_log()
            except:
                pass

    def update_status(self):
        """Update status display"""
        # Update global status
        if self.rules_data.get("global_enabled", True):
            self.global_status_label.config(text="System Active", foreground="green")
        else:
            self.global_status_label.config(text="System DISABLED", foreground="red")

        # Update violations log
        try:
            from core.safety_system import safety_system
            violations = safety_system.get_violations_log()

            # Only update if there are new violations
            if violations:
                self.violations_text.delete(1.0, tk.END)
                for v in violations[-20:]:  # Show last 20
                    timestamp = datetime.fromtimestamp(v['timestamp']).strftime("%H:%M:%S")
                    self.violations_text.insert(tk.END, f"[{timestamp}] ", "timestamp")
                    self.violations_text.insert(tk.END, f"{v['safety_code']}\n", "critical")
        except:
            pass

        # Schedule next update
        if hasattr(self, 'frame') and self.frame.winfo_exists():
            self.frame.after(2000, self.update_status)


class RuleEditorDialog:
    """Dialog for creating/editing safety rules"""

    def __init__(self, parent, rule, available_sources, available_tools):
        self.result = None
        self.rule = rule
        self.available_sources = available_sources
        self.available_tools = available_tools or AVAILABLE_TOOLS
        self.is_new = rule is None

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Add New Rule" if self.is_new else "Edit Rule")
        self.dialog.geometry("700x800")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self.create_ui()

        if rule:
            self.populate_from_rule(rule)

    def create_ui(self):
        """Create the editor UI"""
        # Main scrollable frame
        canvas = tk.Canvas(self.dialog)
        scrollbar = ttk.Scrollbar(self.dialog, orient="vertical", command=canvas.yview)
        main_frame = ttk.Frame(canvas, padding="10")

        main_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=main_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # ID field
        row = 0
        ttk.Label(main_frame, text="Rule ID:").grid(row=row, column=0, sticky="w", pady=2)
        self.id_entry = ttk.Entry(main_frame, width=40)
        self.id_entry.grid(row=row, column=1, sticky="ew", pady=2)
        if not self.is_new:
            self.id_entry.config(state="disabled")

        # Name field
        row += 1
        ttk.Label(main_frame, text="Name:").grid(row=row, column=0, sticky="w", pady=2)
        self.name_entry = ttk.Entry(main_frame, width=40)
        self.name_entry.grid(row=row, column=1, sticky="ew", pady=2)

        # Description field
        row += 1
        ttk.Label(main_frame, text="Description:").grid(row=row, column=0, sticky="nw", pady=2)
        self.desc_text = tk.Text(main_frame, height=3, width=40)
        self.desc_text.grid(row=row, column=1, sticky="ew", pady=2)

        # Enabled checkbox
        row += 1
        self.enabled_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(main_frame, text="Enabled", variable=self.enabled_var).grid(row=row, column=1, sticky="w", pady=2)

        # Priority
        row += 1
        ttk.Label(main_frame, text="Priority:").grid(row=row, column=0, sticky="w", pady=2)
        self.priority_entry = ttk.Entry(main_frame, width=10)
        self.priority_entry.insert(0, "50")
        self.priority_entry.grid(row=row, column=1, sticky="w", pady=2)
        ttk.Label(main_frame, text="(lower = higher priority)", foreground="gray").grid(row=row, column=1, sticky="e", pady=2)

        # Severity
        row += 1
        ttk.Label(main_frame, text="Severity:").grid(row=row, column=0, sticky="w", pady=2)
        self.severity_var = tk.StringVar(value="critical")
        severity_combo = ttk.Combobox(main_frame, textvariable=self.severity_var,
                                       values=["critical", "warning", "info"], state="readonly", width=15)
        severity_combo.grid(row=row, column=1, sticky="w", pady=2)

        # Conditions section
        row += 1
        cond_frame = ttk.LabelFrame(main_frame, text="Conditions (when these are TRUE, operation is BLOCKED)", padding="5")
        cond_frame.grid(row=row, column=0, columnspan=2, sticky="ew", pady=10)

        # Condition operator
        op_frame = ttk.Frame(cond_frame)
        op_frame.pack(fill=tk.X, pady=5)
        ttk.Label(op_frame, text="Match:").pack(side=tk.LEFT)
        self.cond_operator_var = tk.StringVar(value="AND")
        ttk.Radiobutton(op_frame, text="ALL conditions (AND)", variable=self.cond_operator_var, value="AND").pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(op_frame, text="ANY condition (OR)", variable=self.cond_operator_var, value="OR").pack(side=tk.LEFT)

        # Conditions list
        self.conditions_frame = ttk.Frame(cond_frame)
        self.conditions_frame.pack(fill=tk.X, pady=5)
        self.condition_widgets = []

        ttk.Button(cond_frame, text="+ Add Condition", command=self.add_condition_row).pack(anchor="w")

        # Add one default condition row
        self.add_condition_row()

        # Blocked operations section
        row += 1
        ops_frame = ttk.LabelFrame(main_frame, text="Blocked Operations", padding="5")
        ops_frame.grid(row=row, column=0, columnspan=2, sticky="ew", pady=10)

        # Create operation widgets with tool selection for tool_action
        self.blocked_ops_frame = ttk.Frame(ops_frame)
        self.blocked_ops_frame.pack(fill=tk.X, pady=5)
        self.blocked_op_widgets = []

        ttk.Button(ops_frame, text="+ Add Blocked Operation", command=self.add_blocked_operation_row).pack(anchor="w")

        # Add one default operation row
        self.add_blocked_operation_row()

        # Message field
        row += 1
        ttk.Label(main_frame, text="Error Message:").grid(row=row, column=0, sticky="nw", pady=2)
        self.message_text = tk.Text(main_frame, height=3, width=40)
        self.message_text.grid(row=row, column=1, sticky="ew", pady=2)

        # Buttons
        row += 1
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=row, column=0, columnspan=2, pady=20)

        ttk.Button(btn_frame, text="Cancel", command=self.dialog.destroy).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Save", command=self.save).pack(side=tk.LEFT, padx=5)

        main_frame.columnconfigure(1, weight=1)

    def add_condition_row(self):
        """Add a condition row to the editor with smart dropdowns"""
        row_frame = ttk.Frame(self.conditions_frame)
        row_frame.pack(fill=tk.X, pady=2)

        # Type
        type_var = tk.StringVar(value="piston")
        type_combo = ttk.Combobox(row_frame, textvariable=type_var,
                                   values=["piston", "sensor", "position"], state="readonly", width=10)
        type_combo.pack(side=tk.LEFT, padx=2)

        # Source
        source_var = tk.StringVar()
        source_combo = ttk.Combobox(row_frame, textvariable=source_var, state="readonly", width=25)
        source_combo.pack(side=tk.LEFT, padx=2)

        # Operator
        op_var = tk.StringVar(value="equals")
        op_combo = ttk.Combobox(row_frame, textvariable=op_var,
                                 values=["equals", "not_equals", "greater_than", "less_than"],
                                 state="readonly", width=12)
        op_combo.pack(side=tk.LEFT, padx=2)

        # Value - will be either combobox or entry based on type
        value_frame = ttk.Frame(row_frame)
        value_frame.pack(side=tk.LEFT, padx=2)

        value_var = tk.StringVar()
        value_combo = ttk.Combobox(value_frame, textvariable=value_var, state="readonly", width=12)
        value_entry = ttk.Entry(value_frame, textvariable=value_var, width=15)

        # Start with combo for piston
        value_combo.pack()
        value_combo["values"] = PISTON_VALUES

        # Update source and value options based on type
        def update_sources_and_values(*args):
            cond_type = type_var.get()

            if cond_type == "piston":
                source_combo["values"] = self.available_sources.get("pistons", AVAILABLE_TOOLS[:5])
                # Show dropdown for value with up/down
                value_entry.pack_forget()
                value_combo.pack()
                value_combo["values"] = PISTON_VALUES
                value_combo.config(state="readonly")

            elif cond_type == "sensor":
                source_combo["values"] = self.available_sources.get("sensors", [])
                # For sensors, show dropdown with boolean or position values
                value_entry.pack_forget()
                value_combo.pack()
                # If it's a position sensor (like row_motor_limit_switch), use up/down
                source = source_var.get()
                if "limit_switch" in source or "position" in source:
                    value_combo["values"] = SENSOR_POSITION_VALUES
                else:
                    value_combo["values"] = SENSOR_BOOLEAN_VALUES + SENSOR_POSITION_VALUES
                value_combo.config(state="readonly")

            elif cond_type == "position":
                source_combo["values"] = self.available_sources.get("positions", ["x_position", "y_position"])
                # For position, show numeric entry
                value_combo.pack_forget()
                value_entry.pack()

        def update_value_options(*args):
            """Update value options when source changes"""
            cond_type = type_var.get()
            source = source_var.get()

            if cond_type == "sensor":
                if "limit_switch" in source or "_up_" in source or "_down_" in source:
                    value_combo["values"] = SENSOR_POSITION_VALUES
                else:
                    value_combo["values"] = SENSOR_BOOLEAN_VALUES + SENSOR_POSITION_VALUES

        type_var.trace_add("write", update_sources_and_values)
        source_var.trace_add("write", update_value_options)
        update_sources_and_values()

        # Remove button
        def remove_row():
            row_frame.destroy()
            self.condition_widgets = [w for w in self.condition_widgets if w["frame"].winfo_exists()]

        ttk.Button(row_frame, text="X", width=3, command=remove_row).pack(side=tk.LEFT, padx=2)

        self.condition_widgets.append({
            "frame": row_frame,
            "type": type_var,
            "source": source_var,
            "operator": op_var,
            "value": value_var,
            "value_combo": value_combo,
            "value_entry": value_entry
        })

    def add_blocked_operation_row(self):
        """Add a blocked operation row with tool selection"""
        row_frame = ttk.Frame(self.blocked_ops_frame)
        row_frame.pack(fill=tk.X, pady=2)

        # Operation dropdown
        op_var = tk.StringVar(value="move_y")
        op_combo = ttk.Combobox(row_frame, textvariable=op_var,
                                 values=list(OPERATION_DESCRIPTIONS.keys()),
                                 state="readonly", width=15)
        op_combo.pack(side=tk.LEFT, padx=2)

        # Description label
        desc_label = ttk.Label(row_frame, text=OPERATION_DESCRIPTIONS.get("move_y", ""),
                               foreground="gray", font=("Arial", 8))
        desc_label.pack(side=tk.LEFT, padx=5)

        # Tools frame (shown only for tool_action)
        tools_frame = ttk.Frame(row_frame)

        # Tools label and listbox
        ttk.Label(tools_frame, text="Tools:").pack(side=tk.LEFT, padx=2)

        # Use checkbuttons for tool selection
        tool_vars = {}
        tools_inner_frame = ttk.Frame(tools_frame)
        tools_inner_frame.pack(side=tk.LEFT, padx=2)

        for tool in self.available_tools:
            var = tk.BooleanVar(value=False)
            tool_vars[tool] = var
            ttk.Checkbutton(tools_inner_frame, text=tool, variable=var).pack(anchor="w")

        # Exclude setup checkbox
        exclude_setup_var = tk.BooleanVar(value=False)
        exclude_frame = ttk.Frame(row_frame)
        ttk.Checkbutton(exclude_frame, text="Exclude setup movements",
                        variable=exclude_setup_var).pack(anchor="w")

        # Update UI based on operation
        def update_operation(*args):
            op = op_var.get()
            desc_label.config(text=OPERATION_DESCRIPTIONS.get(op, ""))

            if op == "tool_action":
                tools_frame.pack(side=tk.LEFT, padx=5)
                exclude_frame.pack_forget()
            else:
                tools_frame.pack_forget()
                exclude_frame.pack(side=tk.LEFT, padx=5)

        op_var.trace_add("write", update_operation)
        update_operation()

        # Remove button
        def remove_row():
            row_frame.destroy()
            self.blocked_op_widgets = [w for w in self.blocked_op_widgets if w["frame"].winfo_exists()]

        ttk.Button(row_frame, text="X", width=3, command=remove_row).pack(side=tk.RIGHT, padx=2)

        self.blocked_op_widgets.append({
            "frame": row_frame,
            "operation": op_var,
            "tool_vars": tool_vars,
            "exclude_setup": exclude_setup_var
        })

    def populate_from_rule(self, rule):
        """Populate fields from existing rule"""
        self.id_entry.config(state="normal")
        self.id_entry.delete(0, tk.END)
        self.id_entry.insert(0, rule.get("id", ""))
        if not self.is_new:
            self.id_entry.config(state="disabled")

        self.name_entry.delete(0, tk.END)
        self.name_entry.insert(0, rule.get("name", ""))

        self.desc_text.delete(1.0, tk.END)
        self.desc_text.insert(1.0, rule.get("description", ""))

        self.enabled_var.set(rule.get("enabled", True))

        self.priority_entry.delete(0, tk.END)
        self.priority_entry.insert(0, str(rule.get("priority", 50)))

        self.severity_var.set(rule.get("severity", "critical"))

        # Conditions
        conditions = rule.get("conditions", {})
        self.cond_operator_var.set(conditions.get("operator", "AND"))

        # Clear existing condition rows
        for widget in self.condition_widgets:
            widget["frame"].destroy()
        self.condition_widgets = []

        # Add condition rows from rule
        for item in conditions.get("items", []):
            self.add_condition_row()
            widget = self.condition_widgets[-1]
            widget["type"].set(item.get("type", "piston"))

            # Need to update sources first
            self.dialog.update_idletasks()

            widget["source"].set(item.get("source", ""))
            widget["operator"].set(item.get("operator", "equals"))
            widget["value"].set(str(item.get("value", "")))

        # Blocked operations
        # Clear existing operation rows
        for widget in self.blocked_op_widgets:
            widget["frame"].destroy()
        self.blocked_op_widgets = []

        # Add operation rows from rule
        for op in rule.get("blocked_operations", []):
            self.add_blocked_operation_row()
            widget = self.blocked_op_widgets[-1]
            widget["operation"].set(op.get("operation", "move_y"))
            widget["exclude_setup"].set(op.get("exclude_setup", False))

            # Set selected tools
            tools = op.get("tools", [])
            for tool, var in widget["tool_vars"].items():
                var.set(tool in tools)

        self.message_text.delete(1.0, tk.END)
        self.message_text.insert(1.0, rule.get("message", ""))

    def save(self):
        """Save the rule"""
        # Validate
        rule_id = self.id_entry.get().strip()
        if not rule_id:
            messagebox.showerror("Error", "Rule ID is required")
            return

        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("Error", "Rule name is required")
            return

        # Build conditions
        conditions = {
            "operator": self.cond_operator_var.get(),
            "items": []
        }

        for widget in self.condition_widgets:
            if not widget["frame"].winfo_exists():
                continue

            cond = {
                "type": widget["type"].get(),
                "source": widget["source"].get(),
                "operator": widget["operator"].get(),
                "value": widget["value"].get()
            }

            # Convert numeric values
            if cond["type"] == "position":
                try:
                    cond["value"] = float(cond["value"])
                except ValueError:
                    pass

            if cond["source"]:  # Only add if source is set
                conditions["items"].append(cond)

        # Build blocked operations with tools
        blocked_ops = []
        for widget in self.blocked_op_widgets:
            if not widget["frame"].winfo_exists():
                continue

            op_name = widget["operation"].get()
            op_data = {"operation": op_name}

            if op_name == "tool_action":
                # Get selected tools
                selected_tools = [tool for tool, var in widget["tool_vars"].items() if var.get()]
                if selected_tools:
                    op_data["tools"] = selected_tools
            else:
                op_data["exclude_setup"] = widget["exclude_setup"].get()

            blocked_ops.append(op_data)

        # Create result
        self.result = {
            "id": rule_id,
            "name": name,
            "description": self.desc_text.get(1.0, tk.END).strip(),
            "enabled": self.enabled_var.get(),
            "priority": int(self.priority_entry.get() or 50),
            "severity": self.severity_var.get(),
            "is_system_rule": self.rule.get("is_system_rule", False) if self.rule else False,
            "conditions": conditions,
            "blocked_operations": blocked_ops,
            "message": self.message_text.get(1.0, tk.END).strip(),
            "created_at": self.rule.get("created_at", datetime.now().isoformat()) if self.rule else datetime.now().isoformat(),
            "created_by": self.rule.get("created_by", "admin") if self.rule else "admin"
        }

        self.dialog.destroy()
