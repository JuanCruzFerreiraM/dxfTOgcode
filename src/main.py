import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from src.gui.main_window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Configurar App ID para Windows (importante para la barra de tareas)
    app.setApplicationName("Generador G-code")
    app.setApplicationDisplayName("Generador G-code")
    app.setApplicationVersion("1.0")
    app.setOrganizationName("LEICI")
    
    # Configurar icono de la aplicación con ruta absoluta
    icon_path = os.path.join(os.path.dirname(__file__), "gui", "icons", "gcodegerator.ico")
    app_icon = QIcon(icon_path)
    app.setWindowIcon(app_icon)
    
    # En Windows, también configurar el icono del proceso
    if sys.platform == "win32":
        import ctypes
        # Configurar el AppUserModelID para Windows
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("LEICI.GeneradorGcode.1.0")
    
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
