from PyQt6.QtWidgets import QFrame, QHBoxLayout, QPushButton
from PyQt6.QtCore import Qt


class HeaderUI:
    """UI de la barra de navegación (cabecera)."""

    def __init__(self):
        # --- Declaración de todas las variables de instancia ---
        self.linkBiblioteca = None
        self.linkConfiguracion = None

    def setupUi(self, parent):
        parent.setObjectName("headerBar")
        parent.setFixedHeight(50)

        headerLayout = QHBoxLayout(parent)
        headerLayout.setContentsMargins(20, 0, 20, 0)
        headerLayout.setSpacing(30)

        self.linkBiblioteca = QPushButton("Biblioteca")
        self.linkBiblioteca.setObjectName("navLink")
        self.linkBiblioteca.setCursor(Qt.CursorShape.PointingHandCursor)
        self.linkBiblioteca.setProperty("active", True)
        headerLayout.addWidget(self.linkBiblioteca)

        self.linkConfiguracion = QPushButton("Configuración")
        self.linkConfiguracion.setObjectName("navLink")
        self.linkConfiguracion.setCursor(Qt.CursorShape.PointingHandCursor)
        self.linkConfiguracion.setProperty("active", False)
        headerLayout.addWidget(self.linkConfiguracion)

        headerLayout.addStretch()
