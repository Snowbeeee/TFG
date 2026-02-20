import os
from PyQt6.QtWidgets import QMainWindow
from ui.mainWindowUI import MainWindowUI
from ui.gameWindow import GameWindow


def _get_resource_path(relative_path):
    """Devuelve la ruta a un recurso empaquetado (ej: ui/)."""
    import sys
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, relative_path)
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base, relative_path)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = MainWindowUI()
        self.ui.setupUi(self)

        # Cargar hoja de estilos
        qss_path = _get_resource_path(os.path.join("ui", "styles.qss"))
        if os.path.exists(qss_path):
            with open(qss_path, "r") as f:
                self.setStyleSheet(f.read())

        # Referencia a la página de juego (se crea al pulsar "Jugar")
        self.game_page = GameWindow()
        self.ui.stackedWidget.addWidget(self.game_page)
        self.game_page.salir_signal.connect(self._volver_menu)

        # Conectar botón "Jugar"
        self.ui.pushButtonJugar.clicked.connect(self._jugar)

    def _jugar(self):
        """Crea la página de juego y cambia a ella."""
        self.ui.stackedWidget.setCurrentWidget(self.game_page)
        self.game_page.start()

        self.ui.stackedWidget.setCurrentWidget(self.game_page)
        # Iniciar el OpenGL DESPUÉS de estar dentro del stacked widget
        self.game_page.start()

    def _volver_menu(self):
        """Vuelve al menú principal."""
        self.ui.stackedWidget.setCurrentIndex(0)

        # Limpiar la página de juego para poder relanzarla fresca
        if self.game_page:
            self.ui.stackedWidget.setCurrentIndex(0)

    def closeEvent(self, event):
        """Al cerrar la ventana, limpiar el core si estaba activo."""
        if self.game_page:
            self.game_page.cleanup()
        super().closeEvent(event)
