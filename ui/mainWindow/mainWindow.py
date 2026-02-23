import os
from PyQt6.QtWidgets import QMainWindow, QMenu
from PyQt6.QtCore import QFileSystemWatcher
from ui.mainWindow.mainWindowUI import MainWindowUI
from ui.gameWindow.gameWindow import GameWindow
from ui.configWindow.configWindow import ConfigWindow
from ui.sidebar.sidebar import Sidebar
from juego import Juego
from lista import Lista, SIN_LISTA


def _get_resource_path(relative_path):
    """Devuelve la ruta a un recurso empaquetado (ej: ui/)."""
    import sys
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, relative_path)
    else:
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return os.path.join(base, relative_path)


def _get_base_path():
    import sys
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # --- Declaración de todas las variables de instancia ---
        self.ui = None
        self.juegos = []
        self.botones_juego = {}
        self.labels_juego = {}
        self.menus_juego = {}
        self.game_page = None
        self.config_page = None
        self.sidebar = None
        self._ruta_games = None
        self._ruta_cores = None
        self._archivos_actuales = set()
        self._watcher = None
        self._filtro_lista_actual = None  # None = todos

        # --- Configuración de la UI ---
        self.ui = MainWindowUI()
        self.ui.setupUi(self)

        # Cargar hojas de estilo (una por componente)
        import glob
        ui_dir = _get_resource_path("ui")
        qss_total = ""
        for qss_file in sorted(glob.glob(os.path.join(ui_dir, "**", "*.qss"), recursive=True)):
            with open(qss_file, "r", encoding="utf-8") as f:
                qss_total += f.read() + "\n"
        if qss_total:
            self.setStyleSheet(qss_total)

        base = _get_base_path()

        # Escanear juegos
        ruta_games = os.path.join(base, "games")
        ruta_cores = os.path.join(base, "cores")
        self.juegos = Juego.escanear_juegos(ruta_games, ruta_cores)

        # Poblar el grid con cartas y conectar cada botón
        self.botones_juego, self.labels_juego, self.menus_juego = self.ui.poblar_grid(self.juegos)
        self._conectar_cartas()

        # Crear controlador de la sidebar y conectar señales
        self.sidebar = Sidebar(parent=self)
        self.ui.sidebar.setParent(None)  # quitar la SidebarUI por defecto
        # Insertar el widget del controlador Sidebar en el mismo sitio
        menu_layout = self.ui.menuPage.layout()
        menu_layout.insertWidget(0, self.sidebar.widget)
        self.sidebar.poblar(self.juegos)
        self.sidebar.todos_clicked.connect(self._mostrar_todos)
        self.sidebar.lista_clicked.connect(self._filtrar_por_lista)
        self.sidebar.juego_clicked.connect(self._on_sidebar_juego_clicked)

        # Página de configuración
        self.config_page = ConfigWindow()
        self.config_page.set_config_path(os.path.join(base, "config.json"))
        self.ui.stackedWidget.addWidget(self.config_page)  # index 1
        self.config_page.volumen_cambiado.connect(self._on_volume_changed)
        self.config_page.resolucion_cambiada.connect(self._on_resolution_changed)

        # Página de juego permanente (se crea una sola vez)
        self.game_page = GameWindow()
        self.ui.stackedWidget.addWidget(self.game_page)  # index 2
        self.game_page.salir_signal.connect(self._volver_menu)

        # Vigilar la carpeta games/ para refrescar la biblioteca automáticamente
        self._ruta_games = ruta_games
        self._ruta_cores = ruta_cores
        self._archivos_actuales = Juego.obtener_archivos_rom(ruta_games)
        self._watcher = QFileSystemWatcher([ruta_games], self)
        self._watcher.directoryChanged.connect(self._on_games_folder_changed)

        # Conectar navegación de la cabecera
        self.ui.header.navegacion.connect(self._navegar)

    def _jugar(self, juego):
        """Carga el juego seleccionado y cambia a la página de juego."""
        self.ui.header.hide()
        self.ui.stackedWidget.setCurrentWidget(self.game_page)
        # Aplicar resolución interna antes de cargar el core
        self.game_page.game_widget.core_options_extra = {
            'citra_resolution_factor': self.config_page.resolution_value,
        }
        self.game_page.load_game(juego)
        # Aplicar volumen actual al audio del juego
        if self.game_page.game_widget.audio_mgr:
            self.game_page.game_widget.audio_mgr.volume = self.config_page.volume / 100.0

    def _renombrar_juego(self, juego, nuevo_titulo):
        """Guarda el nombre personalizado del juego."""
        juego.titulo = nuevo_titulo

    def _on_games_folder_changed(self):
        """Re-escanea la carpeta games/ y reconstruye el grid de cartas."""
        archivos_nuevos = Juego.obtener_archivos_rom(self._ruta_games)
        Juego.migrar_renombrados(self._ruta_games, self._archivos_actuales, archivos_nuevos)
        self._archivos_actuales = archivos_nuevos
        self.juegos = Juego.escanear_juegos(self._ruta_games, self._ruta_cores)
        self.botones_juego, self.labels_juego, self.menus_juego = self.ui.poblar_grid(
            self.juegos, self._filtro_lista_actual
        )
        self._conectar_cartas()
        self._poblar_sidebar()

    def _volver_menu(self):
        """Vuelve al menú (el juego ya fue descargado por GameWindow)."""
        self.ui.header.show()
        self.ui.header.set_active(0)
        self.ui.stackedWidget.setCurrentIndex(0)

    def _navegar(self, index):
        """Cambia entre páginas del stacked widget (0=Biblioteca, 1=Config)."""
        self.ui.stackedWidget.setCurrentIndex(index)

    def _on_volume_changed(self, value):
        """Aplica el volumen al audio activo si hay juego en marcha."""
        audio_mgr = self.game_page.game_widget.audio_mgr
        if audio_mgr:
            audio_mgr.volume = value / 100.0

    def _on_resolution_changed(self, index):
        """Aplica la resolución al core activo si hay juego en marcha."""
        core = self.game_page.game_widget.core
        if core:
            core.set_option('citra_resolution_factor', self.config_page.resolution_value)

    # ------------------------------------------------------------------
    #  Sidebar helpers
    # ------------------------------------------------------------------

    def _conectar_cartas(self):
        """Conecta botones, labels y menús de las cartas del grid."""
        for btn, juego in self.botones_juego.items():
            btn.clicked.connect(lambda checked, j=juego: self._jugar(j))
        for lbl, juego in self.labels_juego.items():
            lbl.texto_cambiado.connect(lambda texto, j=juego: self._renombrar_juego(j, texto))
        for btn_menu, juego in self.menus_juego.items():
            btn_menu.clicked.connect(lambda checked, b=btn_menu, j=juego: self._mostrar_menu_carta(b, j))

    def _poblar_sidebar(self):
        """Reconstruye la barra lateral."""
        self.sidebar.poblar(self.juegos)

    def _filtrar_por_lista(self, nombre_lista):
        """Filtra las cartas del grid por la lista seleccionada."""
        self._filtro_lista_actual = nombre_lista
        self.botones_juego, self.labels_juego, self.menus_juego = self.ui.poblar_grid(
            self.juegos, nombre_lista
        )
        self._conectar_cartas()

    def _mostrar_todos(self):
        """Muestra todos los juegos (sin filtro de lista)."""
        self._filtro_lista_actual = None
        self.botones_juego, self.labels_juego, self.menus_juego = self.ui.poblar_grid(self.juegos)
        self._conectar_cartas()
        self._poblar_sidebar()

    def _mostrar_menu_carta(self, btn_menu, juego):
        """Muestra el menú contextual con opciones de lista para una carta."""
        menu = QMenu(self)
        menu.setObjectName("cardContextMenu")

        lista_actual = juego.lista
        todas = Lista.obtener_todas_con_sin_lista()

        for nombre_lista in todas:
            accion = menu.addAction(nombre_lista)
            accion.setCheckable(True)
            accion.setChecked(
                (nombre_lista == SIN_LISTA and lista_actual is None)
                or nombre_lista == lista_actual
            )
            accion.triggered.connect(
                lambda checked, nl=nombre_lista, j=juego: self._asignar_lista(j, nl)
            )

        menu.exec(btn_menu.mapToGlobal(btn_menu.rect().bottomLeft()))

    def _asignar_lista(self, juego, nombre_lista):
        """Asigna un juego a una lista y refresca la UI."""
        juego.lista = nombre_lista
        # Refrescar grid y sidebar
        self.botones_juego, self.labels_juego, self.menus_juego = self.ui.poblar_grid(
            self.juegos, self._filtro_lista_actual
        )
        self._conectar_cartas()
        self._poblar_sidebar()

    def _on_sidebar_juego_clicked(self, nombre_archivo):
        """Cuando se clica un juego en la sidebar, carga ese juego directamente."""
        for juego in self.juegos:
            if juego.nombre_archivo == nombre_archivo:
                self._jugar(juego)
                return

    def showEvent(self, event):
        """Reflow inicial cuando la ventana ya tiene su tamaño real."""
        super().showEvent(event)
        self.ui._reflow_grid()

    def resizeEvent(self, event):
        """Recalcula las columnas del grid al redimensionar la ventana."""
        super().resizeEvent(event)
        self.ui._reflow_grid()

    def closeEvent(self, event):
        """Al cerrar la ventana, limpiar el core si estaba activo."""
        self.game_page.unload_game()
        super().closeEvent(event)
