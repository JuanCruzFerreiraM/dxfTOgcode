from PyQt6.QtWidgets import QPushButton, QWidget, QHBoxLayout, QPlainTextEdit, QMessageBox, QFileDialog, QVBoxLayout
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt


class Preview(QWidget):
    def __init__(self, parent_stack, previous_index):
        super().__init__()
        
        self.gcode_str = None
        self.parent_stack = parent_stack
        self.previous_index = previous_index
        btn_layout  = QHBoxLayout()
        layout = QVBoxLayout()
        
        self.gcode_container = QPlainTextEdit()
        self.gcode_container.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.gcode_container.setStyleSheet("""
            QPlainTextEdit {
                background-color: #ffffff;
                color: #2C3E50;
                font-family: Consolas, 'Courier New', monospace;
                font-size: 13px;
                border: 1px solid #D0D6DE;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.gcode_container)
        
        self.save_as_button = QPushButton(QIcon("src/gui/icons/floppy-disk-solid.svg")," Guardar",self)
        self.save_as_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_as_button.setStyleSheet("""
        QPushButton {
                font-size: 18px;
                font-weight: 500;
                margin-top: 15px;
                padding: 10px;
                border-radius: 10;
                background-color: #3584E4;
                color: #F5F7FA;
            }
            
            QPushButton:hover {
                background-color: #2C3E50;
            }
            
            QPushButton:pressed {
                background-color: #1A1A1A; /* Cambia el color al presionar */
            }
        
        """)
        self.save_as_button.clicked.connect(self.save_gcode)
        
        self.cancel = QPushButton("Cancelar")
        self.cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel.clicked.connect(lambda: self.parent_stack.setCurrentIndex(self.previous_index))
        self.cancel.setStyleSheet("""
            QPushButton {
                font-size: 18px;
                font-weight: 500;
                margin-top: 15px;
                padding: 10px;
                border-radius: 10;
                background-color: #E74C3C;
                color: #F5F7FA;
            }
            
            QPushButton:hover {
                background-color: #C0392B;
            }
            
            QPushButton:pressed {
                background-color: #A93226; /* Cambia el color al presionar */
            }
        """)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.save_as_button)
        btn_layout.addWidget(self.cancel)
        
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
        self.setStyleSheet("""
            QWidget {
                background-color: #F5F7FA;
                color: #2C3E50;
            }
        """)
        
        
    def  save_gcode(self):
        if not hasattr(self, 'gcode_str') or not self.gcode_str:
            QMessageBox.warning(self, "Error", "No hay G-code para guardar.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar G-code",
            filter="Archivos G-code (*.gcode);;Todos los archivos (*)"
        )

        if file_path:
            try:
                with open(file_path, "w") as file:
                    file.write(self.gcode_str)
                QMessageBox.information(self, "Éxito", "Archivo guardado correctamente.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo guardar el archivo:\n{str(e)}")

    def setGcode(self,text: str):
        self.gcode_container.setPlainText(text)
        self.gcode_str = text