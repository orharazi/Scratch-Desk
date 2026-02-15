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
from core.translations import t


# Known values for different condition types
PISTON_VALUES = ["up", "down"]
SENSOR_VALUES = ["active", "not_active"]

# Operation descriptions - Hebrew with motor names
OPERATION_DESCRIPTIONS = {
    "move_x": "תנועת ציר X (מנוע עמודות)",
    "move_y": "תנועת ציר Y (מנוע שורות)",
    "move_position": "תנועה למיקום מוחלט (שני צירים)",
    "tool_action": "פעולות כלים (בוכנות למעלה/למטה)",
    "wait_sensor": "המתנה לחיישן"
}

# Available tools for tool_action operations
AVAILABLE_TOOLS = [
    "line_marker",
    "line_cutter",
    "line_motor",
    "row_marker",
    "row_cutter"
]

# Display name mappings for Hebrew UI (internal_value -> display_value)
CONDITION_TYPE_DISPLAY = {
    "piston": t("Pistons"),
    "sensor": t("Sensor"),
    "position": t("Position")
}
CONDITION_TYPE_REVERSE = {v: k for k, v in CONDITION_TYPE_DISPLAY.items()}

OPERATOR_DISPLAY = {
    "equals": t("equals"),
    "not_equals": t("not_equals"),
    "greater_than": t("greater_than"),
    "less_than": t("less_than")
}
OPERATOR_REVERSE = {v: k for k, v in OPERATOR_DISPLAY.items()}

SEVERITY_DISPLAY = {
    "critical": t("critical"),
    "warning": t("Warning"),
    "info": t("Info")
}
SEVERITY_REVERSE = {v: k for k, v in SEVERITY_DISPLAY.items()}

OPERATION_DISPLAY = {
    "move_x": t("move_x") + " (עמודות)",
    "move_y": t("move_y") + " (שורות)",
    "move_position": t("move_position"),
    "tool_action": t("tool_action"),
    "wait_sensor": t("wait_sensor")
}
OPERATION_REVERSE = {v: k for k, v in OPERATION_DISPLAY.items()}

TOOL_DISPLAY = {tool: t(tool) for tool in AVAILABLE_TOOLS}
TOOL_REVERSE = {v: k for k, v in TOOL_DISPLAY.items()}

REASON_DISPLAY = {
    "operational": t("Operational"),
    "collision": t("Collision"),
    "mechanical": t("Mechanical")
}
REASON_REVERSE = {v: k for k, v in REASON_DISPLAY.items()}

REASON_COLORS = {
    "operational": "#F39C12",
    "collision": "#E74C3C",
    "mechanical": "#8E44AD"
}

ACTION_DISPLAY = {
    "emergency_pause": t("emergency_pause"),
}
ACTION_REVERSE = {v: k for k, v in ACTION_DISPLAY.items()}

RECOVERY_ACTION_DISPLAY = {
    "auto_resume": t("auto_resume"),
}
RECOVERY_ACTION_REVERSE = {v: k for k, v in RECOVERY_ACTION_DISPLAY.items()}

PISTON_VALUE_DISPLAY = [t("up"), t("down")]
SENSOR_VALUE_DISPLAY = [t("active"), t("not_active")]

# Combined reverse value mapping
VALUE_REVERSE = {
    t("up"): "up", t("down"): "down",
    t("true"): "true", t("false"): "false",
    t("active"): "active", t("not_active"): "not_active"
}


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
            messagebox.showerror(t("Error"), t("Failed to save rules: {error}", error=str(e)))
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

        ttk.Label(top_frame, text=t("Global Safety:"), font=("Arial", 10, "bold")).pack(side=tk.RIGHT, padx=(5, 0))

        self.global_toggle = ttk.Checkbutton(
            top_frame,
            text=t("Enabled"),
            variable=self.global_enabled_var,
            command=self.toggle_global_safety
        )
        self.global_toggle.pack(side=tk.RIGHT, padx=5)

        # Status indicator
        self.global_status_label = ttk.Label(top_frame, text="", font=("Arial", 10))
        self.global_status_label.pack(side=tk.RIGHT, padx=10)

        # Spacer
        ttk.Frame(top_frame).pack(side=tk.RIGHT, fill=tk.X, expand=True)

        # Action buttons
        ttk.Button(top_frame, text=t("+ Add Rule"), command=self.add_rule).pack(side=tk.LEFT, padx=2)
        ttk.Button(top_frame, text=t("Import"), command=self.import_rules).pack(side=tk.LEFT, padx=2)
        ttk.Button(top_frame, text=t("Export"), command=self.export_rules).pack(side=tk.LEFT, padx=2)
        ttk.Button(top_frame, text=t("Refresh"), command=self.refresh_rules).pack(side=tk.LEFT, padx=2)

    def create_rules_list(self):
        """Create rules list panel"""
        left_frame = ttk.LabelFrame(self.frame, text=t("Safety Rules"), padding="5")
        left_frame.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)
        left_frame.rowconfigure(0, weight=1)
        left_frame.columnconfigure(0, weight=1)

        # Create treeview for rules
        columns = ("enabled", "name", "severity", "type")
        self.rules_tree = ttk.Treeview(left_frame, columns=columns, show="headings", height=15)

        self.rules_tree.heading("enabled", text=t("On"))
        self.rules_tree.heading("name", text=t("Rule Name"))
        self.rules_tree.heading("severity", text=t("Severity"))
        self.rules_tree.heading("type", text=t("Type"))

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

        self.edit_btn = ttk.Button(btn_frame, text=t("Edit"), command=self.edit_rule, state="disabled")
        self.edit_btn.pack(side=tk.RIGHT, padx=2)

        self.delete_btn = ttk.Button(btn_frame, text=t("Delete"), command=self.delete_rule, state="disabled")
        self.delete_btn.pack(side=tk.RIGHT, padx=2)

        self.toggle_btn = ttk.Button(btn_frame, text=t("Enable/Disable"), command=self.toggle_rule, state="disabled")
        self.toggle_btn.pack(side=tk.RIGHT, padx=2)

        # Populate rules
        self.populate_rules_list()

    def create_details_panel(self):
        """Create rule details and violations panel"""
        right_frame = ttk.Frame(self.frame)
        right_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        right_frame.rowconfigure(0, weight=1)
        right_frame.rowconfigure(1, weight=1)
        right_frame.columnconfigure(0, weight=1)

        # Rule details
        details_frame = ttk.LabelFrame(right_frame, text=t("Rule Details"), padding="10")
        details_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 5))
        details_frame.columnconfigure(0, weight=1)

        # Detail labels - RTL: labels on right (column=1), values on left (column=0)
        row = 0
        ttk.Label(details_frame, text=t("ID:"), font=("Arial", 9, "bold")).grid(row=row, column=1, sticky="e", padx=(5, 0), pady=2)
        self.detail_id = ttk.Label(details_frame, text="-")
        self.detail_id.grid(row=row, column=0, sticky="e", pady=2)

        row += 1
        ttk.Label(details_frame, text=t("Name:"), font=("Arial", 9, "bold")).grid(row=row, column=1, sticky="e", padx=(5, 0), pady=2)
        self.detail_name = ttk.Label(details_frame, text="-")
        self.detail_name.grid(row=row, column=0, sticky="e", pady=2)

        row += 1
        ttk.Label(details_frame, text=t("Status:"), font=("Arial", 9, "bold")).grid(row=row, column=1, sticky="e", padx=(5, 0), pady=2)
        self.detail_status = ttk.Label(details_frame, text="-")
        self.detail_status.grid(row=row, column=0, sticky="e", pady=2)

        row += 1
        ttk.Label(details_frame, text=t("Priority:"), font=("Arial", 9, "bold")).grid(row=row, column=1, sticky="e", padx=(5, 0), pady=2)
        self.detail_priority = ttk.Label(details_frame, text="-")
        self.detail_priority.grid(row=row, column=0, sticky="e", pady=2)

        row += 1
        ttk.Label(details_frame, text=t("Severity:"), font=("Arial", 9, "bold")).grid(row=row, column=1, sticky="e", padx=(5, 0), pady=2)
        self.detail_severity = ttk.Label(details_frame, text="-")
        self.detail_severity.grid(row=row, column=0, sticky="e", pady=2)

        row += 1
        ttk.Label(details_frame, text=t("Reason:"), font=("Arial", 9, "bold")).grid(row=row, column=1, sticky="e", padx=(5, 0), pady=2)
        self.detail_reason = ttk.Label(details_frame, text="-")
        self.detail_reason.grid(row=row, column=0, sticky="e", pady=2)

        row += 1
        ttk.Label(details_frame, text=t("Real-time:"), font=("Arial", 9, "bold")).grid(row=row, column=1, sticky="e", padx=(5, 0), pady=2)
        self.detail_realtime = ttk.Label(details_frame, text="-")
        self.detail_realtime.grid(row=row, column=0, sticky="e", pady=2)

        row += 1
        ttk.Label(details_frame, text=t("Description:"), font=("Arial", 9, "bold")).grid(row=row, column=1, sticky="ne", padx=(5, 0), pady=2)
        self.detail_description = ttk.Label(details_frame, text="-", wraplength=300, justify="right")
        self.detail_description.grid(row=row, column=0, sticky="e", pady=2)

        row += 1
        ttk.Label(details_frame, text=t("Conditions:"), font=("Arial", 9, "bold")).grid(row=row, column=1, sticky="ne", padx=(5, 0), pady=2)
        # Use Text widget for multiline conditions display
        self.detail_conditions = tk.Text(details_frame, height=5, width=35, wrap=tk.WORD,
                                         font=("Consolas", 9), bg="#f5f5f5", fg="black", relief="flat",
                                         state="disabled")
        self.detail_conditions.grid(row=row, column=0, sticky="e", pady=2)

        row += 1
        ttk.Label(details_frame, text=t("Blocks:"), font=("Arial", 9, "bold")).grid(row=row, column=1, sticky="ne", padx=(5, 0), pady=2)
        # Use Text widget for multiline blocks display
        self.detail_blocks = tk.Text(details_frame, height=3, width=35, wrap=tk.WORD,
                                     font=("Consolas", 9), bg="#f5f5f5", fg="black", relief="flat",
                                     state="disabled")
        self.detail_blocks.grid(row=row, column=0, sticky="e", pady=2)

        # Violations log
        violations_frame = ttk.LabelFrame(right_frame, text=t("Recent Violations"), padding="5")
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
        ttk.Button(violations_frame, text=t("Clear Log"), command=self.clear_violations).grid(row=1, column=0, sticky="e", pady=(5, 0))

    def populate_rules_list(self):
        """Populate the rules treeview"""
        # Clear existing items
        for item in self.rules_tree.get_children():
            self.rules_tree.delete(item)

        # Add rules
        for rule in self.rules_data.get("rules", []):
            enabled_text = t("Yes") if rule.get("enabled", True) else t("No")
            rule_type = t("System") if rule.get("is_system_rule", False) else t("Custom")
            severity_raw = rule.get("severity", "info")
            severity = SEVERITY_DISPLAY.get(severity_raw, severity_raw)

            # Prefer Hebrew name if available
            display_name = rule.get("name_he", rule.get("name", rule["id"]))

            self.rules_tree.insert("", "end", iid=rule["id"], values=(
                enabled_text,
                display_name,
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
        # Prefer Hebrew name/description/message
        display_name = rule.get("name_he", rule.get("name", "-"))
        self.detail_name.config(text=display_name)

        # Status with color
        if rule.get("enabled", True):
            self.detail_status.config(text=t("Enabled"), foreground="green")
        else:
            self.detail_status.config(text=t("Disabled"), foreground="red")

        self.detail_priority.config(text=str(rule.get("priority", "-")))
        severity_raw = rule.get("severity", "-")
        self.detail_severity.config(text=SEVERITY_DISPLAY.get(severity_raw, severity_raw))

        # Reason field
        reason = rule.get("reason", "")
        reason_display = rule.get("reason_he", REASON_DISPLAY.get(reason, reason)) if reason else "-"
        reason_color = REASON_COLORS.get(reason, "black")
        self.detail_reason.config(text=reason_display, foreground=reason_color)

        # Real-time monitoring field
        monitor = rule.get("monitor", {})
        if monitor.get("enabled", False):
            contexts = monitor.get("operation_context", [])
            context_str = ", ".join([t(c.title()) for c in contexts])
            self.detail_realtime.config(text=context_str, foreground="blue")
        else:
            has_blocked_ops = bool(rule.get("blocked_operations", []))
            self.detail_realtime.config(
                text=t("Pre-step only") if has_blocked_ops else "-",
                foreground="gray"
            )

        display_desc = rule.get("description_he", rule.get("description", "-"))
        self.detail_description.config(text=display_desc)

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
        self.detail_blocks.insert("1.0", blocks_text or t("None"))
        self.detail_blocks.config(state="disabled")

    def format_conditions(self, conditions, indent=0):
        """Format conditions for display in a readable way"""
        if not conditions:
            return t("No conditions")

        operator = conditions.get("operator", "AND")
        items = conditions.get("items", [])

        if not items:
            return t("No conditions")

        # Operator symbols
        op_symbol = "וגם" if operator == "AND" else "או"

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

                # Format based on type - with Hebrew labels
                source_display = t(source) if source else source
                value_display = t(str(value)) if value else str(value)
                if cond_type == "piston":
                    lines.append(f"{prefix}{t('Pistons')} '{source_display}' {op_display} {value_display}")
                elif cond_type == "sensor":
                    lines.append(f"{prefix}{t('Sensor')} '{source_display}' {op_display} {value_display}")
                elif cond_type == "position":
                    lines.append(f"{prefix}{t('Position')} '{source_display}' {op_display} {value_display}")
                else:
                    lines.append(f"{prefix}{source_display} {op_display} {value_display}")

            # Add operator between items (not after last)
            if i < len(items) - 1:
                lines.append(f"{prefix}  {op_symbol}")

        return "\n".join(lines)

    def format_blocked_operations(self, blocks):
        """Format blocked operations for display, including tools and direction"""
        if not blocks:
            return t("None")

        lines = []
        for block in blocks:
            op = block.get("operation", "")
            tools = block.get("tools", [])
            exclude_setup = block.get("exclude_setup", False)
            direction = block.get("direction", "")

            # Get translated operation name
            op_display = OPERATION_DISPLAY.get(op, t(op))

            if op == "tool_action" and tools:
                tools_str = ", ".join([TOOL_DISPLAY.get(tool, t(tool)) for tool in tools])
                line = f"• {op_display}: {tools_str}"
            else:
                line = f"• {op_display}"

            if direction:
                line += f" [{t(direction)}]"

            if exclude_setup:
                line += " " + t("(except setup)")

            lines.append(line)

        return "\n".join(lines)

    def clear_details_panel(self):
        """Clear the details panel"""
        self.detail_id.config(text="-")
        self.detail_name.config(text="-")
        self.detail_status.config(text="-", foreground="black")
        self.detail_priority.config(text="-")
        self.detail_severity.config(text="-")
        self.detail_reason.config(text="-", foreground="black")
        self.detail_realtime.config(text="-", foreground="black")
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
                t("Disable Safety"),
                t("WARNING: Disabling the safety system can lead to hardware damage!\n\nAre you sure you want to disable safety checks?")
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
            messagebox.showwarning(t("Cannot Delete"), t("System rules cannot be deleted. You can only disable them."))
            return

        if messagebox.askyesno(t("Delete Rule"), t("Delete rule '{name}'?", name=rule.get('name', self.selected_rule_id))):
            self.rules_data["rules"] = [r for r in self.rules_data["rules"] if r["id"] != self.selected_rule_id]
            self.save_rules()
            self.populate_rules_list()
            self.clear_details_panel()

    def open_rule_editor(self, rule):
        """Open rule editor dialog"""
        dialog = RuleEditorDialog(self.frame, rule, self.rules_data.get("available_sources", {}),
                                   self.rules_data.get("available_tools", AVAILABLE_TOOLS),
                                   self.rules_data.get("available_directions", {}))
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
            title=t("Import Safety Rules"),
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    imported = json.load(f)

                if "rules" in imported:
                    # Merge or replace?
                    if messagebox.askyesno(t("Import Rules"), t("Merge with existing rules? (No = Replace all)")):
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
                    messagebox.showinfo(t("Success"), t("Rules imported successfully"))
                else:
                    messagebox.showerror(t("Error"), t("Invalid rules file format"))
            except Exception as e:
                messagebox.showerror(t("Error"), t("Failed to import rules: {error}", error=str(e)))

    def export_rules(self):
        """Export rules to file"""
        from tkinter import filedialog

        exports_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data', 'exports')
        os.makedirs(exports_dir, exist_ok=True)

        filename = filedialog.asksaveasfilename(
            title=t("Export Safety Rules"),
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir=exports_dir,
            initialfile="safety_rules_export.json"
        )

        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(self.rules_data, f, indent=2, ensure_ascii=False)
                messagebox.showinfo(t("Success"), t("Rules exported to {filename}", filename=filename))
            except Exception as e:
                messagebox.showerror(t("Error"), t("Failed to export rules: {error}", error=str(e)))

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
            self.global_status_label.config(text=t("System Active"), foreground="green")
        else:
            self.global_status_label.config(text=t("System DISABLED"), foreground="red")

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

    def __init__(self, parent, rule, available_sources, available_tools, available_directions=None):
        self.result = None
        self.rule = rule
        self.available_sources = available_sources
        self.available_tools = available_tools or AVAILABLE_TOOLS
        self.available_directions = available_directions or {}
        self.is_new = rule is None

        self.dialog = tk.Toplevel(parent)
        self.dialog.title(t("Add New Rule") if self.is_new else t("Edit Rule"))
        self.dialog.geometry("900x850")
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

        # RTL: scrollbar on left, canvas on right
        scrollbar.pack(side="left", fill="y")
        canvas.pack(side="right", fill="both", expand=True)

        # RTL layout: labels on right (column=1), inputs on left (column=0)
        main_frame.columnconfigure(0, weight=1)

        # ID field
        row = 0
        ttk.Label(main_frame, text=t("Rule ID:")).grid(row=row, column=1, sticky="e", pady=2)
        self.id_entry = ttk.Entry(main_frame, width=40)
        self.id_entry.grid(row=row, column=0, sticky="ew", pady=2)
        if not self.is_new:
            self.id_entry.config(state="disabled")

        # Name field
        row += 1
        ttk.Label(main_frame, text=t("Name:")).grid(row=row, column=1, sticky="e", pady=2)
        self.name_entry = ttk.Entry(main_frame, width=40)
        self.name_entry.grid(row=row, column=0, sticky="ew", pady=2)

        # Description field
        row += 1
        ttk.Label(main_frame, text=t("Description:")).grid(row=row, column=1, sticky="ne", pady=2)
        self.desc_text = tk.Text(main_frame, height=3, width=40)
        self.desc_text.grid(row=row, column=0, sticky="ew", pady=2)

        # Enabled checkbox
        row += 1
        self.enabled_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(main_frame, text=t("Enabled"), variable=self.enabled_var).grid(row=row, column=0, sticky="e", pady=2)

        # Priority
        row += 1
        ttk.Label(main_frame, text=t("Priority:")).grid(row=row, column=1, sticky="e", pady=2)
        priority_frame = ttk.Frame(main_frame)
        priority_frame.grid(row=row, column=0, sticky="e", pady=2)
        ttk.Label(priority_frame, text=t("(lower = higher priority)"), foreground="gray").pack(side=tk.LEFT, padx=5)
        self.priority_entry = ttk.Entry(priority_frame, width=10)
        self.priority_entry.insert(0, "50")
        self.priority_entry.pack(side=tk.RIGHT)

        # Severity
        row += 1
        ttk.Label(main_frame, text=t("Severity:")).grid(row=row, column=1, sticky="e", pady=2)
        self.severity_var = tk.StringVar(value=SEVERITY_DISPLAY["critical"])
        severity_combo = ttk.Combobox(main_frame, textvariable=self.severity_var,
                                       values=list(SEVERITY_DISPLAY.values()), state="readonly", width=15)
        severity_combo.grid(row=row, column=0, sticky="e", pady=2)

        # Reason
        row += 1
        ttk.Label(main_frame, text=t("Reason:")).grid(row=row, column=1, sticky="e", pady=2)
        self.reason_var = tk.StringVar(value="")
        reason_combo = ttk.Combobox(main_frame, textvariable=self.reason_var,
                                     values=[""] + list(REASON_DISPLAY.values()), state="readonly", width=15)
        reason_combo.grid(row=row, column=0, sticky="e", pady=2)

        # Conditions section
        row += 1
        cond_frame = ttk.LabelFrame(main_frame, text=t("Conditions (when these are TRUE, operation is BLOCKED)"), padding="5")
        cond_frame.grid(row=row, column=0, columnspan=2, sticky="ew", pady=10)

        # Condition operator - RTL: label on right, options follow
        op_frame = ttk.Frame(cond_frame)
        op_frame.pack(fill=tk.X, pady=5)
        ttk.Label(op_frame, text=t("Match:")).pack(side=tk.RIGHT, padx=(0, 5))
        self.cond_operator_var = tk.StringVar(value="AND")
        ttk.Radiobutton(op_frame, text=t("ALL conditions (AND)"), variable=self.cond_operator_var, value="AND").pack(side=tk.RIGHT, padx=5)
        ttk.Radiobutton(op_frame, text=t("ANY condition (OR)"), variable=self.cond_operator_var, value="OR").pack(side=tk.RIGHT, padx=5)

        # Conditions list
        self.conditions_frame = ttk.Frame(cond_frame)
        self.conditions_frame.pack(fill=tk.X, pady=5)
        self.condition_widgets = []

        ttk.Button(cond_frame, text=t("+ Add Condition"), command=self.add_condition_row).pack(anchor="w")

        # Add one default condition row
        self.add_condition_row()

        # Blocked operations section
        row += 1
        ops_frame = ttk.LabelFrame(main_frame, text=t("Blocked Operations"), padding="5")
        ops_frame.grid(row=row, column=0, columnspan=2, sticky="ew", pady=10)

        # Create operation widgets with tool selection for tool_action
        self.blocked_ops_frame = ttk.Frame(ops_frame)
        self.blocked_ops_frame.pack(fill=tk.X, pady=5)
        self.blocked_op_widgets = []

        ttk.Button(ops_frame, text=t("+ Add Blocked Operation"), command=self.add_blocked_operation_row).pack(anchor="w")

        # Add one default operation row
        self.add_blocked_operation_row()

        # Real-Time Monitoring section
        row += 1
        monitor_frame = ttk.LabelFrame(main_frame, text=t("Real-Time Monitoring"), padding="5")
        monitor_frame.grid(row=row, column=0, columnspan=2, sticky="ew", pady=10)

        # Enable monitoring checkbox
        monitor_top = ttk.Frame(monitor_frame)
        monitor_top.pack(fill=tk.X, pady=2)

        self.monitor_enabled_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(monitor_top, text=t("Enable real-time monitoring"),
                        variable=self.monitor_enabled_var,
                        command=self._toggle_monitor_fields).pack(side=tk.RIGHT)

        # Operation context
        context_frame = ttk.Frame(monitor_frame)
        context_frame.pack(fill=tk.X, pady=2)
        ttk.Label(context_frame, text=t("Operation context:")).pack(side=tk.RIGHT, padx=(0, 5))
        self.monitor_lines_var = tk.BooleanVar(value=False)
        self.monitor_rows_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(context_frame, text=t("Lines"), variable=self.monitor_lines_var).pack(side=tk.RIGHT, padx=2)
        ttk.Checkbutton(context_frame, text=t("Rows"), variable=self.monitor_rows_var).pack(side=tk.RIGHT, padx=2)

        # Action
        action_frame = ttk.Frame(monitor_frame)
        action_frame.pack(fill=tk.X, pady=2)
        ttk.Label(action_frame, text=t("Action:")).pack(side=tk.RIGHT, padx=(0, 5))
        self.monitor_action_var = tk.StringVar(value=ACTION_DISPLAY["emergency_pause"])
        ttk.Combobox(action_frame, textvariable=self.monitor_action_var,
                     values=list(ACTION_DISPLAY.values()), state="readonly", width=18).pack(side=tk.RIGHT, padx=2)

        # Recovery action
        recovery_action_frame = ttk.Frame(monitor_frame)
        recovery_action_frame.pack(fill=tk.X, pady=2)
        ttk.Label(recovery_action_frame, text=t("Recovery action:")).pack(side=tk.RIGHT, padx=(0, 5))
        self.monitor_recovery_action_var = tk.StringVar(value=RECOVERY_ACTION_DISPLAY["auto_resume"])
        ttk.Combobox(recovery_action_frame, textvariable=self.monitor_recovery_action_var,
                     values=list(RECOVERY_ACTION_DISPLAY.values()), state="readonly", width=18).pack(side=tk.RIGHT, padx=2)

        # Recovery conditions
        recovery_cond_label = ttk.Label(monitor_frame, text=t("Recovery Conditions (when these are TRUE, auto-resume):"),
                                         font=("Arial", 9, "bold"))
        recovery_cond_label.pack(fill=tk.X, pady=(5, 2), anchor="e")

        # Recovery condition operator
        recovery_op_frame = ttk.Frame(monitor_frame)
        recovery_op_frame.pack(fill=tk.X, pady=2)
        ttk.Label(recovery_op_frame, text=t("Match:")).pack(side=tk.RIGHT, padx=(0, 5))
        self.recovery_cond_operator_var = tk.StringVar(value="AND")
        ttk.Radiobutton(recovery_op_frame, text=t("ALL (AND)"), variable=self.recovery_cond_operator_var, value="AND").pack(side=tk.RIGHT, padx=3)
        ttk.Radiobutton(recovery_op_frame, text=t("ANY (OR)"), variable=self.recovery_cond_operator_var, value="OR").pack(side=tk.RIGHT, padx=3)

        # Recovery conditions list
        self.recovery_conditions_frame = ttk.Frame(monitor_frame)
        self.recovery_conditions_frame.pack(fill=tk.X, pady=2)
        self.recovery_condition_widgets = []

        ttk.Button(monitor_frame, text=t("+ Add Recovery Condition"),
                   command=self.add_recovery_condition_row).pack(anchor="w")

        # Store reference for toggling
        self.monitor_fields_frame = monitor_frame

        # Message field
        row += 1
        ttk.Label(main_frame, text=t("Error Message:")).grid(row=row, column=1, sticky="ne", pady=2)
        self.message_text = tk.Text(main_frame, height=3, width=40)
        self.message_text.grid(row=row, column=0, sticky="ew", pady=2)

        # Buttons
        row += 1
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=row, column=0, columnspan=2, pady=20)

        ttk.Button(btn_frame, text=t("Save"), command=self.save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text=t("Cancel"), command=self.dialog.destroy).pack(side=tk.RIGHT, padx=5)

    def _toggle_monitor_fields(self):
        """Toggle monitor fields visibility based on checkbox"""
        # Fields are always visible, just enable/disable state indicator
        pass

    def add_recovery_condition_row(self):
        """Add a recovery condition row (reuses same UI pattern as violation conditions)"""
        row_frame = ttk.Frame(self.recovery_conditions_frame)
        row_frame.pack(fill=tk.X, pady=2)

        # Type
        type_var = tk.StringVar(value=CONDITION_TYPE_DISPLAY["piston"])
        type_combo = ttk.Combobox(row_frame, textvariable=type_var,
                                   values=list(CONDITION_TYPE_DISPLAY.values()), state="readonly", width=10)
        type_combo.pack(side=tk.RIGHT, padx=2)

        # Source
        source_var = tk.StringVar()
        source_combo = ttk.Combobox(row_frame, textvariable=source_var, state="readonly", width=25)
        source_combo.pack(side=tk.RIGHT, padx=2)

        # Operator
        op_var = tk.StringVar(value=OPERATOR_DISPLAY["equals"])
        op_combo = ttk.Combobox(row_frame, textvariable=op_var,
                                 values=list(OPERATOR_DISPLAY.values()),
                                 state="readonly", width=12)
        op_combo.pack(side=tk.RIGHT, padx=2)

        # Value
        value_frame = ttk.Frame(row_frame)
        value_frame.pack(side=tk.RIGHT, padx=2)

        value_var = tk.StringVar()
        value_combo = ttk.Combobox(value_frame, textvariable=value_var, state="readonly", width=12)
        value_entry = ttk.Entry(value_frame, textvariable=value_var, width=15)
        value_combo.pack()
        value_combo["values"] = PISTON_VALUE_DISPLAY

        def update_sources_and_values(*args):
            source_var.set("")   # Clear stale source
            value_var.set("")    # Clear stale value
            cond_type_display = type_var.get()
            cond_type = CONDITION_TYPE_REVERSE.get(cond_type_display, cond_type_display)
            if cond_type == "piston":
                sources = self.available_sources.get("pistons", AVAILABLE_TOOLS[:5])
                source_combo["values"] = [t(s) for s in sources]
                value_entry.pack_forget()
                value_combo.pack()
                value_combo["values"] = PISTON_VALUE_DISPLAY
            elif cond_type == "sensor":
                sources = self.available_sources.get("sensors", [])
                source_combo["values"] = [t(s) for s in sources]
                value_entry.pack_forget()
                value_combo.pack()
                value_combo["values"] = SENSOR_VALUE_DISPLAY
            elif cond_type == "position":
                sources = self.available_sources.get("positions", ["x_position", "y_position"])
                source_combo["values"] = [t(s) for s in sources]
                value_combo.pack_forget()
                value_entry.pack()

        type_var.trace_add("write", update_sources_and_values)
        update_sources_and_values()

        def remove_row():
            row_frame.destroy()
            self.recovery_condition_widgets = [w for w in self.recovery_condition_widgets if w["frame"].winfo_exists()]

        ttk.Button(row_frame, text="X", width=3, command=remove_row).pack(side=tk.LEFT, padx=2)

        self.recovery_condition_widgets.append({
            "frame": row_frame,
            "type": type_var,
            "source": source_var,
            "operator": op_var,
            "value": value_var,
            "value_combo": value_combo,
            "value_entry": value_entry
        })

    def add_condition_row(self):
        """Add a condition row to the editor with smart dropdowns"""
        row_frame = ttk.Frame(self.conditions_frame)
        row_frame.pack(fill=tk.X, pady=2)

        # Type - translated display values
        type_var = tk.StringVar(value=CONDITION_TYPE_DISPLAY["piston"])
        type_combo = ttk.Combobox(row_frame, textvariable=type_var,
                                   values=list(CONDITION_TYPE_DISPLAY.values()), state="readonly", width=10)
        type_combo.pack(side=tk.RIGHT, padx=2)

        # Source - will be populated with translated names
        source_var = tk.StringVar()
        source_combo = ttk.Combobox(row_frame, textvariable=source_var, state="readonly", width=25)
        source_combo.pack(side=tk.RIGHT, padx=2)

        # Operator - translated display values
        op_var = tk.StringVar(value=OPERATOR_DISPLAY["equals"])
        op_combo = ttk.Combobox(row_frame, textvariable=op_var,
                                 values=list(OPERATOR_DISPLAY.values()),
                                 state="readonly", width=12)
        op_combo.pack(side=tk.RIGHT, padx=2)

        # Value - will be either combobox or entry based on type
        value_frame = ttk.Frame(row_frame)
        value_frame.pack(side=tk.RIGHT, padx=2)

        value_var = tk.StringVar()
        value_combo = ttk.Combobox(value_frame, textvariable=value_var, state="readonly", width=12)
        value_entry = ttk.Entry(value_frame, textvariable=value_var, width=15)

        # Start with combo for piston - translated values
        value_combo.pack()
        value_combo["values"] = PISTON_VALUE_DISPLAY

        # Update source and value options based on type
        def update_sources_and_values(*args):
            source_var.set("")   # Clear stale source
            value_var.set("")    # Clear stale value
            cond_type_display = type_var.get()
            cond_type = CONDITION_TYPE_REVERSE.get(cond_type_display, cond_type_display)

            if cond_type == "piston":
                sources = self.available_sources.get("pistons", AVAILABLE_TOOLS[:5])
                source_combo["values"] = [t(s) for s in sources]
                value_entry.pack_forget()
                value_combo.pack()
                value_combo["values"] = PISTON_VALUE_DISPLAY
                value_combo.config(state="readonly")

            elif cond_type == "sensor":
                sources = self.available_sources.get("sensors", [])
                source_combo["values"] = [t(s) for s in sources]
                value_entry.pack_forget()
                value_combo.pack()
                value_combo["values"] = SENSOR_VALUE_DISPLAY
                value_combo.config(state="readonly")

            elif cond_type == "position":
                sources = self.available_sources.get("positions", ["x_position", "y_position"])
                source_combo["values"] = [t(s) for s in sources]
                value_combo.pack_forget()
                value_entry.pack()

        def update_value_options(*args):
            """Update value options when source changes"""
            cond_type_display = type_var.get()
            cond_type = CONDITION_TYPE_REVERSE.get(cond_type_display, cond_type_display)

            if cond_type == "sensor":
                value_combo["values"] = SENSOR_VALUE_DISPLAY

        type_var.trace_add("write", update_sources_and_values)
        source_var.trace_add("write", update_value_options)
        update_sources_and_values()

        # Remove button - on left side for RTL
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
        """Add a blocked operation row with tool selection and direction"""
        row_frame = ttk.Frame(self.blocked_ops_frame)
        row_frame.pack(fill=tk.X, pady=2)

        # Operation dropdown - translated display values
        op_var = tk.StringVar(value=OPERATION_DISPLAY["move_y"])
        op_combo = ttk.Combobox(row_frame, textvariable=op_var,
                                 values=list(OPERATION_DISPLAY.values()),
                                 state="readonly", width=15)
        op_combo.pack(side=tk.RIGHT, padx=2)

        # Direction dropdown (shown only for movement operations)
        direction_frame = ttk.Frame(row_frame)
        direction_var = tk.StringVar(value="")
        ttk.Label(direction_frame, text=t("Dir:")).pack(side=tk.LEFT, padx=(0, 2))
        direction_combo = ttk.Combobox(direction_frame, textvariable=direction_var,
                                        state="readonly", width=10)
        direction_combo.pack(side=tk.LEFT)

        # Description label
        desc_label = ttk.Label(row_frame, text=OPERATION_DESCRIPTIONS.get("move_y", ""),
                               foreground="gray", font=("Arial", 8))
        desc_label.pack(side=tk.RIGHT, padx=5)

        # Tools frame (shown only for tool_action)
        tools_frame = ttk.Frame(row_frame)

        # Tools label and listbox
        ttk.Label(tools_frame, text=t("Tools:")).pack(side=tk.RIGHT, padx=2)

        # Use checkbuttons for tool selection - translated display names
        tool_vars = {}
        tools_inner_frame = ttk.Frame(tools_frame)
        tools_inner_frame.pack(side=tk.RIGHT, padx=2)

        for tool in self.available_tools:
            var = tk.BooleanVar(value=False)
            tool_vars[tool] = var
            ttk.Checkbutton(tools_inner_frame, text=TOOL_DISPLAY.get(tool, tool), variable=var).pack(anchor="e")

        # Exclude setup checkbox
        exclude_setup_var = tk.BooleanVar(value=False)
        exclude_frame = ttk.Frame(row_frame)
        ttk.Checkbutton(exclude_frame, text=t("Exclude setup movements"),
                        variable=exclude_setup_var).pack(anchor="e")

        # Update UI based on operation
        def update_operation(*args):
            op_display = op_var.get()
            op_internal = OPERATION_REVERSE.get(op_display, op_display)
            desc_label.config(text=OPERATION_DESCRIPTIONS.get(op_internal, ""))

            if op_internal == "tool_action":
                tools_frame.pack(side=tk.RIGHT, padx=5)
                exclude_frame.pack_forget()
                direction_frame.pack_forget()
            elif op_internal in self.available_directions:
                tools_frame.pack_forget()
                exclude_frame.pack(side=tk.RIGHT, padx=5)
                # Show direction dropdown with translated options
                dir_options = list(self.available_directions[op_internal].keys())
                translated_dirs = [t(d) for d in dir_options]
                direction_combo["values"] = translated_dirs
                direction_frame.pack(side=tk.RIGHT, padx=2, after=op_combo)
                # Default to "all_directions" if not set
                if not direction_var.get():
                    direction_var.set(t("all_directions"))
            else:
                tools_frame.pack_forget()
                exclude_frame.pack(side=tk.RIGHT, padx=5)
                direction_frame.pack_forget()
                direction_var.set("")

            # Also hide direction for tool_action
            if op_internal == "tool_action":
                direction_frame.pack_forget()
                direction_var.set("")

        op_var.trace_add("write", update_operation)
        update_operation()

        # Remove button
        def remove_row():
            row_frame.destroy()
            self.blocked_op_widgets = [w for w in self.blocked_op_widgets if w["frame"].winfo_exists()]

        ttk.Button(row_frame, text="X", width=3, command=remove_row).pack(side=tk.LEFT, padx=2)

        self.blocked_op_widgets.append({
            "frame": row_frame,
            "operation": op_var,
            "direction": direction_var,
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

        # Convert severity to display value
        severity = rule.get("severity", "critical")
        self.severity_var.set(SEVERITY_DISPLAY.get(severity, severity))

        # Reason
        reason = rule.get("reason", "")
        self.reason_var.set(REASON_DISPLAY.get(reason, reason))

        # Monitor settings
        monitor = rule.get("monitor", {})
        self.monitor_enabled_var.set(monitor.get("enabled", False))
        contexts = monitor.get("operation_context", [])
        self.monitor_lines_var.set("lines" in contexts)
        self.monitor_rows_var.set("rows" in contexts)
        action_val = monitor.get("action", "emergency_pause")
        self.monitor_action_var.set(ACTION_DISPLAY.get(action_val, action_val))
        recovery_action_val = monitor.get("recovery_action", "auto_resume")
        self.monitor_recovery_action_var.set(RECOVERY_ACTION_DISPLAY.get(recovery_action_val, recovery_action_val))

        # Recovery conditions
        recovery = monitor.get("recovery_conditions", {})
        self.recovery_cond_operator_var.set(recovery.get("operator", "AND"))

        # Clear existing recovery condition rows
        for widget in self.recovery_condition_widgets:
            widget["frame"].destroy()
        self.recovery_condition_widgets = []

        # Add recovery condition rows from rule
        for item in recovery.get("items", []):
            self.add_recovery_condition_row()
            widget = self.recovery_condition_widgets[-1]

            # Set type with display value
            item_type = item.get("type", "piston")
            widget["type"].set(CONDITION_TYPE_DISPLAY.get(item_type, item_type))

            self.dialog.update_idletasks()

            # Set source with translated display value
            source = item.get("source", "")
            widget["source"].set(t(source) if source else "")

            # Set operator with display value
            item_op = item.get("operator", "equals")
            widget["operator"].set(OPERATOR_DISPLAY.get(item_op, item_op))

            # Set value with translated display value
            item_val = str(item.get("value", ""))
            item_type_internal = CONDITION_TYPE_REVERSE.get(widget["type"].get(), "")
            if item_type_internal == "sensor":
                if item_val in ("down", "true", "active"):
                    widget["value"].set(t("active"))
                elif item_val in ("up", "false", "not_active"):
                    widget["value"].set(t("not_active"))
                else:
                    widget["value"].set(item_val)
            elif item_val in ("up", "down", "true", "false"):
                widget["value"].set(t(item_val))
            else:
                widget["value"].set(item_val)

        # Conditions
        conditions = rule.get("conditions", {})
        self.cond_operator_var.set(conditions.get("operator", "AND"))

        # Clear existing condition rows
        for widget in self.condition_widgets:
            widget["frame"].destroy()
        self.condition_widgets = []

        # Add condition rows from rule - convert internal values to display values
        for item in conditions.get("items", []):
            self.add_condition_row()
            widget = self.condition_widgets[-1]

            # Set type with display value
            item_type = item.get("type", "piston")
            widget["type"].set(CONDITION_TYPE_DISPLAY.get(item_type, item_type))

            # Need to update sources first
            self.dialog.update_idletasks()

            # Set source with translated display value
            source = item.get("source", "")
            widget["source"].set(t(source) if source else "")

            # Set operator with display value
            item_op = item.get("operator", "equals")
            widget["operator"].set(OPERATOR_DISPLAY.get(item_op, item_op))

            # Set value with translated display value
            item_val = str(item.get("value", ""))
            item_type = CONDITION_TYPE_REVERSE.get(widget["type"].get(), "")
            if item_type == "sensor":
                # Map legacy "down"/"true" to "active", "up"/"false" to "not_active"
                if item_val in ("down", "true", "active"):
                    widget["value"].set(t("active"))
                elif item_val in ("up", "false", "not_active"):
                    widget["value"].set(t("not_active"))
                else:
                    widget["value"].set(item_val)
            elif item_val in ("up", "down", "true", "false"):
                widget["value"].set(t(item_val))
            else:
                widget["value"].set(item_val)

        # Blocked operations
        # Clear existing operation rows
        for widget in self.blocked_op_widgets:
            widget["frame"].destroy()
        self.blocked_op_widgets = []

        # Add operation rows from rule - convert to display values
        for op in rule.get("blocked_operations", []):
            self.add_blocked_operation_row()
            widget = self.blocked_op_widgets[-1]

            # Set operation with display value
            op_name = op.get("operation", "move_y")
            widget["operation"].set(OPERATION_DISPLAY.get(op_name, op_name))
            widget["exclude_setup"].set(op.get("exclude_setup", False))

            # Set direction with translated display value
            direction = op.get("direction", "")
            widget["direction"].set(t(direction) if direction else "")

            # Set selected tools
            tools = op.get("tools", [])
            for tool, var in widget["tool_vars"].items():
                var.set(tool in tools)

        self.message_text.delete(1.0, tk.END)
        self.message_text.insert(1.0, rule.get("message", ""))

    def _reverse_source(self, display_name, source_type):
        """Convert translated source name back to internal name"""
        source_key = {"piston": "pistons", "sensor": "sensors", "position": "positions"}.get(source_type, source_type)
        sources = self.available_sources.get(source_key, [])
        for s in sources:
            if t(s) == display_name:
                return s
        return display_name

    def _reverse_direction(self, display_name):
        """Convert translated direction name back to internal name"""
        for dirs in self.available_directions.values():
            for d in dirs.keys():
                if t(d) == display_name:
                    return d
        return display_name

    def save(self):
        """Save the rule"""
        # Validate
        rule_id = self.id_entry.get().strip()
        if not rule_id:
            messagebox.showerror(t("Error"), t("Rule ID is required"))
            return

        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror(t("Error"), t("Rule name is required"))
            return

        # Build conditions - convert display values back to internal
        conditions = {
            "operator": self.cond_operator_var.get(),
            "items": []
        }

        for widget in self.condition_widgets:
            if not widget["frame"].winfo_exists():
                continue

            # Reverse-map display values to internal values
            cond_type_display = widget["type"].get()
            cond_type = CONDITION_TYPE_REVERSE.get(cond_type_display, cond_type_display)

            source_display = widget["source"].get()
            source = self._reverse_source(source_display, cond_type)

            op_display = widget["operator"].get()
            operator = OPERATOR_REVERSE.get(op_display, op_display)

            value_display = widget["value"].get()
            value = VALUE_REVERSE.get(value_display, value_display)

            cond = {
                "type": cond_type,
                "source": source,
                "operator": operator,
                "value": value
            }

            # Convert numeric values for position type
            if cond_type == "position":
                try:
                    cond["value"] = float(cond["value"])
                except ValueError:
                    pass

            if cond["source"]:  # Only add if source is set
                conditions["items"].append(cond)

        # Build blocked operations with tools - convert display values back
        blocked_ops = []
        for widget in self.blocked_op_widgets:
            if not widget["frame"].winfo_exists():
                continue

            op_display = widget["operation"].get()
            op_name = OPERATION_REVERSE.get(op_display, op_display)
            op_data = {"operation": op_name}

            if op_name == "tool_action":
                # Get selected tools (keys are already internal names)
                selected_tools = [tool for tool, var in widget["tool_vars"].items() if var.get()]
                if selected_tools:
                    op_data["tools"] = selected_tools
            else:
                op_data["exclude_setup"] = widget["exclude_setup"].get()

            # Include direction if set - reverse translate
            direction_display = widget["direction"].get()
            if direction_display:
                op_data["direction"] = self._reverse_direction(direction_display)

            blocked_ops.append(op_data)

        # Reverse-map severity display value to internal
        severity_display = self.severity_var.get()
        severity = SEVERITY_REVERSE.get(severity_display, severity_display)

        # Reverse-map reason display value to internal
        reason_display = self.reason_var.get()
        reason = REASON_REVERSE.get(reason_display, reason_display)

        # Build monitor settings
        monitor = None
        if self.monitor_enabled_var.get() or self.monitor_lines_var.get() or self.monitor_rows_var.get():
            # Build recovery conditions
            recovery_conditions = {
                "operator": self.recovery_cond_operator_var.get(),
                "items": []
            }
            for widget in self.recovery_condition_widgets:
                if not widget["frame"].winfo_exists():
                    continue
                cond_type_display = widget["type"].get()
                cond_type = CONDITION_TYPE_REVERSE.get(cond_type_display, cond_type_display)
                source_display = widget["source"].get()
                source = self._reverse_source(source_display, cond_type)
                op_display = widget["operator"].get()
                operator = OPERATOR_REVERSE.get(op_display, op_display)
                value_display = widget["value"].get()
                value = VALUE_REVERSE.get(value_display, value_display)
                cond = {
                    "type": cond_type,
                    "source": source,
                    "operator": operator,
                    "value": value
                }
                if cond_type == "position":
                    try:
                        cond["value"] = float(cond["value"])
                    except ValueError:
                        pass
                if cond["source"]:
                    recovery_conditions["items"].append(cond)

            operation_context = []
            if self.monitor_lines_var.get():
                operation_context.append("lines")
            if self.monitor_rows_var.get():
                operation_context.append("rows")

            action_display = self.monitor_action_var.get()
            action_internal = ACTION_REVERSE.get(action_display, action_display)
            recovery_action_display = self.monitor_recovery_action_var.get()
            recovery_action_internal = RECOVERY_ACTION_REVERSE.get(recovery_action_display, recovery_action_display)

            monitor = {
                "enabled": self.monitor_enabled_var.get(),
                "operation_context": operation_context,
                "action": action_internal,
                "recovery_conditions": recovery_conditions,
                "recovery_action": recovery_action_internal
            }

        # Create result
        self.result = {
            "id": rule_id,
            "name": name,
            "description": self.desc_text.get(1.0, tk.END).strip(),
            "enabled": self.enabled_var.get(),
            "priority": int(self.priority_entry.get() or 50),
            "severity": severity,
            "reason": reason,
            "is_system_rule": self.rule.get("is_system_rule", False) if self.rule else False,
            "conditions": conditions,
            "blocked_operations": blocked_ops,
            "message": self.message_text.get(1.0, tk.END).strip(),
            "created_at": self.rule.get("created_at", datetime.now().isoformat()) if self.rule else datetime.now().isoformat(),
            "created_by": self.rule.get("created_by", "admin") if self.rule else "admin"
        }

        # Add monitor if configured
        if monitor:
            self.result["monitor"] = monitor

        # Preserve existing monitor if not edited (for rules that already have it)
        if not monitor and self.rule and "monitor" in self.rule:
            self.result["monitor"] = self.rule["monitor"]

        self.dialog.destroy()
