import tkinter as tk
from tkinter import ttk
from core.translations import t


class BottomPanel:
    """Bottom panel for status and progress information"""
    
    def __init__(self, main_app, parent_frame):
        self.main_app = main_app
        self.parent_frame = parent_frame
        
        self.create_widgets()
    
    def create_widgets(self):
        """Create all widgets for the bottom panel - match original exactly"""
        # Status label (RTL: on right side)
        tk.Label(self.parent_frame, text=t("STATUS:"), font=('Arial', 10, 'bold'),
                bg='lightyellow', fg='darkgreen').pack(side=tk.RIGHT, padx=8)

        # System status summary (RTL: on left side)
        self.system_status_label = tk.Label(self.parent_frame, text=t("System Ready - Load program to begin"),
                                           bg='lightyellow', fg='darkblue', font=('Arial', 9, 'bold'),
                                           anchor='e')
        self.system_status_label.pack(side=tk.LEFT, padx=8)

        # Progress bar (compact version, fills middle)
        progress_frame = tk.Frame(self.parent_frame, bg='lightyellow')
        progress_frame.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=10)

        self.progress = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress.pack(fill=tk.X, pady=8)
        
        # Store references in main app for other components
        self.main_app.progress = self.progress
        self.main_app.system_status_label = self.system_status_label