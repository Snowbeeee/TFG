from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import QTimer, pyqtSignal
from ui.gameWindowUI import GameWindowUI
from ui.openGLWidget import OpenGLWidget


class GameWindow(QWidget):
    """Página de juego: se crea una vez y se reutiliza para cada juego."""

    salir_signal = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = GameWindowUI()
        self.ui.setupUi(self)

        # OpenGLWidget permanente (sin juego cargado aún)
        self.game_widget = OpenGLWidget(self.ui.openglContainer)
        container_layout = QVBoxLayout(self.ui.openglContainer)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addWidget(self.game_widget)

        # Timer permanente (parado)
        self.timer = QTimer()
        self.timer.timeout.connect(self.game_widget.update)

        # Conectar botón salir
        self.ui.pushButtonSalir.clicked.connect(self._salir)

    def load_game(self, juego):
        """Carga un juego en el OpenGLWidget y arranca el timer."""
        self.game_widget.load_game(juego.ruta_core, juego.ruta_juego)
        self.game_widget.setFocus()
        if not self.timer.isActive():
            self.timer.start(16)

    def unload_game(self):
        """Descarga el juego actual y para el timer."""
        self.timer.stop()
        self.game_widget.unload_game()

    def _salir(self):
        """Descarga el juego y emite la señal para volver al menú."""
        self.unload_game()
        self.salir_signal.emit()

    
