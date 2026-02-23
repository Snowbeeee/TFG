from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit
from PyQt6.QtCore import Qt, pyqtSignal


class EditableLabel(QWidget):
    """Label que al hacer doble clic se convierte en un QLineEdit para editar."""
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

    def mouseDoubleClickEvent(self, event):
        self.line_edit.setText(self.label.text())
        self.label.hide()
        self.line_edit.show()
        self.line_edit.setFocus()
        self.line_edit.selectAll()

    def _confirmar(self):
        if self.line_edit.isHidden():
            return
        nuevo = self.line_edit.text().strip()
        if nuevo:
            self.label.setText(nuevo)
        self.line_edit.hide()
        self.label.show()
        self.texto_cambiado.emit(self.label.text())
