from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QStackedWidget, QHBoxLayout, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from src.gui.nav_bar import NavigationBar
from src.gui.dxf_page import DXFPage
from gui.ifc_page import IFCPage
from src.gui.gcode_preview import Preview


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Configuración básica con funcionalidad nativa
        self.setWindowTitle("Generador G-code")
        self.setWindowIcon(QIcon("src/gui/icons/gcodegerator.ico"))  # Icono de ventana
        self.setMinimumSize(800, 600)
        self.resize(1200, 800)  # Tamaño inicial
        self.actIndex = 0

        # === Contenedor central de la app ===
        self.nav_bar = NavigationBar(self.switch_page)
       
        self.stack = QStackedWidget()
        self.preview_page = Preview(parent_stack=self.stack, previous_index=self.actIndex)
        self.stack.addWidget(DXFPage(self.stack, self.preview_page))
        self.stack.addWidget(IFCPage(self.stack, self.preview_page))
        
        self.stack.addWidget(self.preview_page)
        
        from PyQt6.QtWidgets import QFrame

        self.divider = QFrame()
        self.divider.setFrameShape(QFrame.Shape.HLine)
        self.divider.setFrameShadow(QFrame.Shadow.Sunken)
        self.divider.setLineWidth(2)
        self.divider.setStyleSheet("color: #2C3E50")

        # Contenido visualmente limitado a 1200px y centrado
        content_wrapper = QWidget()
        content_layout = QVBoxLayout(content_wrapper)
        content_layout.setContentsMargins(10, 0, 0, 0)
        content_layout.setSpacing(0)
        content_layout.addWidget(self.nav_bar)
        content_layout.addSpacerItem(QSpacerItem(0, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))
        content_layout.addWidget(self.divider)
        content_layout.addWidget(self.stack)
        content_wrapper.setMaximumWidth(1200)

        content_center = QWidget()
        center_layout = QHBoxLayout(content_center)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        center_layout.addWidget(content_wrapper)

        # === Composición total (sin barra de título personalizada) ===
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 10)
        layout.setSpacing(0)

        # Contenido de la app directamente
        layout.addWidget(content_center)

        self.setCentralWidget(container)

        # Estilo general de la aplicación
        self.setStyleSheet("""
            QMainWindow {
                background-color: #F5F7FA;
            }
        """)

    def switch_page(self, index: int):
        self.stack.setCurrentIndex(index)
        self.actIndex = index
