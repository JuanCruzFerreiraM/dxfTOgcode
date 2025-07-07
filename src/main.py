import sys
from PyQt6.QtWidgets import QApplication
from src.gui.main_window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
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
