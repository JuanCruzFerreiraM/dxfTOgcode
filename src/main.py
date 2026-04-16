"""
Main entry point for the G-code Generator application.

This module initializes the PyQt6 application with proper styling,
icon configuration, and platform-specific settings for optimal
user experience across different operating systems.
"""

import sys
import os
import logging
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from src.gui.main_window import MainWindow
from src.gui.resource_paths import gui_icon_path


def _read_app_version():
    """Read semantic version from VERSION.txt next to the bundle or repo root."""
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    path = os.path.join(base, "VERSION.txt")
    try:
        with open(path, encoding="utf-8") as f:
            v = f.read().strip()
            return v if v else "2.0.0"
    except OSError:
        return "2.0.0"


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )
    app = QApplication(sys.argv)
    
    app.setApplicationName("Generador G-code")
    app.setApplicationDisplayName("Generador G-code")
    app_version = _read_app_version()
    app.setApplicationVersion(app_version)
    app.setOrganizationName("LEICI")

    app_icon = QIcon(gui_icon_path("gcodegerator.ico"))
    app.setWindowIcon(app_icon)
    
    if sys.platform == "win32":
        import ctypes

        app_id = f"LEICI.GeneradorGcode.{app_version}"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    
    app.setStyleSheet("""
    QWidget {
        background-color: #F5F7FA;
        color: #2C3E50;
        font-family: 'Segoe UI', sans-serif;
    }

    QLineEdit, QPlainTextEdit, QTextEdit {
        background-color: white;
        border: 1px solid #CCC;
        border-radius: 4px;
        color: #2C3E50;
    }

    QPushButton {
        background-color: #3584E4;
        color: white;
        border-radius: 5px;
        padding: 6px 12px;
    }

    QPushButton:hover {
        background-color: #2a68c9;
    }
    """)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())
