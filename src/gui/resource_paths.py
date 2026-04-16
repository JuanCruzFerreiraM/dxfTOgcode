"""Resolve paths to GUI assets for development and PyInstaller (frozen) runs."""

import os
import sys


def gui_icon_path(filename: str) -> str:
    """Return an absolute path to ``filename`` inside ``src/gui/icons``."""
    if getattr(sys, "frozen", False):
        return os.path.join(sys._MEIPASS, "src", "gui", "icons", filename)
    return os.path.normpath(os.path.join(os.path.dirname(__file__), "icons", filename))
