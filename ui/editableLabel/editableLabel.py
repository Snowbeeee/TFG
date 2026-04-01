# ── Imports ──────────────────────────────────────────────────────
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit
from PyQt6.QtCore import Qt, pyqtSignal


# Widget compuesto: un QLabel que al hacer doble clic se convierte en un QLineEdit.
# Se usa en las cartas de juego para renombrar el título in-place.
# Al confirmar (Enter o perder foco) vuelve a mostrar el QLabel con el nuevo texto.
class EditableLabel(QWidget):
    # Señal emitida con el nuevo texto cuando el usuario confirma la edición
    texto_cambiado = pyqtSignal(str)

    def __init__(self, texto, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.label = QLabel(texto)
        self.label.setObjectName("gameCardTitle")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setWordWrap(True)
        self.label.setMaximumWidth(200)
        layout.addWidget(self.label)

        self.line_edit = QLineEdit(texto)
        self.line_edit.setObjectName("gameCardTitleEdit")
        self.line_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.line_edit.hide()
        layout.addWidget(self.line_edit)

        self.line_edit.returnPressed.connect(self._confirmar)
        self.line_edit.editingFinished.connect(self._confirmar)

    # Consumir clic simple para que no se propague al widget padre (la carta de juego)
    # y evitar que se abra el juego al intentar editar el nombre.
    def mousePressEvent(self, event):
        event.accept()

    # Doble clic: intercambia el QLabel visible por el QLineEdit editable.
    # selectAll() selecciona todo el texto para facilitar la edición.
    def mouseDoubleClickEvent(self, event):
        self.line_edit.setText(self.label.text())
        self.label.hide()
        self.line_edit.show()
        self.line_edit.setFocus()
        self.line_edit.selectAll()

    # Confirma la edición: oculta el QLineEdit y muestra el QLabel actualizado.
    # Se conecta tanto a returnPressed (Enter) como a editingFinished (perder foco).
    def _confirmar(self):
        if self.line_edit.isHidden():
            return
        nuevo = self.line_edit.text().strip()
        if nuevo:
            self.label.setText(nuevo)
        self.line_edit.hide()
        self.label.show()
        self.texto_cambiado.emit(self.label.text())
