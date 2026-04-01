# ── Imports ──────────────────────────────────────────────────────
# time.perf_counter: reloj de alta precisión para medir FPS
import time

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from ui.gameWindow.gameWindowUI import GameWindowUI
from ui.openGLWidget import OpenGLWidget


# Página de juego: se crea una sola vez y se reutiliza para cada juego.
# Contiene un OpenGLWidget donde se renderiza el emulador, una sidebar
# de configuración rápida y un contador de FPS superpuesto.
class GameWindow(QWidget):

    salir_signal = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = GameWindowUI()
        self.ui.setupUi(self)
        self._juego_actual = None   # juego que se está ejecutando ahora mismo
        self._pending_state = None  # savestate en memoria para restaurar tras reload

        # Layout del contenedor (vacío hasta que se carga el primer juego)
        self._container_layout = QVBoxLayout(self.ui.openglContainer)
        self._container_layout.setContentsMargins(0, 0, 0, 0)

        # OpenGLWidget inicial
        self.game_widget = OpenGLWidget(self.ui.openglContainer)
        self._container_layout.addWidget(self.game_widget)

        # Timer permanente (parado)
        self.timer = QTimer()
        self.timer.timeout.connect(self._on_frame)

        # Conectar botón salir de la sidebar
        self.ui.gameSideBar.salir_clicked.connect(self._salir)

        # Performance tracking
        self._fps_frame_count = 0
        self._fps_last_time = 0.0

        _overlay_style = (
            "background-color: rgba(0, 0, 0, 160);"
            "font-size: 13px; font-weight: bold; padding: 2px 8px;"
        )
        self._fps_label = QLabel("FPS: --", self.ui.openglContainer)
        self._fps_label.setObjectName("fpsOverlay")
        self._fps_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._fps_label.setStyleSheet(
            _overlay_style + "color: #2ecc71; border-bottom-right-radius: 0px;"
        )
        self._fps_label.move(0, 0)
        self._fps_label.hide()

    # Destruye el OpenGLWidget actual y crea uno nuevo con contexto GL limpio.
    # Citra libretro deja objetos GL huérfanos (shaders, VAOs, texturas de caché)
    # que no libera en retro_deinit(). Recrear el widget fuerza a Qt a destruir el
    # contexto OpenGL antiguo y crear uno completamente limpio para el siguiente juego.
    # deleteLater(): no destruye inmediatamente, espera al event loop de Qt.
    def _recreate_game_widget(self):
        old = self.game_widget
        old.unload_game()                         # libera lo que puede
        self._container_layout.removeWidget(old)
        old.hide()
        old.deleteLater()                         # Qt destruye el contexto GL al procesar el evento

        self.game_widget = OpenGLWidget(self.ui.openglContainer)
        self._container_layout.addWidget(self.game_widget)

    # Tick del timer (~60 Hz): restaura savestate si hay uno pendiente,
    # actualiza el contador de FPS y repinta el widget OpenGL.
    # perf_counter: reloj monotonónico de nanosegundos, ideal para medir
    # intervalos cortos de tiempo con alta precisión.
    def _on_frame(self):
        # Si hay un savestate pendiente (tras reload), restaurarlo ahora
        if self._pending_state and self.game_widget.initialized and self.game_widget.core:
            state = self._pending_state
            self._pending_state = None
            QTimer.singleShot(32, lambda: self._restore_state(state))
        self._fps_frame_count += 1
        now = time.perf_counter()
        elapsed = now - self._fps_last_time
        if elapsed >= 0.5:
            fps = self._fps_frame_count / elapsed
            self._fps_label.setText(f"FPS: {fps:.1f}")
            self._fps_label.adjustSize()

            self._fps_frame_count = 0
            self._fps_last_time = now
        self.game_widget.update()

    # Restaura un savestate (bloque de bytes) en el core activo
    def _restore_state(self, state_data):
        if self.game_widget.core and self.game_widget.initialized:
            self.game_widget.core.load_state(state_data)

    # Atajo para acceder a la sidebar desde fuera
    @property
    def sidebar(self):
        return self.ui.gameSideBar

    @property
    def juego_actual(self):
        return self._juego_actual

    # Carga un juego: recrea el contexto GL limpio y arranca el timer de renderizado
    def load_game(self, juego, core_options_extra=None):
        self.timer.stop()
        self._recreate_game_widget()
        self._juego_actual = juego
        self.ui.gameSideBar.set_consola(juego.extension)
        if core_options_extra:
            self.game_widget.core_options_extra = core_options_extra
        self.game_widget.load_game(juego.ruta_core, juego.ruta_juego)
        self.game_widget.setFocus()
        self._fps_frame_count = 0
        self._fps_last_time = time.perf_counter() # primer muestreo (descartado)
        self._fps_label.setText("FPS: --")
        self._fps_label.adjustSize()
        self._fps_label.show()
        self._fps_label.raise_()
        if not self.timer.isActive():
            self.timer.start(16)

    # Recarga el juego actual con nuevas opciones gráficas (ej: cambio de renderer).
    # Guarda el estado completo en memoria (savestate) antes de recargar y lo
    # restaura después, por lo que el juego continúa exactamente donde estaba.
    # El savestate se restaura en el siguiente tick porque el core necesita
    # al menos un frame para inicializarse tras la carga.
    def reload_game(self, core_options_extra):
        if not self._juego_actual:
            return
        juego = self._juego_actual

        # 1. Guardar estado completo en memoria (savestate)
        state_data = None
        if self.game_widget.core:
            state_data = self.game_widget.core.save_state()
            if state_data is None:
                print("[Reload] Savestate no disponible; se perderá el estado en RAM")

        # 2. Recargar con contexto GL limpio y las nuevas opciones
        self.timer.stop()
        self._recreate_game_widget()
        self.game_widget.core_options_extra = core_options_extra
        self.game_widget.load_game(juego.ruta_core, juego.ruta_juego)
        self.game_widget.setFocus()
        if not self.timer.isActive():
            self.timer.start(16)

        # 3. Restaurar estado en el próximo tick (el core necesita al menos un frame)
        if state_data:
            self._pending_state = state_data
        else:
            self._pending_state = None

    # Descarga el juego actual y para el timer de renderizado
    def unload_game(self):
        self.timer.stop()
        self._fps_label.hide()
        self._juego_actual = None
        self._pending_state = None
        self.game_widget.unload_game()

    # Descarga el juego y emite señal para volver al menú principal
    def _salir(self):
        self.unload_game()
        self.salir_signal.emit()

    
