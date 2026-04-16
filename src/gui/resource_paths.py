"""Resolve paths to GUI assets for development and PyInstaller (frozen) runs."""

import os
import sys
from pathlib import Path


def gui_icon_path(filename: str) -> str:
    """Return an absolute path to ``filename`` inside ``src/gui/icons``."""
    if getattr(sys, "frozen", False):
        return os.path.join(sys._MEIPASS, "src", "gui", "icons", filename)
    return os.path.normpath(os.path.join(os.path.dirname(__file__), "icons", filename))


def manual_pdf_path() -> str:
    """Absolute path to ``Manual_de_usuario.pdf`` (repo root in dev, bundle root when frozen)."""
    if getattr(sys, "frozen", False):
        return os.path.join(sys._MEIPASS, "Manual_de_usuario.pdf")
    repo_root = Path(__file__).resolve().parent.parent.parent
    return str(repo_root / "Manual_de_usuario.pdf")
