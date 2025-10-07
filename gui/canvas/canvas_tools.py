import tkinter as tk
from mock_hardware import get_hardware_status


class CanvasTools:
    """Handles tool status visualization and updates"""
    
    def __init__(self, main_app):
        self.main_app = main_app
        self.canvas_objects = main_app.canvas_objects
    
    def update_tool_status_from_step(self, step_description):
        """Update tool status indicators based on step execution"""
        if not step_description:
            return
        
        step_desc = step_description.lower()
        
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
    
    def ensure_all_tools_up(self):
        """Ensure all tool indicators show UP state during motor movements"""
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
    
    def refresh_tool_status_display(self):
        """Refresh tool status display from hardware"""
        # Get current hardware status
        status = get_hardware_status()
        
        # Update line marker status
        marker_status = "DOWN" if status['line_marker'] == 'down' else "UP"
        marker_color = "red" if status['line_marker'] == 'down' else "green"
        if 'line_marker' in self.canvas_objects:
            self.main_app.canvas.itemconfig(self.canvas_objects['line_marker'],
                                           text=f"Line Marker: {marker_status}", fill=marker_color)
        
        # Update line marker piston status
        piston_status = "UP" if status['line_marker_piston'] == 'up' else "DOWN"
        piston_color = "blue" if status['line_marker_piston'] == 'up' else "red"
        if 'line_marker_piston' in self.canvas_objects:
            self.main_app.canvas.itemconfig(self.canvas_objects['line_marker_piston'],
                                           text=f"Line Marker State: {piston_status}", fill=piston_color)
        
        # Update line cutter status
        cutter_status = "DOWN" if status['line_cutter'] == 'down' else "UP"
        cutter_color = "red" if status['line_cutter'] == 'down' else "green"
        if 'line_cutter' in self.canvas_objects:
            self.main_app.canvas.itemconfig(self.canvas_objects['line_cutter'],
                                           text=f"Line Cutter: {cutter_status}", fill=cutter_color)
        
        # Update row marker status
        marker_status = "DOWN" if status['row_marker'] == 'down' else "UP"
        marker_color = "red" if status['row_marker'] == 'down' else "green"
        if 'row_marker' in self.canvas_objects:
            self.main_app.canvas.itemconfig(self.canvas_objects['row_marker'],
                                           text=f"Row Marker: {marker_status}", fill=marker_color)
        
        # Update row marker limit switch status
        limit_status = "DOWN" if status['row_marker_limit_switch'] == 'down' else "UP"
        limit_color = "darkred" if status['row_marker_limit_switch'] == 'down' else "darkgreen"
        if 'row_marker_limit_switch' in self.canvas_objects:
            self.main_app.canvas.itemconfig(self.canvas_objects['row_marker_limit_switch'],
                                           text=f"Row Marker State: {limit_status}", fill=limit_color)
        
        # Update row cutter status
        cutter_status = "DOWN" if status['row_cutter'] == 'down' else "UP"
        cutter_color = "red" if status['row_cutter'] == 'down' else "green"
        if 'row_cutter' in self.canvas_objects:
            self.main_app.canvas.itemconfig(self.canvas_objects['row_cutter'],
                                           text=f"Row Cutter: {cutter_status}", fill=cutter_color)