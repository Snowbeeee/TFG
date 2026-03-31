import os
from PyQt6.QtWidgets import QWidget, QMenu, QVBoxLayout
from PyQt6.QtCore import QThread, pyqtSignal

from ui.gameDetailPage.gameDetailPageUI import GameDetailPageUI
from api.screenscraper import (
    ScreenScraperAPI, cargar_info_cache, guardar_info_cache,
    obtener_cache_dir, obtener_ruta_portada, obtener_rutas_galeria,
)
from game.game import extraer_titulo_rom
from lista import Lista, SIN_LISTA


class _ScraperWorker(QThread):
    """Hilo para llamar a la API sin bloquear la UI."""
    terminado = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, api, nombre_busqueda, extension, ruta_games, nombre_archivo, ruta_rom):
        super().__init__()
        self.api = api
        self.nombre_busqueda = nombre_busqueda
        self.extension = extension
        self.ruta_games = ruta_games
        self.nombre_archivo = nombre_archivo
        self.ruta_rom = ruta_rom

    def run(self):
        # 1º: Buscar por hash del fichero ROM (más fiable)
        print(f"[ScreenScraper] Intentando identificar por hash: '{self.nombre_archivo}'")
        info = self.api.buscar_por_hash(self.ruta_rom, self.extension)

        # 2º: Fallback a búsqueda por nombre
        if not info:
            print(f"[ScreenScraper] Hash no encontrado, buscando por nombre: '{self.nombre_busqueda}'")
            info = self.api.buscar_por_nombre(self.nombre_busqueda, self.extension)

        if not info:
            self.error.emit("No se encontró información del juego en ScreenScraper")
            return

        cache_dir = obtener_cache_dir(self.ruta_games, self.nombre_archivo)
        os.makedirs(cache_dir, exist_ok=True)

        # Descargar portada
        medias = info.get("medias", {})
        portada_url = medias.get("portada_url")
        if portada_url:
            ext = ".png" if ".png" in portada_url.lower() else ".jpg"
            cover_path = os.path.join(cache_dir, f"cover{ext}")
            if ScreenScraperAPI.descargar_imagen(portada_url, cover_path):
                info["cover_local"] = os.path.basename(cover_path)

        # Descargar imágenes de galería (máx. 20)
        imagenes_locales = []
        for i, img in enumerate(medias.get("imagenes", [])[:20]):
            url = img.get("url", "")
            if not url:
                continue
            tipo = img.get("type", f"img{i}")
            region = img.get("region", "")
            ext = ".png" if ".png" in url.lower() else ".jpg"
            safe = "".join(c for c in f"{tipo}_{region}"
                           if c.isalnum() or c in "_-") + ext
            path = os.path.join(cache_dir, safe)
            if not os.path.exists(path):
                if ScreenScraperAPI.descargar_imagen(url, path):
                    imagenes_locales.append(safe)
            else:
                imagenes_locales.append(safe)

        info["imagenes_locales"] = imagenes_locales

        # Quitar URLs crudas antes de cachear
        info.pop("medias", None)
        guardar_info_cache(self.ruta_games, self.nombre_archivo, info)
        self.terminado.emit(info)


class GameDetailPage(QWidget):
    """Página de detalle: muestra info de ScreenScraper y permite jugar."""

    jugar_signal = pyqtSignal(object)
    volver_signal = pyqtSignal()

    def __init__(self, api, ruta_games, parent=None):
        super().__init__(parent)
        self.api = api
        self.ruta_games = ruta_games
        self._juego_actual = None
        self._worker = None

        self.ui = GameDetailPageUI()
        self.ui.setupUi(self)

        self.ui.btn_volver.clicked.connect(self.volver_signal.emit)
        self.ui.btn_jugar.clicked.connect(self._on_jugar)
        self.ui.btn_menu.clicked.connect(self._on_menu)

    # ── Público ──

    def mostrar_juego(self, juego):
        """Carga la información del juego (desde caché o API)."""
        self._juego_actual = juego

        # Cancelar worker anterior si existe
        if self._worker and self._worker.isRunning():
            print("[ScreenScraper] Worker anterior aún corriendo, esperando…")
            self._worker.quit()
            self._worker.wait(3000)

        info = cargar_info_cache(self.ruta_games, juego.nombre_archivo)
        if info:
            from api.screenscraper import obtener_cache_dir, CACHE_INFO_FILE
            cache_path = os.path.join(obtener_cache_dir(self.ruta_games, juego.nombre_archivo), CACHE_INFO_FILE)
            print(f"[ScreenScraper] Caché encontrada para '{juego.nombre_archivo}' → {cache_path}")
            print(f"[ScreenScraper]   titulo={info.get('titulo', '?')!r}, generos={info.get('generos', [])}, desc={bool(info.get('descripcion'))}")
            self._mostrar_info(info, juego)
        else:
            print(f"[ScreenScraper] Sin caché para '{juego.nombre_archivo}', llamando a la API…")
            # Datos básicos mientras se busca
            self.ui.titulo_label.setText(juego.titulo)
            self.ui.consola_label.setText(f"🎮  {juego.consola}")
            self.ui.descripcion_label.setText("")
            self.ui.generos_label.setText("")
            self.ui.fecha_label.setText("")
            self.ui.editeur_label.setText("")
            self.ui.developpeur_label.setText("")
            self.ui.jugadores_label.setText("")
            self.ui.set_cover(juego.imagen)
            self.ui.set_galeria([])
            self.ui.mostrar_cargando(True)

            titulo_rom = extraer_titulo_rom(juego.ruta_juego, juego.extension)
            nombre_busqueda = titulo_rom if titulo_rom else juego.titulo
            print(f"[ScreenScraper] Buscando juego: '{nombre_busqueda}' (título ROM: {titulo_rom!r})")

            self._worker = _ScraperWorker(
                self.api, nombre_busqueda, juego.extension,
                self.ruta_games, juego.nombre_archivo, juego.ruta_juego,
            )
            self._worker.terminado.connect(
                lambda info_dict: self._on_api_ok(info_dict, juego))
            self._worker.error.connect(self._on_api_error)
            self._worker.start()

    # ── Callbacks de la API ──

    def _on_api_ok(self, info, juego):
        self.ui.mostrar_cargando(False)
        self._mostrar_info(info, juego)
        portada = obtener_ruta_portada(self.ruta_games, juego.nombre_archivo)
        if portada:
            juego.imagen = portada

    def _on_api_error(self, msg):
        self.ui.mostrar_cargando(False)
        self.ui.descripcion_label.setText(msg)

    # ── Presentación ──

    def _mostrar_info(self, info, juego):
        self.ui.titulo_label.setText(juego.titulo)
        self.ui.set_info(info)
        portada = obtener_ruta_portada(self.ruta_games, juego.nombre_archivo)
        self.ui.set_cover(portada)
        rutas = obtener_rutas_galeria(self.ruta_games, juego.nombre_archivo)
        self.ui.set_galeria(rutas)

    # ── Acciones ──

    def _on_jugar(self):
        if self._juego_actual:
            self.jugar_signal.emit(self._juego_actual)

    def _on_menu(self):
        """Menú contextual para asignar el juego a listas."""
        if not self._juego_actual:
            return
        juego = self._juego_actual
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
                lambda checked, nl=nombre_lista: self._asignar(nl))

        menu.exec(self.ui.btn_menu.mapToGlobal(
            self.ui.btn_menu.rect().bottomLeft()))

    def _asignar(self, nombre_lista):
        if self._juego_actual:
            self._juego_actual.lista = nombre_lista
