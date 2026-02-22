"""
Wayland focus fix for Tkinter on labwc/wlroots compositors.

Tkinter runs via XWayland on Wayland, and labwc doesn't properly handle
X11 focus requests. This module uses wlrctl (native Wayland tool) to
request focus via the wlr-foreign-toplevel-management protocol.

Usage:
    # Call once at startup, before creating any windows:
    from gui.wayland_focus import patch_wayland_focus
    patch_wayland_focus()
"""

import os
import tkinter as tk


def force_focus(window):
    """Request compositor focus for a Tk window on Wayland.

    Uses wlrctl app_id matching. Falls back to Tkinter methods on X11.
    Safe to call on any platform - no-ops gracefully if wlrctl is unavailable.
    """
    window.update_idletasks()

    try:
        import subprocess, shutil
        if shutil.which('wlrctl') and os.environ.get('WAYLAND_DISPLAY'):
            app_id = window.winfo_name()
            window.after(150, lambda: subprocess.Popen(
                ['wlrctl', 'toplevel', 'focus', 'app_id:' + app_id],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            ))
            return
    except Exception:
        pass

    # Fallback for X11
    window.lift()
    window.focus_force()


def patch_wayland_focus():
    """Monkey-patch tk.Toplevel so every new dialog auto-requests focus.

    Call once at startup before creating any windows. On X11 or if wlrctl
    is not installed, this is a no-op (no patching occurs).
    """
    import shutil
    if not (shutil.which('wlrctl') and os.environ.get('WAYLAND_DISPLAY')):
        return

    _OriginalInit = tk.Toplevel.__init__

    def _patched_init(self, *args, **kwargs):
        _OriginalInit(self, *args, **kwargs)
        import subprocess
        app_id = self.winfo_name()
        self.after(150, lambda: subprocess.Popen(
            ['wlrctl', 'toplevel', 'focus', 'app_id:' + app_id],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        ))

    tk.Toplevel.__init__ = _patched_init
