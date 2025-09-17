from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QStackedWidget, QHBoxLayout, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QCursor
from src.gui.customTitleBar import CustomTitleBar
from src.gui.nav_bar import NavigationBar
from src.gui.dxf_page import DXFPage
from gui.ifc_page import IFCPage
from src.gui.gcode_preview import Preview


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setMinimumSize(800, 600)
        self.actIndex = 0
        
        # Variables para redimensionado
        self.setMouseTracking(True)
        self.resizing = False
        self.resize_direction = None
        self.resize_margin = 8  # Margen para detectar bordes
        self.dragging = False

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

        # === Composición total (barra de título + contenido) ===
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 10)
        layout.setSpacing(0)

        # Título queda fijo arriba
        self.title_bar = CustomTitleBar(self)
        layout.addWidget(self.title_bar)

        # Contenido de la app debajo
        layout.addWidget(content_center)

        self.setCentralWidget(container)

    def switch_page(self, index: int):
        self.stack.setCurrentIndex(index)
        self.actIndex = index

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Verificar si es un área de redimensionado
            self.resize_direction = self.get_resize_direction(event.position().toPoint())
            
            if self.resize_direction:
                # Modo redimensionado
                self.resizing = True
                self.resize_start_pos = event.globalPosition().toPoint()
                self.resize_start_geometry = self.geometry()
                event.accept()
                return
            
            # Si no es redimensionado, verificar si es área de título para arrastrar
            if self.is_in_title_area(event.position().toPoint()):
                self.dragging = True
                self.drag_start_pos = event.globalPosition().toPoint()
                self.window_start_pos = self.pos()
                event.accept()
                return
                
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.resizing and self.resize_direction:
            # Redimensionar ventana
            self.handle_resize(event.globalPosition().toPoint())
            event.accept()
        elif self.dragging:
            # Mover ventana
            delta = event.globalPosition().toPoint() - self.drag_start_pos
            new_pos = self.window_start_pos + delta
            self.move(new_pos)
            event.accept()
        else:
            # Cambiar cursor según la posición para mostrar funcionalidad de resize
            direction = self.get_resize_direction(event.position().toPoint())
            self.set_cursor_for_direction(direction)
            
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.resizing:
            self.resizing = False
            self.resize_direction = None
        
        if self.dragging:
            self.dragging = False
            
        # Restaurar cursor normal al soltar
        self.setCursor(Qt.CursorShape.ArrowCursor)
        super().mouseReleaseEvent(event)

    def is_in_title_area(self, pos):
        """Verifica si el mouse está en el área de la barra de título (excluyendo bordes)"""
        margin = self.resize_margin
        # Área de título: excluyendo los márgenes de resize y los últimos 100px (botones)
        return (margin < pos.x() < self.width() - 100 and 
                margin < pos.y() <= 40)

    def get_resize_direction(self, pos):
        """Determina la dirección de redimensionado basada en la posición del mouse"""
        margin = self.resize_margin
        rect = self.rect()
        
        left = pos.x() <= margin
        right = pos.x() >= rect.width() - margin
        top = pos.y() <= margin
        bottom = pos.y() >= rect.height() - margin
        
        # Combinaciones de esquinas primero
        if top and left:
            return 'top-left'
        elif top and right:
            return 'top-right'
        elif bottom and left:
            return 'bottom-left'
        elif bottom and right:
            return 'bottom-right'
        # Luego bordes individuales
        elif top:
            return 'top'
        elif bottom:
            return 'bottom'
        elif left:
            return 'left'
        elif right:
            return 'right'
        
        return None

    def set_cursor_for_direction(self, direction):
        """Establece el cursor apropiado según la dirección de redimensionado"""
        if direction in ['top', 'bottom']:
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        elif direction in ['left', 'right']:
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif direction in ['top-left', 'bottom-right']:
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif direction in ['top-right', 'bottom-left']:
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def handle_resize(self, global_pos):
        """Maneja el redimensionado de la ventana"""
        if not self.resize_direction:
            return
            
        delta = global_pos - self.resize_start_pos
        new_geometry = QRect(self.resize_start_geometry)
        
        direction = self.resize_direction
        
        # Aplicar cambios según la dirección
        if 'left' in direction:
            new_width = new_geometry.width() - delta.x()
            if new_width >= self.minimumSize().width():
                new_geometry.setLeft(new_geometry.left() + delta.x())
            
        if 'right' in direction:
            new_geometry.setRight(new_geometry.right() + delta.x())
            
        if 'top' in direction:
            new_height = new_geometry.height() - delta.y()
            if new_height >= self.minimumSize().height():
                new_geometry.setTop(new_geometry.top() + delta.y())
            
        if 'bottom' in direction:
            new_geometry.setBottom(new_geometry.bottom() + delta.y())
        
        # Aplicar restricciones de tamaño mínimo
        min_size = self.minimumSize()
        if new_geometry.width() < min_size.width():
            if 'left' in direction:
                new_geometry.setLeft(new_geometry.right() - min_size.width())
            else:
                new_geometry.setWidth(min_size.width())
        
        if new_geometry.height() < min_size.height():
            if 'top' in direction:
                new_geometry.setTop(new_geometry.bottom() - min_size.height())
            else:
                new_geometry.setHeight(min_size.height())
        
        self.setGeometry(new_geometry)

    def leaveEvent(self, event):
        """Restaurar cursor normal cuando el mouse sale de la ventana"""
        self.setCursor(Qt.CursorShape.ArrowCursor)
        super().leaveEvent(event)
