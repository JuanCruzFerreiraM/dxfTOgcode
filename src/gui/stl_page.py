from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt

class STLPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        label = QLabel("En desarrollo")
        label.setStyleSheet("""
            background-color: #F5F7FA;
            font-size: 18px;
            color: #555;
        """)

        layout.addWidget(label)
        self.setLayout(layout)
