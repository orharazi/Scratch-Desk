"""
Wayland focus fix for Tkinter on labwc/wlroots compositors.

Tkinter runs via XWayland on Wayland, and labwc doesn't properly route
input focus to new windows. This module uses wlrctl to request focus
via the wlr-foreign-toplevel-management protocol.

Matching strategy:
- For the root Tk window (only one per app_id): use app_id matching.
- For child Toplevels: use exact title matching (wlrctl v0.2.2 requires
  exact match, including any RTL marks that t_title() prepends).
- app_id matching targets the first window found, so it can't distinguish
  between multiple windows in the same app — title matching is needed.

On X11 (or when wlrctl is unavailable), falls back to lift() + focus_force().

Usage:
    # Call once at startup, before creating any windows:
    from gui.wayland_focus import patch_wayland_focus
    patch_wayland_focus()
"""

import os
import subprocess
import shutil
import tkinter as tk

# Cache wlrctl availability at module load (avoid repeated shutil.which calls)
_HAS_WLRCTL = bool(shutil.which('wlrctl') and os.environ.get('WAYLAND_DISPLAY'))


def _wlrctl_focus_app(app_id):
    """Ask the compositor to focus the window with the given app_id."""
    try:
        subprocess.Popen(
            ['wlrctl', 'toplevel', 'focus', f'app_id:{app_id}'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    except Exception:
        pass


def _wlrctl_focus_title(title):
    """Ask the compositor to focus the window with the exact title.

    wlrctl v0.2.2 uses exact string matching, so the title must include
    any RTL marks (U+200F) that t_title() prepends.
    """
    if not title:
        return
    try:
        subprocess.Popen(
            ['wlrctl', 'toplevel', 'focus', f'title:{title}'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    except Exception:
        pass


def _wlrctl_maximize_app(app_id):
    """Ask the compositor to maximize the window with the given app_id."""
    try:
        subprocess.Popen(
            ['wlrctl', 'toplevel', 'maximize', f'app_id:{app_id}'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    except Exception:
        pass


def force_focus(window, app_id='scratch-desk'):
    """Request compositor focus for a Tk window.

    Uses wlrctl on Wayland — both app_id matching (immediate) and exact
    title matching (delayed, after title is set). Falls back to Tkinter
    methods on X11.

    Binds a <Map> event for reliable timing, plus delayed title-based
    focus as a safety net.
    """
    window.lift()
    window.focus_force()

    if _HAS_WLRCTL:
        def _on_map(event=None):
            _wlrctl_focus_app(app_id)
            try:
                window.unbind('<Map>', _map_id)
            except Exception:
                pass

        _map_id = window.bind('<Map>', _on_map, add='+')

        # Delayed title-based focus — by this time the window title is set
        # (constructors like AdminToolGUI set the title synchronously)
        def _title_focus():
            try:
                if not window.winfo_exists():
                    return
                title = window.title()
                if title:
                    _wlrctl_focus_title(title)
                else:
                    _wlrctl_focus_app(app_id)
            except Exception:
                pass

        window.after(250, _title_focus)


def force_focus_return(parent, app_id='scratch-desk'):
    """Re-focus parent window after a dialog closes.

    Call this right after dialog.destroy(). Uses a 50ms delay so the
    compositor has time to process the window removal before we request
    focus on the parent.
    """
    try:
        parent.lift()
        parent.focus_force()
    except Exception:
        pass

    if _HAS_WLRCTL:
        def _refocus():
            try:
                if not parent.winfo_exists():
                    return
                title = parent.title()
                if title:
                    _wlrctl_focus_title(title)
                else:
                    _wlrctl_focus_app(app_id)
            except Exception:
                pass

        try:
            parent.after(50, _refocus)
        except Exception:
            pass


def maximize_window(window, app_id='scratch-desk'):
    """Maximize a Tk window, using wlrctl on labwc where state('zoomed') is a no-op.

    Tries Tk's built-in maximize methods first, then uses wlrctl as the
    reliable path on labwc/wlroots compositors.
    """
    try:
        window.state('zoomed')
    except tk.TclError:
        try:
            window.attributes('-zoomed', True)
        except tk.TclError:
            pass

    if _HAS_WLRCTL:
        window.after(100, lambda: _wlrctl_maximize_app(app_id))


def patch_wayland_focus(app_id='scratch-desk'):
    """Monkey-patch tk.Toplevel and tkinter.messagebox so every new window
    auto-requests compositor focus, and focus returns to the app after
    messagebox dialogs.

    Call once at startup before creating any windows. Works on both
    Wayland (via wlrctl) and X11 (via lift + focus_force).
    """
    # --- Patch Toplevel.__init__ ---
    _OriginalInit = tk.Toplevel.__init__

    def _patched_init(self, *args, **kwargs):
        _OriginalInit(self, *args, **kwargs)

        def _on_map(event=None):
            """Request focus when compositor maps the window."""
            try:
                if not self.winfo_exists():
                    return
                self.lift()
                self.focus_force()
                if _HAS_WLRCTL:
                    _wlrctl_focus_app(app_id)
            except Exception:
                pass
            try:
                self.unbind('<Map>', _map_id)
            except Exception:
                pass

        _map_id = self.bind('<Map>', _on_map, add='+')

        # Delayed title-based focus — by this time the caller has set the
        # window title (e.g. AdminToolGUI.__init__ runs synchronously after
        # Toplevel creation), so exact title matching can target this window
        # even when multiple windows share the same app_id.
        def _delayed_title_focus():
            try:
                if not self.winfo_exists():
                    return
                self.lift()
                self.focus_force()
                if _HAS_WLRCTL:
                    title = self.title()
                    if title:
                        _wlrctl_focus_title(title)
                    else:
                        _wlrctl_focus_app(app_id)
            except Exception:
                pass

        self.after(250, _delayed_title_focus)

    tk.Toplevel.__init__ = _patched_init

    # --- Patch tkinter.messagebox functions to re-focus after close ---
    if _HAS_WLRCTL:
        import tkinter.messagebox as mb

        def _wrap_messagebox(original_func):
            def wrapper(*args, **kwargs):
                result = original_func(*args, **kwargs)
                _wlrctl_focus_app(app_id)
                return result
            wrapper.__name__ = original_func.__name__
            wrapper.__doc__ = original_func.__doc__
            return wrapper

        for name in ('showinfo', 'showwarning', 'showerror',
                     'askquestion', 'askokcancel', 'askyesno',
                     'askretrycancel', 'askyesnocancel'):
            original = getattr(mb, name, None)
            if original and not getattr(original, '_wayland_patched', False):
                wrapped = _wrap_messagebox(original)
                wrapped._wayland_patched = True
                setattr(mb, name, wrapped)
