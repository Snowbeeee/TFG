import os
import json
from PyQt6.QtWidgets import QMainWindow, QMenu
from PyQt6.QtCore import QFileSystemWatcher
from ui.mainWindow.mainWindowUI import MainWindowUI
from ui.gameWindow.gameWindow import GameWindow
from ui.configWindow.configWindow import ConfigWindow
from ui.controlsWindow.controlsWindow import ControlsWindow
from ui.sidebar.sidebar import Sidebar
from ui.popups.popupEliminar.popupEliminar import PopupEliminar
from ui.gameDetailPage.gameDetailPage import GameDetailPage
from game.juego import Game, extraer_titulo_rom
from lista import Lista, SIN_LISTA
from api.screenscraper import ScreenScraperAPI, obtener_ruta_portada


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
        self.cartas_juego = {}
        self.labels_juego = {}
        self.botones_carpeta = {}
        self.botones_borrar_carpeta = {}
        self.game_page = None
        self.config_page = None
        self.controls_page = None
        self.detail_page = None
        self.scraper_api = None

        self.sidebar = None
        self._ruta_games = None
        self._ruta_cores = None
        self._archivos_actuales = set()
        self._watcher = None
        self._filtro_lista_actual = None  # None = todos
        self._prev_ds_renderer_index = 0  # para detectar cambios de renderer DS
        self._prev_ds_resolution_index = 0
        self._prev_citra_resolution_index = 0

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
        self.juegos = Game.escanear_juegos(ruta_games, ruta_cores)

        # Usar portadas cacheadas como imagen de la carta
        for juego in self.juegos:
            portada = obtener_ruta_portada(ruta_games, juego.nombre_archivo)
            if portada:
                juego.imagen = portada

        # Poblar el grid con cartas y conectar
        self.cartas_juego, self.labels_juego, self.botones_carpeta, self.botones_borrar_carpeta = self.ui.poblar_grid(self.juegos)
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
        self.sidebar.lista_borrada.connect(self._borrar_lista)

        # Página de configuración
        self.config_page = ConfigWindow()
        self.config_page.set_config_path(os.path.join(base, "config.json"))
        self.ui.stackedWidget.addWidget(self.config_page)  # index 1
        self.controls_page = ControlsWindow()
        self.controls_page.set_config_path(os.path.join(base, "config.json"))
        self.ui.stackedWidget.addWidget(self.controls_page)  # index 2
        self.controls_page.controles_cambiados.connect(self._on_controls_changed)
        self.config_page.volumen_cambiado.connect(self._on_volume_changed)
        self.config_page.resolucion_cambiada.connect(self._on_graphics_changed)

        # Página de juego permanente (se crea una sola vez)
        self.game_page = GameWindow()
        self.ui.stackedWidget.addWidget(self.game_page)  # index 3
        self.game_page.salir_signal.connect(self._volver_menu)

        # ScreenScraper API
        config_path = os.path.join(base, "config.json")
        ss_devid, ss_devpassword = "", ""
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                ss_devid = cfg.get("screenscraper_devid", "")
                ss_devpassword = cfg.get("screenscraper_devpassword", "")
            except Exception:
                pass
        self.scraper_api = ScreenScraperAPI(
            devid=ss_devid, devpassword=ss_devpassword
        )

        # Página de detalle del juego
        self.detail_page = GameDetailPage(self.scraper_api, ruta_games)
        self.ui.stackedWidget.addWidget(self.detail_page)  # index 4
        self.detail_page.jugar_signal.connect(self._jugar)
        self.detail_page.volver_signal.connect(self._volver_menu)

        # Sincronizar game sidebar → config page
        self.game_page.sidebar.volumen_cambiado.connect(self._on_game_sidebar_volume)
        self.game_page.sidebar.resolucion_cambiada.connect(self._on_game_sidebar_graphics)

        # Vigilar la carpeta games/ para refrescar la biblioteca automáticamente
        self._ruta_games = ruta_games
        self._ruta_cores = ruta_cores
        self._archivos_actuales = Game.obtener_archivos_rom(ruta_games)
        self._watcher = QFileSystemWatcher([ruta_games], self)
        self._watcher.directoryChanged.connect(self._on_games_folder_changed)

        # Conectar navegación de la cabecera
        self.ui.header.navegacion.connect(self._navegar)

    def _build_core_options_extra(self):
        """Construye el dict de opciones gráficas para inyectar al core."""
        return {
            # melonDS DS
            'melonds_render_mode': self.config_page.ds_renderer_value,
            'melonds_opengl_resolution': self.config_page.ds_resolution_value,
            # Citra
            'citra_resolution_factor': self.config_page.citra_resolution_value,
        }

    def _jugar(self, juego):
        """Carga el juego seleccionado y cambia a la página de juego."""
        # Extraer y mostrar el título interno de la ROM
        titulo_rom = extraer_titulo_rom(juego.ruta_juego, juego.extension)
        if titulo_rom:
            print(f"[ROM] Título interno: {titulo_rom}")
        else:
            print(f"[ROM] No se pudo extraer el título interno de {juego.nombre_archivo}")

        self.ui.header.hide()
        # Sincronizar config → game sidebar antes de mostrar
        self._sync_config_to_game_sidebar()
        self.ui.stackedWidget.setCurrentWidget(self.game_page)
        # Cargar juego con las opciones gráficas actuales
        self.game_page.load_game(juego, self._build_core_options_extra())
        # Aplicar bindings DESPUÉS de load_game (que recrea el widget)
        self.game_page.game_widget.set_pending_bindings(
            self.controls_page.ds_bindings,
            self.controls_page.n3ds_bindings
        )
        # Registrar estado gráfico actual para detectar cambios en runtime
        self._prev_ds_renderer_index = self.config_page.ui.dsRendererCombo.currentIndex()
        self._prev_ds_resolution_index = self.config_page.ui.dsResolutionCombo.currentIndex()
        self._prev_citra_resolution_index = self.config_page.ui.citraResolutionCombo.currentIndex()
        # Aplicar volumen actual al audio del juego
        if self.game_page.game_widget.audio_mgr:
            self.game_page.game_widget.audio_mgr.volume = self.config_page.volume / 100.0

    def _renombrar_juego(self, juego, nuevo_titulo):
        """Guarda el nombre personalizado del juego."""
        juego.titulo = nuevo_titulo

    def _on_games_folder_changed(self):
        """Re-escanea la carpeta games/ y reconstruye el grid de cartas."""
        archivos_nuevos = Game.obtener_archivos_rom(self._ruta_games)
        Game.migrar_renombrados(self._ruta_games, self._archivos_actuales, archivos_nuevos)
        self._archivos_actuales = archivos_nuevos
        self.juegos = Game.escanear_juegos(self._ruta_games, self._ruta_cores)
        for juego in self.juegos:
            portada = obtener_ruta_portada(self._ruta_games, juego.nombre_archivo)
            if portada:
                juego.imagen = portada
        self.cartas_juego, self.labels_juego, self.botones_carpeta, self.botones_borrar_carpeta = self.ui.poblar_grid(
            self.juegos, self._filtro_lista_actual
        )
        self._conectar_cartas()
        self._poblar_sidebar()

    def _volver_menu(self):
        """Vuelve al menú (el juego ya fue descargado por GameWindow)."""
        self.ui.header.show()
        self.ui.header.set_active(0)
        self.ui.stackedWidget.setCurrentIndex(0)
        # Refrescar el grid por si se descargaron portadas nuevas
        self.cartas_juego, self.labels_juego, self.botones_carpeta, self.botones_borrar_carpeta = self.ui.poblar_grid(
            self.juegos, self._filtro_lista_actual
        )
        self._conectar_cartas()

    def _navegar(self, index):
        """Cambia entre páginas del stacked widget (0=Biblioteca, 1=Config)."""
        self.ui.stackedWidget.setCurrentIndex(index)

    def _on_volume_changed(self, value):
        """Aplica el volumen al audio activo si hay juego en marcha."""
        audio_mgr = self.game_page.game_widget.audio_mgr
        if audio_mgr:
            audio_mgr.volume = value / 100.0

    def _on_controls_changed(self):
        """Recarga los controles en el InputManager del juego activo."""
        self.game_page.game_widget.set_pending_bindings(
            self.controls_page.ds_bindings,
            self.controls_page.n3ds_bindings
        )

    def _on_graphics_changed(self):
        """Aplica las opciones gráficas al core activo si hay juego en marcha."""
        self._sync_config_to_game_sidebar()

        if not self.game_page.juego_actual:
            return

        # Comprobar si algo ha cambiado realmente
        new_renderer = self.config_page.ui.dsRendererCombo.currentIndex()
        new_ds_res = self.config_page.ui.dsResolutionCombo.currentIndex()
        new_citra_res = self.config_page.ui.citraResolutionCombo.currentIndex()

        ds_changed = (
            new_renderer != self._prev_ds_renderer_index
            or new_ds_res != self._prev_ds_resolution_index
        )
        citra_changed = new_citra_res != self._prev_citra_resolution_index

        if not ds_changed and not citra_changed:
            return

        is_ds = self.game_page.juego_actual.extension == '.nds'

        if is_ds and ds_changed:
            renderer_changed = new_renderer != self._prev_ds_renderer_index
            self._prev_ds_renderer_index = new_renderer
            self._prev_ds_resolution_index = new_ds_res
            self._prev_citra_resolution_index = new_citra_res
            if renderer_changed:
                # Cambio de renderer (SW↔GL) requiere reload completo
                print("[Frontend] Renderer DS cambiado → recargando con savestate")
                self.game_page.reload_game(self._build_core_options_extra())
                self.game_page.game_widget.set_pending_bindings(
                    self.controls_page.ds_bindings,
                    self.controls_page.n3ds_bindings
                )
                if self.game_page.game_widget.audio_mgr:
                    self.game_page.game_widget.audio_mgr.volume = self.config_page.volume / 100.0
            elif self.game_page.game_widget.core:
                # Solo resolución; melonDS la aplica via SET_SYSTEM_AV_INFO
                print("[Frontend] Resolución DS cambiada → hot-swap")
                for key, val in self._build_core_options_extra().items():
                    self.game_page.game_widget.core.set_option(key, val)
        elif not is_ds and citra_changed and self.game_page.game_widget.core:
            # Citra soporta hot-swap de resolución via set_option
            self._prev_ds_renderer_index = new_renderer
            self._prev_ds_resolution_index = new_ds_res
            self._prev_citra_resolution_index = new_citra_res
            print("[Frontend] Resolución 3DS cambiada → hot-swap")
            for key, val in self._build_core_options_extra().items():
                self.game_page.game_widget.core.set_option(key, val)

    # ── Sincronización bidireccional config ↔ game sidebar ──

    def _sync_config_to_game_sidebar(self):
        """Copia los valores de ConfigWindow a la sidebar del juego."""
        cp = self.config_page
        self.game_page.sidebar.sync_from_config(
            cp.volume,
            cp.ui.dsRendererCombo.currentIndex(),
            cp.ui.dsResolutionCombo.currentIndex(),
            cp.ui.citraResolutionCombo.currentIndex(),
        )

    def _on_game_sidebar_volume(self, value):
        """La sidebar del juego cambió el volumen → actualizar ConfigWindow y audio."""
        self.config_page.ui.volumeSlider.setValue(value)
        audio_mgr = self.game_page.game_widget.audio_mgr
        if audio_mgr:
            audio_mgr.volume = value / 100.0

    def _on_game_sidebar_graphics(self):
        """La sidebar del juego cambió gráficos → actualizar ConfigWindow y core."""
        sb = self.game_page.sidebar
        self.config_page.ui.dsRendererCombo.setCurrentIndex(sb.ds_renderer_index)
        self.config_page.ui.dsResolutionCombo.setCurrentIndex(sb.ds_resolution_index)
        self.config_page.ui.citraResolutionCombo.setCurrentIndex(sb.citra_resolution_index)
        # _on_graphics_changed se disparará automáticamente por la señal del combo

    # ------------------------------------------------------------------
    #  Sidebar helpers
    # ------------------------------------------------------------------

    def _conectar_cartas(self):
        """Conecta cartas clickables y labels editables del grid."""
        for carta, juego in self.cartas_juego.items():
            carta.clicked.connect(lambda j=juego: self._mostrar_detalle(j))
        for lbl, juego in self.labels_juego.items():
            lbl.texto_cambiado.connect(lambda texto, j=juego: self._renombrar_juego(j, texto))
        for btn, nombre_lista in self.botones_carpeta.items():
            btn.clicked.connect(lambda checked, nl=nombre_lista: self._filtrar_por_lista(nl))
        for btn, nombre_lista in self.botones_borrar_carpeta.items():
            btn.clicked.connect(lambda checked, nl=nombre_lista: self._borrar_lista(nl))

    def _poblar_sidebar(self):
        """Reconstruye la barra lateral."""
        self.sidebar.poblar(self.juegos)

    def _filtrar_por_lista(self, nombre_lista):
        """Filtra las cartas del grid por la lista seleccionada."""
        self._filtro_lista_actual = nombre_lista
        self.cartas_juego, self.labels_juego, self.botones_carpeta, self.botones_borrar_carpeta = self.ui.poblar_grid(
            self.juegos, nombre_lista
        )
        self._conectar_cartas()

    def _mostrar_todos(self):
        """Muestra todos los juegos (sin filtro de lista)."""
        self._filtro_lista_actual = None
        self.cartas_juego, self.labels_juego, self.botones_carpeta, self.botones_borrar_carpeta = self.ui.poblar_grid(self.juegos)
        self._conectar_cartas()
        self._poblar_sidebar()

    def _mostrar_detalle(self, juego):
        """Abre la página de detalle de un juego."""
        self.detail_page.mostrar_juego(juego)
        self.ui.stackedWidget.setCurrentWidget(self.detail_page)

    def _asignar_lista(self, juego, nombre_lista):
        """Asigna un juego a una lista y refresca la UI."""
        juego.lista = nombre_lista
        # Refrescar grid y sidebar
        self.cartas_juego, self.labels_juego, self.botones_carpeta, self.botones_borrar_carpeta = self.ui.poblar_grid(
            self.juegos, self._filtro_lista_actual
        )
        self._conectar_cartas()
        self._poblar_sidebar()

    def _borrar_lista(self, nombre_lista):
        """Muestra el popup de confirmación y elimina la carpeta si se acepta."""
        popup = PopupEliminar(nombre_lista, parent=self)
        if popup.exec():
            Lista.eliminar_lista(nombre_lista)
            self._mostrar_todos()

    def _on_sidebar_juego_clicked(self, nombre_archivo):
        """Cuando se clica un juego en la sidebar, abre su página de detalle."""
        for juego in self.juegos:
            if juego.nombre_archivo == nombre_archivo:
                self._mostrar_detalle(juego)
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
