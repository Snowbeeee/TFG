# ── Imports ──────────────────────────────────────────────────────
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton
)
from PyQt6.QtCore import Qt


# Define el layout del popup para añadir una nueva carpeta.
# Título + campo de texto + botones (Cancelar / Crear).
class PopupAnadirUI:

    def __init__(self):
        # --- Declaración de todas las variables de instancia ---
        self.titleLabel = None
        self.inputField = None
        self.btnAceptar = None
        self.btnCancelar = None

    def setupUi(self, parent):
        parent.setObjectName("popupAnadir")
        parent.setWindowTitle("Nueva carpeta")
        parent.setFixedWidth(360)

        main_layout = QVBoxLayout(parent)
        main_layout.setContentsMargins(24, 24, 24, 20)
        main_layout.setSpacing(16)

        # Título
        self.titleLabel = QLabel("Nueva carpeta")
        self.titleLabel.setObjectName("popupTitle")
        main_layout.addWidget(self.titleLabel)

        # Campo de texto
        self.inputField = QLineEdit()
        self.inputField.setObjectName("popupInputField")
        self.inputField.setPlaceholderText("Nombre de la carpeta…")
        main_layout.addWidget(self.inputField)

        # Fila de botones
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch()

        self.btnCancelar = QPushButton("Cancelar")
        self.btnCancelar.setObjectName("popupBtnSecondary")
        self.btnCancelar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_row.addWidget(self.btnCancelar)

        self.btnAceptar = QPushButton("Crear")
        self.btnAceptar.setObjectName("popupBtnPrimary")
        self.btnAceptar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btnAceptar.setDefault(True)
        btn_row.addWidget(self.btnAceptar)

        main_layout.addLayout(btn_row)
