from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import QTimer, pyqtSignal
from ui.gameWindowUI import GameWindowUI
from ui.openGLWidget import OpenGLWidget


class GameWindow(QWidget):
    """Página de juego: inicializa el core, renderiza y permite salir."""

    # Señal emitida al pulsar "Salir del Juego" para que MainWindow cambie de página
    salir_signal = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = GameWindowUI()
        self.ui.setupUi(self)

        self.game_widget = None
        self.timer = None

        # Conectar botón salir
        self.ui.pushButtonSalir.clicked.connect(self._salir)

    def start(self):
        """Crea el OpenGLWidget e inicia el juego.
        Llamar DESPUÉS de que este widget ya esté dentro del QStackedWidget,
        para evitar que Qt recree la ventana nativa."""
        if self.game_widget is not None:
            return  # Ya iniciado

        old_widget = self.ui.openGLWidget
        if old_widget:
            layout = old_widget.parent().layout() if old_widget.parent() else None
            self.game_widget = OpenGLWidget(old_widget.parent())

            if layout:
                index = layout.indexOf(old_widget)
                stretch = layout.stretch(index) if hasattr(layout, 'stretch') else 0
                layout.removeWidget(old_widget)
                old_widget.setParent(None)
                old_widget.deleteLater()
                layout.insertWidget(index, self.game_widget, stretch)
            else:
                geometry = old_widget.geometry()
                old_widget.setParent(None)
                old_widget.deleteLater()
                self.game_widget.setGeometry(geometry)

            self.game_widget.setFocus()

            # Timer de renderizado (~60 FPS)
            self.timer = QTimer()
            self.timer.timeout.connect(self.game_widget.update)
            self.timer.start(16)

    def _salir(self):
        """Detiene el core, el audio y emite la señal para volver al menú."""
        if self.timer:
            self.timer.stop()
        if self.game_widget and self.game_widget.core:
            self.game_widget.core.unload()
        if self.game_widget and self.game_widget.audio_mgr:
            self.game_widget.audio_mgr.stop()
        self.salir_signal.emit()

    def cleanup(self):
        """Limpieza completa al cerrar la aplicación."""
        if self.timer:
            self.timer.stop()
        if self.game_widget and self.game_widget.core:
            self.game_widget.core.unload()
        if self.game_widget and self.game_widget.audio_mgr:
            self.game_widget.audio_mgr.stop()
