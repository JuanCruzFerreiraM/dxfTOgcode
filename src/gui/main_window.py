from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QStackedWidget, QHBoxLayout, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from src.gui.ifc_page import IFCPage
from src.gui.gcode_preview import Preview
from src.gui.resource_paths import gui_icon_path


class MainWindow(QMainWindow):
    """Main application window (IFC workflow and G-code preview)."""

    def __init__(self):
        """Initialize main window with IFC page and preview stack."""
        super().__init__()

        self.setWindowTitle("Generador G-code")
        self.setWindowIcon(QIcon(gui_icon_path("gcodegerator.ico")))
        self.setMinimumSize(800, 600)
        self.resize(1200, 800)

        self.stack = QStackedWidget()
        self.preview_page = Preview(parent_stack=self.stack, previous_index=0)
        self.stack.addWidget(IFCPage(self.stack, self.preview_page))
        self.stack.addWidget(self.preview_page)

        from PyQt6.QtWidgets import QFrame

        self.divider = QFrame()
        self.divider.setFrameShape(QFrame.Shape.HLine)
        self.divider.setFrameShadow(QFrame.Shadow.Sunken)
        self.divider.setLineWidth(2)
        self.divider.setStyleSheet("color: #2C3E50")

        content_wrapper = QWidget()
        content_layout = QVBoxLayout(content_wrapper)
        content_layout.setContentsMargins(10, 0, 0, 0)
        content_layout.setSpacing(0)
        content_layout.addSpacerItem(QSpacerItem(0, 8, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))
        content_layout.addWidget(self.divider)
        content_layout.addWidget(self.stack)
        content_wrapper.setMaximumWidth(1200)

        content_center = QWidget()
        center_layout = QHBoxLayout(content_center)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        center_layout.addWidget(content_wrapper)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 10)
        layout.setSpacing(0)

        layout.addWidget(content_center)

        self.setCentralWidget(container)

        self.setStyleSheet("""
            QMainWindow {
                background-color: #F5F7FA;
            }
        """)
