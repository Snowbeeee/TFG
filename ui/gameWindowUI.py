from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton
)


class GameWindowUI:
    """UI de la página de juego: botón salir + placeholder OpenGL."""

    def setupUi(self, parent):
        # Layout principal vertical (ocupa todo el espacio asignado)
        self.layout = QVBoxLayout(parent)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # Contenedor horizontal: botón + zona de juego
        self.widget = QWidget()
        self.widget.setObjectName("gameWidget")
        self.layout.addWidget(self.widget)

        self.horizontalLayout = QHBoxLayout(self.widget)
        self.horizontalLayout.setObjectName("gameHorizontalLayout")
        self.horizontalLayout.setSpacing(30)
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)

        # Botón salir del juego
        self.pushButtonSalir = QPushButton()
        self.pushButtonSalir.setObjectName("pushButtonSalir")
        self.pushButtonSalir.setText("Salir del Juego")
        self.horizontalLayout.addWidget(self.pushButtonSalir, 30)

        # Placeholder (se reemplazará por el OpenGLWidget real)
        self.openGLWidget = QWidget()
        self.openGLWidget.setObjectName("openGLWidget")
        self.horizontalLayout.addWidget(self.openGLWidget, 70)
