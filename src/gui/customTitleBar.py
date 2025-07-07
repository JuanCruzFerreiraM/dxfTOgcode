from PyQt6.QtWidgets import QWidget, QLabel, QPushButton, QHBoxLayout
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, QSize

class CustomTitleBar(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.mouse_pos = None

        self.setFixedHeight(40)
        self.setStyleSheet("background-color: #F5F7FA;")

        title = QLabel("Generador G-code")
        title.setStyleSheet("font-weight: bold; font-size: 16px; padding-left: 10px;")

        # Botón cerrar
        btn_close = QPushButton()
        btn_close.setIcon(QIcon("src/gui/icons/xmark-solid.svg"))
        btn_close.setIconSize(QSize(16, 16))
        btn_close.clicked.connect(self.parent.close)
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #E74C3C;
                border: none;
                border-radius: 15px;
            }
            QPushButton:hover {
                background-color: rgba(231, 76, 60, 0.15);
            }
            QPushButton:pressed {
                background-color: rgba(231, 76, 60, 0.3);
            }
        """)

        # Botón restaurar/maximizar
        self.btn_resize = QPushButton()
        self.btn_resize.setIcon(QIcon("src/gui/icons/window-maximize-regular.svg"))
        self.btn_resize.setIconSize(QSize(16, 16))
        self.btn_resize.clicked.connect(self.toggle_max_restore)
        self.btn_resize.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #2ECC71;
                border: none;
                border-radius: 15px;

            }
            QPushButton:hover {
                background-color: rgba(46, 204, 113, 0.15);
            }
            QPushButton:pressed {
                background-color: rgba(46, 204, 113, 0.3);
            }
        """)

        # Botón minimizar
        btn_minimize = QPushButton()
        btn_minimize.setObjectName("MinimizeButton")
        btn_minimize.setIcon(QIcon("src/gui/icons/window-minimize-solid.svg"))
        btn_minimize.setIconSize(QSize(16, 16))
        btn_minimize.clicked.connect(lambda: self.parent.showMinimized())
        btn_minimize.setStyleSheet("""
            QPushButton#MinimizeButton {
                background-color: transparent;
                color: #F1C40F;
                border: none;
                border-radius: 15px;
            }
            QPushButton#MinimizeButton:hover {
                background-color: rgba(241, 196, 15, 0.15);
            }
            QPushButton#MinimizeButton:pressed {
                background-color: rgba(241, 196, 15, 0.3);
            }
        """)

        # Layout
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 10, 0)
        layout.setSpacing(0)
        layout.addWidget(title)
        layout.addStretch()
        layout.addWidget(btn_minimize)
        layout.addWidget(self.btn_resize)
        layout.addWidget(btn_close)
        self.setLayout(layout)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.mouse_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self.mouse_pos is not None:
            delta = event.globalPosition().toPoint() - self.mouse_pos
            self.parent.move(self.parent.pos() + delta)
            self.mouse_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self.mouse_pos = None

    def toggle_max_restore(self):
        if self.parent.isMaximized():
            self.parent.showNormal()
            self.btn_resize.setIcon(QIcon("src/gui/icons/window-maximize-regular.svg"))
        else:
            self.parent.showMaximized()
            self.btn_resize.setIcon(QIcon("src/gui/icons/window-restore-regular.svg"))
