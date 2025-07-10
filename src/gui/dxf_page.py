from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
QDoubleSpinBox, QSpinBox, QLineEdit, QPushButton, QFileDialog, QMessageBox)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt
from src.core.app import dxf_script
from core.dxf.dxf_parser import FileError, UnsupportedEntityError

class DXFPage (QWidget):
    def __init__(self, parent_stack, parent_preview):
        super().__init__()
        self.parent_stack = parent_stack
        self.parent_preview = parent_preview
        layout = QVBoxLayout()
        
        # Form para seleccionar un archivo dxf
        form_layout = QHBoxLayout()
        
        form_label = QLabel('Seleccione el archivo dxf que quiere transformar')
        form_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(form_label)
        
        self.form_input = QLineEdit()
        self.form_input.setPlaceholderText('Introduzca la ruta del archivo o seleccione uno')
        self.form_input.textChanged.connect(lambda path: setattr(self, 'path', path))
        form_layout.addWidget(self.form_input)
        
        form_button = QPushButton(QIcon("src/gui/icons/folder-open-regular.svg"), "", self)
        form_button.clicked.connect(self.open_file)
        form_button.setStyleSheet("""
            
            QPushButton:hover {
                background-color: #D6D6D6;
            }
        """)
        form_layout.addWidget(form_button)       
        
        layout.addLayout(form_layout)
        
        # Parámetro de extrusion
        extruction_label = QLabel('Configurar Extrusion (E)')
        extruction_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(extruction_label)
        
        self.extruction = QDoubleSpinBox()
        self.extruction.setMinimum(0)
        self.extruction.setMaximum(1e6)
        self.extruction.setDecimals(3)
        self.extruction.setSingleStep(0.01)
        self.extruction.setValue(0)
        self.extruction.valueChanged.connect(lambda e: setattr(self, 'e', e))
        layout.addWidget(self.extruction)

        # Parámetro de velocidad de movimiento 
        feedRate_label = QLabel('Configurar Velocidad de Movimiento (F)')
        feedRate_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(feedRate_label)
        
        self.feedRate = QDoubleSpinBox()
        self.feedRate.setMinimum(1)
        self.feedRate.setMaximum(1e6)
        self.feedRate.setSingleStep(10)
        self.feedRate.setValue(1)
        self.feedRate.setSuffix(" mm/min")
        self.feedRate.valueChanged.connect(lambda f: setattr(self, 'f', f))
        layout.addWidget(self.feedRate)
        
        # Parámetro de velocidad de movimiento G0
        feedRateG0_label = QLabel('Configurar Velocidad de Movimiento (F) para movimientos sin extrusion')
        feedRateG0_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(feedRateG0_label)
        
        self.feedRateG0 = QDoubleSpinBox()
        self.feedRateG0.setMinimum(1)
        self.feedRateG0.setMaximum(1e6)
        self.feedRateG0.setSingleStep(10)
        self.feedRateG0.setValue(1)
        self.feedRateG0.setSuffix(" mm/min")
        self.feedRateG0.valueChanged.connect(lambda fg0: setattr(self, 'fg0', fg0))
        layout.addWidget(self.feedRateG0)
        
        # Parámetro de altura de capa.
        layerThickness_label = QLabel('Configurar altura de capa')
        layerThickness_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(layerThickness_label)
        
        self.layerThickness = QDoubleSpinBox()
        self.layerThickness.setMinimum(0.1)
        self.layerThickness.setMaximum(1e6)
        self.layerThickness.setSingleStep(1)
        self.layerThickness.setValue(1)
        self.layerThickness.setSuffix(' mm')
        self.layerThickness.valueChanged.connect(lambda lt: setattr(self, 'lt', lt))
        layout.addWidget(self.layerThickness)
        
        # Parámetro de cantidad de capas
        layers_label = QLabel('Indicar la cantidad de capas que se desean')
        layers_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(layers_label)
        
        self.layers = QSpinBox()
        self.layers.setMinimum(1)
        self.layers.setMaximum(int(1e6))
        self.layers.setSingleStep(1)
        self.layers.setValue(1)
        self.layers.valueChanged.connect(lambda l: setattr(self, 'cant_l', l))
        layout.addWidget(self.layers)
        
        # Botón para generar g-code
        generate = QPushButton('Generar G-code')
        generate.clicked.connect(self.generate_gcode)
        generate.setMaximumWidth(400)
        generate.setCursor(Qt.CursorShape.PointingHandCursor)
        generate.setStyleSheet("""
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
        layout.addWidget(generate)
        
        self.setStyleSheet("""
              QWidget {
                  background-color: #F5F7FA;
                  color: #2C3E50;
              }  
              
              QLabel {
                  font-size: 18px;
                  font-weight: 500;
              }
              
              QLineEdit {
                  border: none;
                  border-bottom: 2px solid #D0D6DE;
                  padding-top: 5px;
                  padding-bottom: 5px; 
                  outline: none;
              }
              
              QLineEdit:focus {
                  border-bottom: 2px solid #3584E4;
              }
              
              QSpinBox {
                   border: none;
                  border-bottom: 2px solid #D0D6DE;
                  padding-top: 5px;
                  padding-bottom: 5px; 
                  outline: none;
              }
              
              QSpinBox:focus {
                  border-bottom: 2px solid #3584E4;
              }
              
              QSpinBox::up-button, QSpinBox::down-button {
                  width: 0;
                  height: 0;
                  border: none;
              } 
              
              QDoubleSpinBox {
                   border: none;
                  border-bottom: 2px solid #D0D6DE;
                  padding-top: 5px;
                  padding-bottom: 5px; 
                  outline: none;
              }
              
              QDoubleSpinBox:focus {
                  border-bottom: 2px solid #3584E4;
              }
              
              QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
                  width: 0;
                  height: 0;
                  border: none;
              }
            
        """)

        
        self.setLayout(layout)
        
    def open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Seleccionar archivo DXF", "", "Archivos DXF (*.dxf);;Todos los archivos (*)")
        if file_path:
            self.form_input.setText(file_path)
    
    def generate_gcode(self):
        try: 
            gcode = dxf_script(self.form_input.text(), self.extruction.value(), self.layerThickness.value() ,self.layers.value(), self.feedRate.value(), self.feedRateG0.value())
            self.parent_preview.setGcode(gcode)
            self.parent_stack.setCurrentIndex(2)
        except (FileError, UnsupportedEntityError, RuntimeError) as e:
            QMessageBox.critical(self, "Error", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Error inesperado", f"Se produjo un error inesperado:\n{str(e)}")

