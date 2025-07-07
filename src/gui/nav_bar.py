from PyQt6.QtWidgets import QWidget, QPushButton, QHBoxLayout
from PyQt6.QtCore import Qt

class NavigationBar(QWidget):
    def __init__(self, on_page_change, parent=None):
        super().__init__(parent)

        self.setFixedHeight(40)
        self.setStyleSheet("background-color: #EAF2FD;")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.btn_dxf = QPushButton("DXF")
        self.btn_stl = QPushButton("STL")

        for btn in [self.btn_dxf, self.btn_stl]:
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    font-size: 17px;
                    border: none;
                    color: #2C3E50;
                    padding: 10px 20px;
                }
                QPushButton:hover {
                    background-color: #DDEEFF;
                }
                QPushButton:checked {
                    background-color: #3584E4;
                    color: white;
                }
            """)
            btn.setCheckable(True)

        self.btn_dxf.setChecked(True)  # Vista inicial

        # Conexiones
        self.btn_dxf.clicked.connect(lambda: self.switch_mode(0, on_page_change))
        self.btn_stl.clicked.connect(lambda: self.switch_mode(1, on_page_change))

        layout.addWidget(self.btn_dxf)
        layout.addWidget(self.btn_stl)
        layout.addStretch()

    def switch_mode(self, index, callback):
        self.btn_dxf.setChecked(index == 0)
        self.btn_stl.setChecked(index == 1)
        callback(index)
