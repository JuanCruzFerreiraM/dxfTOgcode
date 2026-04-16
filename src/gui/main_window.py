import os

from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QStackedWidget,
    QHBoxLayout,
    QSpacerItem,
    QSizePolicy,
    QPushButton,
    QMessageBox,
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QIcon, QDesktopServices
from src.gui.ifc_page import IFCPage
from src.gui.gcode_preview import Preview
from src.gui.resource_paths import gui_icon_path, manual_pdf_path


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
        content_layout.addSpacerItem(QSpacerItem(0, 4, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))

        help_row = QHBoxLayout()
        help_row.setContentsMargins(0, 0, 0, 0)
        help_row.addStretch()
        btn_help = QPushButton("Ayuda")
        btn_help.setToolTip("Abrir manual de usuario (PDF)")
        btn_help.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_help.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                font-size: 14px;
                font-weight: 500;
                color: #3584E4;
                border: none;
                padding: 6px 12px;
            }
            QPushButton:hover {
                color: #2C3E50;
                text-decoration: underline;
            }
        """)
        btn_help.clicked.connect(self._open_user_manual)
        help_row.addWidget(btn_help)
        content_layout.addLayout(help_row)

        content_layout.addSpacerItem(QSpacerItem(0, 4, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))
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

    def _open_user_manual(self):
        path = manual_pdf_path()
        if os.path.isfile(path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        else:
            QMessageBox.warning(
                self,
                "Ayuda",
                "No se encontró el manual de usuario (Manual_de_usuario.pdf).",
            )
