from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QDoubleSpinBox, QFileDialog, QMessageBox, QScrollArea, QProgressDialog
)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from src.core.app import ifc_script
from src.core.dxf.dxf_parser import FileError, UnsupportedEntityError
from src.core.machine_handler import LayerTimeError  # ✅ Agregar
import traceback


# SpinBox personalizado que ignora la rueda del mouse
class NoWheelDoubleSpinBox(QDoubleSpinBox):
    def wheelEvent(self, event):
        # Ignorar completamente el evento de la rueda
        event.ignore()


# Worker en un hilo separado para ejecutar ifc_script sin bloquear la UI
class IFCWorker(QThread):
    finished = pyqtSignal(object, object)  # resultado, error

    def __init__(self, params):
        super().__init__()
        self.params = params

    def run(self):
        try:
            gcode = ifc_script(**self.params)
            self.finished.emit(gcode, None)
        except Exception as e:
            self.finished.emit(None, e)


class IFCPage(QWidget):
    def __init__(self, parent_stack, parent_preview):
        super().__init__()
        self.parent_stack = parent_stack
        self.parent_preview = parent_preview

        # Scroll principal
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background: #F5F7FA;
            }
            QScrollBar:vertical {
                border: none;
                background: #F5F7FA;
                width: 12px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:vertical {
                background: #D0D6DE;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #3584E4;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
        """)

        container = QWidget()
        layout = QVBoxLayout(container)

        # Formulario selección de archivo
        form_layout = QHBoxLayout()
        form_label = QLabel('Seleccione el archivo IFC que quiere transformar')
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

        # Parámetros - usando NoWheelDoubleSpinBox
        self.layerThickness = self._add_spinbox(layout, "Espesor de capa", 0.01, 100, 20, 0.01, " mm")
        self.feedRate = self._add_spinbox(layout, "Velocidad de impresión (F)", 1, 10000, 2500, 1, " mm/min")
        self.feedRateG0 = self._add_spinbox(layout, "Velocidad de desplazamiento (G0)", 1, 10000, 3000, 1, " mm/min")
        self.extrusion = self._add_spinbox(layout, "Cantidad de extrusión", 0, 10, 0.05, 0.01, " mm")
        self.offsetFill = self._add_spinbox(layout, "Offset de relleno", 0.001, 10, 0.03, 0.001, " m")
        self.stepFill = self._add_spinbox(layout, "Paso de relleno", 0.01, 10, 0.1, 0.01, " m")

        v_angle_label = QLabel('Ángulo de relleno vertical')
        v_angle_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(v_angle_label)

        # Usar la clase personalizada sin rueda
        self.v_angle = NoWheelDoubleSpinBox()
        self.v_angle.setMinimum(0)
        self.v_angle.setMaximum(80)
        self.v_angle.setSingleStep(1)
        self.v_angle.setValue(0)
        self.v_angle.setSuffix(' deg')
        layout.addWidget(self.v_angle)

        self.v_angle_msg = QLabel(
            "⚠️ Si el ángulo es distinto de cero, el paso de relleno (step) será ignorado."
        )
        self.v_angle_msg.setStyleSheet("color: #C0392B; font-size: 12px;")
        self.v_angle_msg.setVisible(False)
        layout.addWidget(self.v_angle_msg)

        def show_v_angle_msg(val):
            self.v_angle_msg.setVisible(val != 0)
        self.v_angle.valueChanged.connect(show_v_angle_msg)

        # En el __init__, agregar después de v_angle:
        self.t_min = self._add_spinbox(layout, "Tiempo mínimo por capa", 0, 60, 0, 0.1, " min")
        self.t_max = self._add_spinbox(layout, "Tiempo máximo por capa", 0.1, 10000, 10000, 0.1, " min")

        # Mensaje informativo
        time_info = QLabel("⚠️ Si una capa excede el tiempo máximo, se detendrá la generación.")
        time_info.setStyleSheet("color: #C0392B; font-size: 12px;")
        layout.addWidget(time_info)

        # Botón generar
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
            QPushButton:hover { background-color: #2C3E50; }
            QPushButton:pressed { background-color: #1A1A1A; }
        """)
        layout.addWidget(generate)

        scroll.setWidget(container)
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(scroll)

        self.setStyleSheet("""
              QWidget {
                  background-color: #F5F7FA;
                  color: #2C3E50;
              }  
              QLabel {
                  font-size: 18px;
                  font-weight: 500;
              }
              QLineEdit, QSpinBox, QDoubleSpinBox {
                  border: none;
                  border-bottom: 2px solid #D0D6DE;
                  padding-top: 5px;
                  padding-bottom: 5px; 
                  outline: none;
              }
              QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
                  border-bottom: 2px solid #3584E4;
              }
              QSpinBox::up-button, QSpinBox::down-button,
              QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
                  width: 0;
                  height: 0;
                  border: none;
              }
        """)

    def _add_spinbox(self, layout, label, minv, maxv, default, step, suffix):
        layout.addWidget(QLabel(label))
        # Usar la clase personalizada sin rueda
        box = NoWheelDoubleSpinBox()
        box.setMinimum(minv)
        box.setMaximum(maxv)
        box.setSingleStep(step)
        box.setValue(default)
        box.setSuffix(suffix)
        layout.addWidget(box)
        return box

    def open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Seleccionar archivo IFC", "", "Archivos IFC (*.ifc);;Todos los archivos (*)")
        if file_path:
            self.form_input.setText(file_path)

    def generate_gcode(self):
        params = dict(
            path=self.form_input.text(),
            e=self.extrusion.value(),
            layer_tick=self.layerThickness.value(),
            feed_rate=self.feedRate.value(),
            feed_rate_g0=self.feedRateG0.value(),
            offset=self.offsetFill.value(),
            step=self.stepFill.value(),
            v_angle=self.v_angle.value(),
            t_min=self.t_min.value(),          # ✅ Agregar
            t_max=self.t_max.value()           # ✅ Agregar
        )

        # Progress dialog estilo custom
        self.progress = QProgressDialog("Generando G-code...\nEste proceso puede tardar varios minutos.", None, 0, 0, self)
        self.progress.setWindowTitle("Procesando")
        self.progress.setWindowModality(Qt.WindowModality.NonModal)  # Permite minimizar
        self.progress.setMinimumDuration(0)
        self.progress.setCancelButton(None)
        self.progress.setStyleSheet("""
            QProgressDialog {
                background-color: #F5F7FA;
                border: 2px solid #D0D6DE;
                border-radius: 12px;
            }
            QLabel {
                font-size: 16px;
                font-weight: 500;
                color: #2C3E50;
            }
        """)
        self.progress.show()

        # Worker en segundo plano
        self.worker = IFCWorker(params)
        self.worker.finished.connect(self.on_gcode_finished)
        self.worker.start()

        # Timer de 15 minutos (900000 ms)
        self.timeout_timer = QTimer(self)
        self.timeout_timer.setSingleShot(True)
        self.timeout_timer.timeout.connect(self.on_timeout)
        self.timeout_timer.start(900000)

    def on_gcode_finished(self, gcode, error):
        self.timeout_timer.stop()
        self.progress.close()

        if error:
            if isinstance(error, LayerTimeError):
                # Mensaje específico para error de tiempo de capa
                QMessageBox.warning(
                    self, 
                    "Tiempo de capa excedido", 
                    f"⚠️ Error en la capa {error.layer_number}:\n\n"
                    f"Tiempo calculado: {error.layer_time:.2f} minutos\n"
                    f"Límite máximo: {error.t_max:.2f} minutos\n\n"
                    f"Sugerencias:\n"
                    f"• Reducir la velocidad de impresión\n"
                    f"• Aumentar el límite de tiempo máximo\n"
                    f"• Revisar la geometría de esta capa"
                )
            elif isinstance(error, (FileError, UnsupportedEntityError, RuntimeError)):
                QMessageBox.critical(self, "Error", str(error))
            else:
                QMessageBox.critical(self, "Error inesperado", f"Se produjo un error inesperado:\n{str(error)}")
            return

        self.parent_preview.setGcode(gcode)
        self.parent_stack.setCurrentIndex(2)

    def on_timeout(self):
        if self.worker.isRunning():
            self.worker.terminate()
            self.progress.close()
            QMessageBox.warning(self, "Tiempo excedido", "El proceso demoró demasiado tiempo y fue cancelado automáticamente.")
