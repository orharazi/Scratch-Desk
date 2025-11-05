import tkinter as tk
import re
from core.mock_hardware import get_hardware_status


class CanvasTools:
    """Handles tool status visualization and updates"""
    
    def __init__(self, main_app, canvas_manager):
        self.main_app = main_app
        self.canvas_manager = canvas_manager
        self.canvas_objects = main_app.canvas_objects
    
    def update_tool_status_from_step(self, step_description):
        """Update tool status indicators based on step description with original logic"""
        if not step_description:
            return
            
        step_desc = step_description.lower()
        
        # Parse tool action steps and update canvas indicators
        # Pattern: "Tool action: Open/Close [tool_name]"
        
        # Line marker tool actions
        if 'line marker' in step_desc:
            if 'open line marker' in step_desc:
                # Line marker opening (going down)
                if 'line_marker' in self.canvas_objects:
                    self.main_app.canvas.itemconfig(self.canvas_objects['line_marker'], 
                                                   text="Line Marker: DOWN", fill='red')
                print("🔴 Line Marker: DOWN (marking)")
                
            elif 'close line marker' in step_desc:
                # Line marker closing (going up)
                if 'line_marker' in self.canvas_objects:
                    self.main_app.canvas.itemconfig(self.canvas_objects['line_marker'], 
                                                   text="Line Marker: UP", fill='green')
                print("🟢 Line Marker: UP (raised)")
        
        # Line cutter tool actions
        elif 'line cutter' in step_desc:
            if 'open line cutter' in step_desc:
                # Line cutter opening (going down)
                if 'line_cutter' in self.canvas_objects:
                    self.main_app.canvas.itemconfig(self.canvas_objects['line_cutter'], 
                                                   text="Line Cutter: DOWN", fill='red')
                print("🔴 Line Cutter: DOWN (cutting)")
                
            elif 'close line cutter' in step_desc:
                # Line cutter closing (going up)
                if 'line_cutter' in self.canvas_objects:
                    self.main_app.canvas.itemconfig(self.canvas_objects['line_cutter'], 
                                                   text="Line Cutter: UP", fill='green')
                print("🟢 Line Cutter: UP (raised)")
        
        # Row marker tool actions
        elif 'row marker' in step_desc:
            if 'open row marker' in step_desc:
                # Row marker opening (going down)
                if 'row_marker' in self.canvas_objects:
                    self.main_app.canvas.itemconfig(self.canvas_objects['row_marker'], 
                                                   text="Row Marker: DOWN", fill='red')
                print("🔴 Row Marker: DOWN (marking)")
                
            elif 'close row marker' in step_desc:
                # Row marker closing (going up)
                if 'row_marker' in self.canvas_objects:
                    self.main_app.canvas.itemconfig(self.canvas_objects['row_marker'], 
                                                   text="Row Marker: UP", fill='green')
                print("🟢 Row Marker: UP (raised)")
        
        # Row cutter tool actions
        elif 'row cutter' in step_desc:
            if 'open row cutter' in step_desc:
                # Row cutter opening (going down)
                if 'row_cutter' in self.canvas_objects:
                    self.main_app.canvas.itemconfig(self.canvas_objects['row_cutter'], 
                                                   text="Row Cutter: DOWN", fill='red')
                print("🔴 Row Cutter: DOWN (cutting)")
                
            elif 'close row cutter' in step_desc:
                # Row cutter closing (going up)
                if 'row_cutter' in self.canvas_objects:
                    self.main_app.canvas.itemconfig(self.canvas_objects['row_cutter'], 
                                                   text="Row Cutter: UP", fill='green')
                print("🟢 Row Cutter: UP (raised)")
        
        print(f"Tool status updated from step: {step_description}")
    
    def update_tool_status(self, tool_name, status, color):
        """Update specific tool status indicator"""
        tool_key = f"{tool_name}_status"
        if tool_key in self.canvas_objects:
            self.main_app.canvas.itemconfig(self.canvas_objects[tool_key], fill=color)
            print(f"🔧 {tool_name.upper()} {status.upper()}: {color}")
    
    def ensure_all_tools_up(self):
        """Ensure all tool indicators show UP state during motor movements with original logic"""
        # Set all tool indicators to UP state for safety during movement
        if 'line_marker' in self.canvas_objects:
            self.main_app.canvas.itemconfig(self.canvas_objects['line_marker'], 
                                           text="Line Marker: UP", fill='green')
        
        if 'line_cutter' in self.canvas_objects:
            self.main_app.canvas.itemconfig(self.canvas_objects['line_cutter'], 
                                           text="Line Cutter: UP", fill='green')
        
        if 'row_marker' in self.canvas_objects:
            self.main_app.canvas.itemconfig(self.canvas_objects['row_marker'], 
                                           text="Row Marker: UP", fill='green')
        
        if 'row_cutter' in self.canvas_objects:
            self.main_app.canvas.itemconfig(self.canvas_objects['row_cutter'], 
                                           text="Row Cutter: UP", fill='green')
        
        print("🔧 ALL TOOLS UP: Safety position")
    
    def refresh_tool_status_display(self):
        """Refresh tool status display from hardware status"""
        try:
            status = get_hardware_status()
            
            # Update line marker status
            if hasattr(status, 'line_marker_down') and status.line_marker_down:
                self.update_tool_status("line_marker", "down", "green")
            else:
                self.update_tool_status("line_marker", "up", "gray")
            
            # Update cutter status  
            if hasattr(status, 'cutter_down') and status.cutter_down:
                self.update_tool_status("cutter", "down", "red")
            else:
                self.update_tool_status("cutter", "up", "gray")
                
        except Exception as e:
            print(f"Error refreshing tool status: {e}")
            # Default to safe state
            self.ensure_all_tools_up()