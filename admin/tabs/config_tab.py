#!/usr/bin/env python3
"""
System Configuration Tab for Admin Tool
========================================

Provides interface for viewing and editing all system settings:
- Browse settings by category
- Edit values with proper type-specific widgets
- Search settings
- Save/revert changes
- Backup/restore functionality
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, colorchooser
import json
import os
from datetime import datetime
import shutil
from core.translations import t, t_title, rtl


class ConfigTab:
    """System Configuration Management Tab"""

    SETTINGS_FILE = "config/settings.json"
    DESCRIPTIONS_FILE = "config/config_descriptions.json"
    BACKUP_DIR = "config/backups"

    def __init__(self, parent_frame, admin_app):
        self.frame = parent_frame
        self.app = admin_app
        self.settings = {}
        self.descriptions = {}
        self.pending_changes = {}
        self.original_settings = {}

        # Load settings and descriptions
        self.load_settings()
        self.load_descriptions()

        # Create UI
        self.create_ui()

    def load_settings(self):
        """Load settings from JSON file"""
        try:
            if os.path.exists(self.SETTINGS_FILE):
                with open(self.SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    self.settings = json.load(f)
                # Keep a deep copy for change detection
                self.original_settings = json.loads(json.dumps(self.settings))
        except Exception as e:
            self.settings = {}
            print(f"Error loading settings: {e}")

    def load_descriptions(self):
        """Load setting descriptions from JSON file"""
        try:
            if os.path.exists(self.DESCRIPTIONS_FILE):
                with open(self.DESCRIPTIONS_FILE, 'r', encoding='utf-8') as f:
                    self.descriptions = json.load(f)
        except Exception as e:
            self.descriptions = {}
            print(f"Error loading descriptions: {e}")

    def save_settings(self):
        """Save settings to JSON file"""
        try:
            # Create backup first
            self.create_backup("auto_save")

            with open(self.SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)

            self.original_settings = json.loads(json.dumps(self.settings))
            self.pending_changes.clear()
            self.update_status()
            return True
        except Exception as e:
            messagebox.showerror(t("Error"), t("Failed to save settings: {error}", error=str(e)))
            return False

    def create_ui(self):
        """Create the Configuration tab UI"""
        # Configure grid
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(1, weight=1)

        # Top bar with search and actions
        self.create_top_bar()

        # Main content - split pane
        self.create_main_content()

        # Bottom status bar
        self.create_status_bar()

    def create_top_bar(self):
        """Create top control bar with search"""
        top_frame = ttk.Frame(self.frame)
        top_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)

        # Search
        ttk.Label(top_frame, text=t("Search:")).pack(side=tk.RIGHT, padx=(5, 0))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self.on_search)
        search_entry = ttk.Entry(top_frame, textvariable=self.search_var, width=30)
        search_entry.pack(side=tk.RIGHT, padx=5)

        ttk.Button(top_frame, text=t("Clear"), command=self.clear_search).pack(side=tk.RIGHT, padx=2)

        # Spacer
        ttk.Frame(top_frame).pack(side=tk.RIGHT, fill=tk.X, expand=True)

        # Action buttons
        ttk.Button(top_frame, text=t("Save Changes"), command=self.save_changes).pack(side=tk.LEFT, padx=2)
        ttk.Button(top_frame, text=t("Revert"), command=self.revert_changes).pack(side=tk.LEFT, padx=2)
        ttk.Button(top_frame, text=t("Backup"), command=self.create_manual_backup).pack(side=tk.LEFT, padx=2)
        ttk.Button(top_frame, text=t("Restore"), command=self.restore_backup).pack(side=tk.LEFT, padx=2)
        ttk.Button(top_frame, text=t("Refresh"), command=self.refresh_settings).pack(side=tk.LEFT, padx=2)

    def create_main_content(self):
        """Create main split pane content"""
        # Paned window for resizable split
        paned = ttk.PanedWindow(self.frame, orient=tk.HORIZONTAL)
        paned.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        # Right side - settings editor (add FIRST so it's on the left)
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=2)

        self.create_settings_editor(right_frame)

        # Left side - category tree (add SECOND so it's on the right)
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=1)

        self.create_category_tree(left_frame)

    def create_category_tree(self, parent):
        """Create hierarchical category tree"""
        tree_frame = ttk.LabelFrame(parent, text=t("Categories"), padding="5")
        tree_frame.pack(fill=tk.BOTH, expand=True)
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        # Treeview
        self.category_tree = ttk.Treeview(tree_frame, show="tree")
        self.category_tree.grid(row=0, column=0, sticky="nsew")

        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.category_tree.yview)
        self.category_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")

        # Bind selection
        self.category_tree.bind("<<TreeviewSelect>>", self.on_category_selected)

        # Populate tree
        self.populate_category_tree()

    def _get_hebrew_title(self, path, key):
        """Get Hebrew display title for a settings key, falling back to raw key"""
        desc_sections = self.descriptions.get("sections", {})
        parts = path.split(".")

        # Top-level section
        if len(parts) == 1:
            section = desc_sections.get(key, {})
            title = section.get("title_he", section.get("title", key))
            return rtl(title) if title != key else key

        # Subsection (e.g., hardware_config.raspberry_pi)
        if len(parts) == 2:
            section = desc_sections.get(parts[0], {})
            subsections = section.get("subsections", {})
            if key in subsections:
                sub = subsections[key]
                title = sub.get("title_he", sub.get("title", key))
                return rtl(title) if title != key else key

        # Leaf setting - try description_he from descriptions
        desc_info = self.get_description_info(path)
        if desc_info:
            he = desc_info.get("description_he", "")
            if he:
                return rtl(he)

        # Fallback: translate key via translations.py, then raw key
        translated = t(key)
        if translated != key:
            return translated
        return key

    def populate_category_tree(self, filter_text=""):
        """Populate the category tree from settings"""
        # Clear existing
        for item in self.category_tree.get_children():
            self.category_tree.delete(item)

        filter_lower = filter_text.lower()

        def add_items(parent_id, data, path=""):
            """Recursively add items to tree"""
            for key, value in data.items():
                full_path = f"{path}.{key}" if path else key

                # Check if this or any child matches filter
                if filter_lower:
                    if not self.matches_filter(full_path, value, filter_lower):
                        continue

                display_name = self._get_hebrew_title(full_path, key)

                if isinstance(value, dict):
                    # Category node - store real path as tag
                    node_id = self.category_tree.insert(parent_id, "end", text=f"📁 {display_name}",
                                                        open=True, tags=(full_path,))
                    add_items(node_id, value, full_path)
                else:
                    # Leaf node (setting)
                    display_value = str(value)[:30] + "..." if len(str(value)) > 30 else str(value)
                    self.category_tree.insert(parent_id, "end", text=f"📄 {display_name}: {display_value}",
                                              tags=(full_path,))

        add_items("", self.settings)

    def matches_filter(self, path, value, filter_text):
        """Check if path or value matches filter"""
        if filter_text in path.lower():
            return True
        if isinstance(value, dict):
            for k, v in value.items():
                if self.matches_filter(f"{path}.{k}", v, filter_text):
                    return True
        else:
            if filter_text in str(value).lower():
                return True
        return False

    def create_settings_editor(self, parent):
        """Create settings editor panel"""
        editor_frame = ttk.LabelFrame(parent, text=t("Settings Editor"), padding="5")
        editor_frame.pack(fill=tk.BOTH, expand=True)
        editor_frame.rowconfigure(0, weight=1)
        editor_frame.columnconfigure(0, weight=1)

        # Canvas with scrollbar for settings
        canvas = tk.Canvas(editor_frame, bg="white", highlightthickness=0)
        scrollbar_y = ttk.Scrollbar(editor_frame, orient="vertical", command=canvas.yview)
        scrollbar_x = ttk.Scrollbar(editor_frame, orient="horizontal", command=canvas.xview)

        self.settings_frame = ttk.Frame(canvas)

        self.settings_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        self._canvas_window_id = canvas.create_window((0, 0), window=self.settings_frame, anchor="ne")
        canvas.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

        # RTL: vertical scrollbar on left (column=0), canvas on right (column=1)
        scrollbar_y.grid(row=0, column=0, sticky="ns")
        canvas.grid(row=0, column=1, sticky="nsew")
        scrollbar_x.grid(row=1, column=0, columnspan=2, sticky="ew")
        editor_frame.columnconfigure(1, weight=1)

        # RTL: keep the settings frame pinned to the right edge of the canvas
        def _reanchor_rtl(event, c=canvas):
            c.itemconfigure(self._canvas_window_id, width=event.width)
            c.coords(self._canvas_window_id, event.width, 0)

        canvas.bind("<Configure>", _reanchor_rtl)

        # Enable mousewheel scrolling
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", on_mousewheel)

        # Store reference for updates
        self.editor_canvas = canvas
        self.setting_widgets = {}

    def on_category_selected(self, event):
        """Handle category selection"""
        selection = self.category_tree.selection()
        if not selection:
            return

        item = selection[0]
        tags = self.category_tree.item(item, "tags")
        text = self.category_tree.item(item, "text")

        if not tags:
            return

        path = tags[0]

        if text.startswith("📄"):
            # Leaf node selected - show single setting
            self.show_setting_editor(path)
        else:
            # Category selected - show all settings in category
            self.show_category_settings(path)

    def show_setting_editor(self, path):
        """Show editor for a single setting"""
        # Clear existing widgets
        for widget in self.settings_frame.winfo_children():
            widget.destroy()
        self.setting_widgets.clear()

        value = self.get_setting_value(path)
        if value is None:
            return

        # Header
        header_frame = ttk.Frame(self.settings_frame)
        header_frame.grid(row=0, column=0, columnspan=3, sticky="e", pady=10)
        ttk.Label(header_frame, text=t("Setting: {path}", path=path.split(".")[-1]),
                  font=("Arial", 10, "bold")).pack(anchor="e")
        ttk.Label(header_frame, text=path,
                  font=("Courier", 8), foreground="#999").pack(anchor="e")

        self.create_setting_widget(path, value, 1)

    def show_category_settings(self, path):
        """Show all settings in a category"""
        # Clear existing widgets
        for widget in self.settings_frame.winfo_children():
            widget.destroy()
        self.setting_widgets.clear()

        data = self.get_setting_value(path)
        if not isinstance(data, dict):
            return

        # Get section description - prefer Hebrew title
        section_info = self.get_section_info(path)
        section_title = rtl(section_info.get("title_he", section_info.get("title", path))) if section_info else path
        section_desc = rtl(section_info.get("description_he", section_info.get("description", ""))) if section_info else ""

        # Header
        header_frame = ttk.Frame(self.settings_frame)
        header_frame.grid(row=0, column=0, columnspan=3, sticky="e", pady=(10, 2))
        ttk.Label(header_frame, text=section_title,
                  font=("Arial", 12, "bold")).pack(anchor="e")
        # Show settings.json key path in smaller text
        ttk.Label(header_frame, text=path,
                  font=("Courier", 8), foreground="#999").pack(anchor="e")

        if section_desc:
            ttk.Label(self.settings_frame, text=section_desc,
                      foreground="gray", wraplength=500, justify="right").grid(row=1, column=0, columnspan=3, sticky="e", pady=(0, 10))

        ttk.Separator(self.settings_frame, orient="horizontal").grid(row=2, column=0, columnspan=3, sticky="ew", pady=5)

        row = 3
        for key, value in data.items():
            if not isinstance(value, dict):
                full_path = f"{path}.{key}"
                self.create_setting_widget(full_path, value, row)
                row += 1

    def create_setting_widget(self, path, value, row):
        """Create appropriate widget for a setting based on type"""
        # Key label
        key_name = path.split(".")[-1]

        # Get description info for this setting
        desc_info = self.get_description_info(path)
        setting_type = desc_info.get("type", "") if desc_info else ""
        options = desc_info.get("options", []) if desc_info else []
        unit = desc_info.get("unit", "") if desc_info else ""
        min_val = desc_info.get("min") if desc_info else None
        max_val = desc_info.get("max") if desc_info else None
        default_val = desc_info.get("default") if desc_info else None
        # Prefer Hebrew description
        description = ""
        if desc_info:
            description = rtl(desc_info.get("description_he", desc_info.get("description", "")))

        # RTL: Setting name on right (column=2), editor in middle (column=1), description on left (column=0)
        name_frame = ttk.Frame(self.settings_frame)
        name_frame.grid(row=row, column=2, sticky="ne", padx=5, pady=5)

        ttk.Label(name_frame, text=key_name, font=("Arial", 9, "bold")).pack(anchor="e")

        # Settings.json key path in smaller text
        ttk.Label(name_frame, text=path, font=("Courier", 7), foreground="#999").pack(anchor="e")

        # Type badge
        type_display = setting_type or self._infer_type(value)
        if unit:
            type_display += f" ({unit})"
        ttk.Label(name_frame, text=type_display, foreground="blue",
                  font=("Arial", 7)).pack(anchor="e")

        # RTL: Editor in middle column
        editor_frame = ttk.Frame(self.settings_frame)
        editor_frame.grid(row=row, column=1, sticky="e", padx=5, pady=5)

        # Enum type - use dropdown
        if setting_type == "enum" and options:
            var = tk.StringVar(value=str(value))
            widget = ttk.Combobox(editor_frame, textvariable=var, values=[str(o) for o in options],
                                  state="readonly", width=25)
            widget.pack(side=tk.LEFT)
            var.trace_add("write", lambda *args, p=path, v=var: self.on_value_changed(p, v.get()))
            self.setting_widgets[path] = {"type": "enum", "var": var, "widget": widget}

        # Boolean - use checkbox
        elif isinstance(value, bool) or setting_type == "bool":
            var = tk.BooleanVar(value=bool(value))
            widget = ttk.Checkbutton(editor_frame, variable=var, text=t("Enabled") if var.get() else t("Disabled"),
                                     command=lambda p=path, v=var: self._on_bool_changed(p, v))
            widget.pack(side=tk.LEFT)
            self.setting_widgets[path] = {"type": "bool", "var": var, "widget": widget}

        # Integer - use spinbox
        elif isinstance(value, int) or setting_type == "int":
            var = tk.IntVar(value=int(value) if value is not None else 0)
            from_val = int(min_val) if min_val is not None else -999999
            to_val = int(max_val) if max_val is not None else 999999
            widget = ttk.Spinbox(editor_frame, textvariable=var, from_=from_val, to=to_val, width=15)
            widget.pack(side=tk.LEFT)
            var.trace_add("write", lambda *args, p=path, v=var: self.on_value_changed(p, v.get(), value_type="int"))
            self.setting_widgets[path] = {"type": "int", "var": var, "widget": widget}

            # Show range info
            if min_val is not None or max_val is not None:
                range_text = f"[{min_val if min_val is not None else '?'} - {max_val if max_val is not None else '?'}]"
                ttk.Label(editor_frame, text=range_text, foreground="gray",
                          font=("Arial", 8)).pack(side=tk.LEFT, padx=5)

        # Float - use spinbox with increment
        elif isinstance(value, float) or setting_type == "float":
            var = tk.DoubleVar(value=float(value) if value is not None else 0.0)
            from_val = float(min_val) if min_val is not None else -999999.0
            to_val = float(max_val) if max_val is not None else 999999.0
            # Determine increment based on value magnitude
            increment = 0.1 if abs(value) < 10 else 1.0 if abs(value) < 100 else 10.0
            widget = ttk.Spinbox(editor_frame, textvariable=var, from_=from_val, to=to_val,
                                 increment=increment, width=15)
            widget.pack(side=tk.LEFT)
            var.trace_add("write", lambda *args, p=path, v=var: self.on_value_changed(p, v.get(), value_type="float"))
            self.setting_widgets[path] = {"type": "float", "var": var, "widget": widget}

            # Show range info
            if min_val is not None or max_val is not None:
                range_text = f"[{min_val if min_val is not None else '?'} - {max_val if max_val is not None else '?'}]"
                ttk.Label(editor_frame, text=range_text, foreground="gray",
                          font=("Arial", 8)).pack(side=tk.LEFT, padx=5)

        # List/Array - use button to open list editor
        elif isinstance(value, list):
            var = tk.StringVar(value=json.dumps(value))
            preview = str(value)[:40] + "..." if len(str(value)) > 40 else str(value)
            preview_label = ttk.Label(editor_frame, text=preview, width=35, anchor="e")
            preview_label.pack(side=tk.LEFT)
            ttk.Button(editor_frame, text=t("Edit List..."),
                       command=lambda p=path, v=value, pl=preview_label: self.open_list_editor(p, v, pl)).pack(side=tk.LEFT, padx=5)
            self.setting_widgets[path] = {"type": "list", "var": var, "widget": preview_label}

        # Color - use swatch + entry + picker button
        elif setting_type == "color":
            var = tk.StringVar(value=str(value))
            # Color swatch preview
            swatch = tk.Label(editor_frame, text="  ", width=3, relief="solid", borderwidth=1)
            swatch.pack(side=tk.LEFT, padx=(0, 4))
            try:
                swatch.config(bg=str(value))
            except tk.TclError:
                swatch.config(bg="#FFFFFF")
            # Hex entry
            widget = ttk.Entry(editor_frame, textvariable=var, width=12)
            widget.pack(side=tk.LEFT)

            def _update_swatch(*args, s=swatch, v=var):
                try:
                    s.config(bg=v.get())
                except tk.TclError:
                    pass

            var.trace_add("write", _update_swatch)

            def _pick_color(v=var, s=swatch, p=path):
                initial = v.get()
                try:
                    result = colorchooser.askcolor(color=initial, title="Pick Color")
                except Exception:
                    result = colorchooser.askcolor(title="Pick Color")
                if result and result[1]:
                    v.set(result[1])
                    self.on_value_changed(p, result[1])

            ttk.Button(editor_frame, text="Pick...", width=6,
                       command=_pick_color).pack(side=tk.LEFT, padx=4)
            var.trace_add("write", lambda *args, p=path, v=var: self.on_value_changed(p, v.get()))
            self.setting_widgets[path] = {"type": "color", "var": var, "widget": widget}

        # String - use entry
        elif isinstance(value, str) or setting_type == "string":
            var = tk.StringVar(value=str(value))
            # Use larger entry for paths
            width = 50 if "/" in str(value) or "\\" in str(value) else 30
            widget = ttk.Entry(editor_frame, textvariable=var, width=width)
            widget.pack(side=tk.LEFT)
            var.trace_add("write", lambda *args, p=path, v=var: self.on_value_changed(p, v.get()))
            self.setting_widgets[path] = {"type": "string", "var": var, "widget": widget}

        # Fallback - display as readonly text
        else:
            ttk.Label(editor_frame, text=str(value)[:50]).pack(side=tk.LEFT)
            return

        # RTL: Description on left (column=0)
        desc_frame = ttk.Frame(self.settings_frame)
        desc_frame.grid(row=row, column=0, sticky="ne", padx=5, pady=5)

        if description:
            ttk.Label(desc_frame, text=description, foreground="gray",
                      wraplength=300, justify="right", font=("Arial", 8)).pack(anchor="e")

        # Default value info
        if default_val is not None:
            ttk.Label(desc_frame, text=t("Default: {default}", default=default_val), foreground="#888",
                      font=("Arial", 7, "italic")).pack(anchor="e")

    def _infer_type(self, value):
        """Infer type name from value"""
        if isinstance(value, bool):
            return "bool"
        elif isinstance(value, int):
            return "int"
        elif isinstance(value, float):
            return "float"
        elif isinstance(value, str):
            return "string"
        elif isinstance(value, list):
            return "list"
        elif isinstance(value, dict):
            return "object"
        return "unknown"

    def _on_bool_changed(self, path, var):
        """Handle boolean checkbox change"""
        value = var.get()
        # Update checkbox text
        widget_info = self.setting_widgets.get(path)
        if widget_info:
            widget_info["widget"].config(text=t("Enabled") if value else t("Disabled"))
        self.on_value_changed(path, value)

    def open_list_editor(self, path, current_value, preview_label):
        """Open a dialog to edit a list value"""
        dialog = tk.Toplevel(self.frame)
        dialog.title(t_title("Edit List: {key}", key=path.split('.')[-1]))
        dialog.geometry("400x300")
        dialog.transient(self.frame)
        dialog.grab_set()

        ttk.Label(dialog, text=t("Edit list items (one per line):")).pack(pady=5, anchor="e", padx=10)

        # Text area for editing
        text_frame = ttk.Frame(dialog)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        text = tk.Text(text_frame, height=10, width=40)
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)

        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Populate with current values
        for item in current_value:
            text.insert(tk.END, str(item) + "\n")

        def save_list():
            content = text.get("1.0", tk.END).strip()
            lines = [line.strip() for line in content.split("\n") if line.strip()]

            # Try to convert to original types
            new_list = []
            for line in lines:
                # Try int, then float, then keep as string
                try:
                    new_list.append(int(line))
                except ValueError:
                    try:
                        new_list.append(float(line))
                    except ValueError:
                        # Check for boolean
                        if line.lower() == "true":
                            new_list.append(True)
                        elif line.lower() == "false":
                            new_list.append(False)
                        else:
                            new_list.append(line)

            # Update the setting
            self.on_value_changed(path, new_list)

            # Update preview
            preview = str(new_list)[:40] + "..." if len(str(new_list)) > 40 else str(new_list)
            preview_label.config(text=preview)

            # Update stored var
            if path in self.setting_widgets:
                self.setting_widgets[path]["var"].set(json.dumps(new_list))

            dialog.destroy()

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text=t("Save"), command=save_list).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text=t("Cancel"), command=dialog.destroy).pack(side=tk.RIGHT, padx=5)

    def on_value_changed(self, path, new_value, value_type=None):
        """Handle value change"""
        try:
            # Convert value to appropriate type
            if value_type == "int":
                try:
                    new_value = int(new_value) if new_value else 0
                except (ValueError, tk.TclError):
                    return  # Invalid, don't update
            elif value_type == "float":
                try:
                    new_value = float(new_value) if new_value else 0.0
                except (ValueError, tk.TclError):
                    return  # Invalid, don't update

            # Update settings
            self.set_setting_value(path, new_value)

            # Track as pending change
            original = self.get_original_value(path)
            if new_value != original:
                self.pending_changes[path] = new_value
            elif path in self.pending_changes:
                del self.pending_changes[path]

            self.update_status()

        except (ValueError, json.JSONDecodeError) as e:
            # Invalid value - don't update
            pass

    def get_setting_value(self, path):
        """Get setting value by dot-notation path"""
        parts = path.split(".")
        data = self.settings
        for part in parts:
            if isinstance(data, dict) and part in data:
                data = data[part]
            else:
                return None
        return data

    def set_setting_value(self, path, value):
        """Set setting value by dot-notation path"""
        parts = path.split(".")
        data = self.settings
        for part in parts[:-1]:
            if part not in data:
                data[part] = {}
            data = data[part]
        data[parts[-1]] = value

    def get_original_value(self, path):
        """Get original setting value"""
        parts = path.split(".")
        data = self.original_settings
        for part in parts:
            if isinstance(data, dict) and part in data:
                data = data[part]
            else:
                return None
        return data

    def get_section_info(self, path):
        """Get section info from descriptions"""
        desc_sections = self.descriptions.get("sections", {})
        parts = path.split(".")

        if len(parts) >= 1:
            section = desc_sections.get(parts[0], {})
            if len(parts) == 1:
                return section

            # Check for subsections
            subsections = section.get("subsections", {})
            if len(parts) >= 2 and parts[1] in subsections:
                return subsections[parts[1]]

        return None

    def get_description_info(self, path):
        """Get full description info for a setting"""
        desc_sections = self.descriptions.get("sections", {})
        parts = path.split(".")

        if len(parts) < 2:
            return None

        # Get section
        section = desc_sections.get(parts[0], {})

        # Check direct settings in section
        settings = section.get("settings", {})
        setting_key = parts[-1]
        if setting_key in settings:
            return settings[setting_key]

        # Check subsections (e.g., hardware_config.raspberry_pi.pistons)
        subsections = section.get("subsections", {})
        if len(parts) >= 2:
            # Try to find in subsection
            for i in range(1, len(parts) - 1):
                subsection_key = parts[i]
                if subsection_key in subsections:
                    subsection = subsections[subsection_key]
                    sub_settings = subsection.get("settings", {})
                    if setting_key in sub_settings:
                        return sub_settings[setting_key]

        # Direct subsection check (e.g., hardware_config.use_real_hardware)
        if parts[-1] in subsections:
            return subsections[parts[-1]]

        return None

    def on_search(self, *args):
        """Handle search input"""
        filter_text = self.search_var.get()
        self.populate_category_tree(filter_text)

    def clear_search(self):
        """Clear search filter"""
        self.search_var.set("")

    def save_changes(self):
        """Save pending changes"""
        if not self.pending_changes:
            messagebox.showinfo(t("No Changes"), t("There are no pending changes to save."))
            return

        num_changes = len(self.pending_changes)
        if messagebox.askyesno(t("Save Changes"),
                               t("Save {num_changes} pending change(s)?", num_changes=num_changes)):
            if self.save_settings():
                # Refresh the category tree to show updated values on the left side
                self.populate_category_tree(self.search_var.get())
                messagebox.showinfo(t("Success"), t("Settings saved successfully."))
                if hasattr(self.app, 'log'):
                    self.app.log("SUCCESS", t("Saved {num_changes} configuration changes", num_changes=num_changes))

    def revert_changes(self):
        """Revert pending changes"""
        if not self.pending_changes:
            messagebox.showinfo(t("No Changes"), t("There are no pending changes to revert."))
            return

        if messagebox.askyesno(t("Revert Changes"),
                               t("Revert {num_changes} pending change(s)?", num_changes=len(self.pending_changes))):
            self.settings = json.loads(json.dumps(self.original_settings))
            self.pending_changes.clear()
            self.update_status()
            # Refresh the editor
            self.populate_category_tree()
            messagebox.showinfo(t("Success"), t("Changes reverted."))

    def create_backup(self, reason="manual"):
        """Create a backup of current settings"""
        try:
            # Ensure backup directory exists
            os.makedirs(self.BACKUP_DIR, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(self.BACKUP_DIR, f"settings_backup_{timestamp}_{reason}.json")

            shutil.copy2(self.SETTINGS_FILE, backup_file)
            return backup_file
        except Exception as e:
            print(f"Error creating backup: {e}")
            return None

    def create_manual_backup(self):
        """Create manual backup"""
        backup_file = self.create_backup("manual")
        if backup_file:
            messagebox.showinfo(t("Backup Created"), t("Backup saved to:\n{backup_file}", backup_file=backup_file))
        else:
            messagebox.showerror(t("Error"), t("Failed to create backup"))

    def restore_backup(self):
        """Restore from backup"""
        # Ensure backup directory exists
        if not os.path.exists(self.BACKUP_DIR):
            messagebox.showinfo(t("No Backups"), t("No backup files found."))
            return

        # List available backups
        backups = sorted([f for f in os.listdir(self.BACKUP_DIR) if f.endswith('.json')], reverse=True)

        if not backups:
            messagebox.showinfo(t("No Backups"), t("No backup files found."))
            return

        # Create selection dialog
        dialog = tk.Toplevel(self.frame)
        dialog.title(t_title("Restore Backup"))
        dialog.geometry("500x400")
        dialog.transient(self.frame)
        dialog.grab_set()

        ttk.Label(dialog, text=t("Select backup to restore:")).pack(pady=10)

        # Listbox for backups
        listbox = tk.Listbox(dialog, width=60, height=15)
        listbox.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)

        for backup in backups:
            listbox.insert(tk.END, backup)

        def do_restore():
            selection = listbox.curselection()
            if not selection:
                messagebox.showwarning(t("No Selection"), t("Please select a backup file."))
                return

            backup_file = os.path.join(self.BACKUP_DIR, backups[selection[0]])

            if messagebox.askyesno(t("Restore Backup"),
                                   t("Restore settings from:\n{backup}\n\nCurrent settings will be backed up first.", backup=backups[selection[0]])):
                # Backup current before restore
                self.create_backup("pre_restore")

                # Restore
                shutil.copy2(backup_file, self.SETTINGS_FILE)
                self.load_settings()
                self.pending_changes.clear()
                self.populate_category_tree()
                self.update_status()

                dialog.destroy()
                messagebox.showinfo(t("Success"), t("Settings restored successfully."))

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text=t("Restore"), command=do_restore).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text=t("Cancel"), command=dialog.destroy).pack(side=tk.RIGHT, padx=5)

    def refresh_settings(self):
        """Reload settings from file"""
        if self.pending_changes:
            if not messagebox.askyesno(t("Unsaved Changes"),
                                       t("You have unsaved changes. Refresh anyway?")):
                return

        self.refresh_ui()

    def refresh_ui(self):
        """Reload settings from file and refresh UI without prompts"""
        self.load_settings()
        self.pending_changes.clear()
        self.populate_category_tree()
        self.update_status()

    def create_status_bar(self):
        """Create bottom status bar - RTL: status on right, changes on left"""
        status_frame = ttk.Frame(self.frame)
        status_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=5)

        self.status_label = ttk.Label(status_frame, text="")
        self.status_label.pack(side=tk.LEFT)

        self.changes_label = ttk.Label(status_frame, text="")
        self.changes_label.pack(side=tk.RIGHT)

        self.update_status()

    def update_status(self):
        """Update status bar"""
        if self.pending_changes:
            self.changes_label.config(
                text=t("{num_changes} unsaved change(s)", num_changes=len(self.pending_changes)),
                foreground="orange"
            )
        else:
            self.changes_label.config(
                text=t("No unsaved changes"),
                foreground="green"
            )

        self.status_label.config(text=t("Settings file: {file}", file=self.SETTINGS_FILE))
