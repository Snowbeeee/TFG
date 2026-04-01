# ── Imports ──────────────────────────────────────────────────────
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout
)
from ui.gameSideBar.gameSideBar import GameSideBar


# Define el layout de la página de juego: sidebar (izquierda) + zona OpenGL (derecha).
# openglContainer es un QWidget placeholder donde GameWindow añadirá el OpenGLWidget real.
class GameWindowUI:

    def __init__(self):
        # --- Declaración de todas las variables de instancia ---
        self.layout = None
        self.widget = None
        self.horizontalLayout = None
        self.gameSideBar = None
        self.openglContainer = None

    # Construye el layout horizontal: sidebar fija + zona de juego expansible
    def setupUi(self, parent):
        # Layout principal vertical (ocupa todo el espacio asignado)
        self.layout = QVBoxLayout(parent)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # Contenedor horizontal: sidebar + zona de juego
        self.widget = QWidget()
        self.widget.setObjectName("gameWidget")
        self.layout.addWidget(self.widget)

        self.horizontalLayout = QHBoxLayout(self.widget)
        self.horizontalLayout.setObjectName("gameHorizontalLayout")
        self.horizontalLayout.setSpacing(0)
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)

        # Sidebar de configuración + botón salir
        self.gameSideBar = GameSideBar()
        self.horizontalLayout.addWidget(self.gameSideBar)

        # Placeholder (se reemplazará por el OpenGLWidget real)
        self.openglContainer = QWidget()
        self.horizontalLayout.addWidget(self.openglContainer, 1)
