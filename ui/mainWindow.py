import os
from PyQt6.QtWidgets import QMainWindow
from ui.mainWindowUI import MainWindowUI
from ui.gameWindow import GameWindow
from juego import Juego


def _get_resource_path(relative_path):
    """Devuelve la ruta a un recurso empaquetado (ej: ui/)."""
    import sys
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, relative_path)
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base, relative_path)


def _get_base_path():
    import sys
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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

        base = _get_base_path()

        # Escanear juegos
        ruta_games = os.path.join(base, "games")
        ruta_cores = os.path.join(base, "cores")
        self.juegos = Juego.escanear_juegos(ruta_games, ruta_cores)

        # Poblar el grid con cartas y conectar cada botón
        self.botones_juego, self.labels_juego = self.ui.poblar_grid(self.juegos)
        for btn, juego in self.botones_juego.items():
            btn.clicked.connect(lambda checked, j=juego: self._jugar(j))

        # Conectar edición de nombre → guardar en JSON
        for lbl, juego in self.labels_juego.items():
            lbl.texto_cambiado.connect(lambda texto, j=juego: self._renombrar_juego(j, texto))

        # Página de juego permanente (se crea una sola vez)
        self.game_page = GameWindow()
        self.ui.stackedWidget.addWidget(self.game_page)  # index 1
        self.game_page.salir_signal.connect(self._volver_menu)

    def _jugar(self, juego):
        """Carga el juego seleccionado y cambia a la página de juego."""
        self.ui.stackedWidget.setCurrentWidget(self.game_page)
        self.game_page.load_game(juego)

    def _renombrar_juego(self, juego, nuevo_titulo):
        """Guarda el nombre personalizado del juego."""
        juego.titulo = nuevo_titulo

    def _volver_menu(self):
        """Vuelve al menú (el juego ya fue descargado por GameWindow)."""
        self.ui.stackedWidget.setCurrentIndex(0)

    def resizeEvent(self, event):
        """Recalcula las columnas del grid al redimensionar la ventana."""
        super().resizeEvent(event)
        self.ui._reflow_grid()

    def closeEvent(self, event):
        """Al cerrar la ventana, limpiar el core si estaba activo."""
        self.game_page.unload_game()
        super().closeEvent(event)
