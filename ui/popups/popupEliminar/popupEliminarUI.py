from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton
)
from PyQt6.QtCore import Qt


class PopupEliminarUI:
    """UI del popup de confirmación para eliminar una carpeta."""

    def __init__(self):
        # --- Declaración de todas las variables de instancia ---
        self.titleLabel = None
        self.messageLabel = None
        self.btnEliminar = None
        self.btnCancelar = None

    def setupUi(self, parent, nombre_lista):
        parent.setObjectName("popupEliminar")
        parent.setWindowTitle("Eliminar carpeta")
        parent.setFixedWidth(380)

        main_layout = QVBoxLayout(parent)
        main_layout.setContentsMargins(24, 24, 24, 20)
        main_layout.setSpacing(16)

        # Título
        self.titleLabel = QLabel("Eliminar carpeta")
        self.titleLabel.setObjectName("popupTitle")
        main_layout.addWidget(self.titleLabel)

        # Mensaje
        self.messageLabel = QLabel(
            f'¿Estás seguro de que quieres eliminar la carpeta\n"{nombre_lista}"?\n\n'
            "Los juegos que contiene pasarán a Sin Lista."
        )
        self.messageLabel.setObjectName("popupMessage")
        self.messageLabel.setWordWrap(True)
        main_layout.addWidget(self.messageLabel)

        # Fila de botones
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch()

        self.btnCancelar = QPushButton("Cancelar")
        self.btnCancelar.setObjectName("popupBtnSecondary")
        self.btnCancelar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_row.addWidget(self.btnCancelar)

        self.btnEliminar = QPushButton("Eliminar")
        self.btnEliminar.setObjectName("popupBtnDanger")
        self.btnEliminar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btnEliminar.setDefault(True)
        btn_row.addWidget(self.btnEliminar)

        main_layout.addLayout(btn_row)
