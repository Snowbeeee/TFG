import os
import sys
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtCore import Qt
from retro_core import RetroCore
from audio_manager import AudioManager
from input_manager import QtInputManager


def _get_base_path():
    """Devuelve la ruta base del proyecto, compatible con PyInstaller."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        # Subimos un nivel porque este archivo está en ui/
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class OpenGLWidget(QOpenGLWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.core_path = None
        self.rom_path = None
        self.core = None
        self.audio_mgr = None
        self.input_mgr = None
        self.initialized = False
        self.gl_ready = False
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)

    def initializeGL(self):
        """Se llama una sola vez por Qt cuando el contexto GL está listo."""
        self.gl_ready = True
        # Si hay un juego pendiente de cargar, cargarlo ahora
        if self.core_path and self.rom_path and not self.initialized:
            self._load_core()

    def load_game(self, core_path, rom_path):
        """Carga un juego. Si el contexto GL ya existe, carga inmediatamente.
        Si no, se cargará cuando initializeGL sea llamado por Qt."""
        # Descargar juego anterior si lo hay
        self.unload_game()
        self.core_path = core_path
        self.rom_path = rom_path
        if self.gl_ready:
            self._load_core()

    def _load_core(self):
        """Lógica interna de carga del core y el juego."""
        print("Inicializando GL en RetroWidget...")

        if not self.core_path or not self.rom_path:
            print("Error: No se ha proporcionado core_path o rom_path")
            return

        if not os.path.exists(self.core_path):
            print(f"Error: No se encuentra el core en {self.core_path}")
            return

        if not os.path.exists(self.rom_path):
            print(f"Error: ROM no encontrada en {self.rom_path}")
            return

        self.audio_mgr = AudioManager()
        self.input_mgr = QtInputManager()
        self.core = RetroCore(self.core_path, self.audio_mgr, self.input_mgr)

        if self.core.load_game(self.rom_path):
            self.initialized = True
            print("Juego iniciado en Qt!")
        else:
            print("Fallo al iniciar el juego")

    def unload_game(self):
        """Descarga el core y el audio, dejando el widget GL vivo."""
        if self.core:
            self.core.unload()
            self.core = None
        if self.audio_mgr:
            self.audio_mgr.stop()
            self.audio_mgr = None
        self.input_mgr = None
        self.initialized = False
        self.core_path = None
        self.rom_path = None

    def resizeGL(self, w, h):
        if self.core:
            dpr = self.devicePixelRatio()
            phys_w = int(w * dpr)
            phys_h = int(h * dpr)
            
            self.core.update_video(phys_w, phys_h)
            vx, vy, vw, vh = self.core.view_rect
            self.input_mgr.update_viewport(vx, vy, vw, vh)

    def paintGL(self):
        if self.initialized and self.core and self.core.lib:
            from OpenGL.GL import glGetIntegerv, GL_DRAW_FRAMEBUFFER_BINDING
            current_fbo = glGetIntegerv(GL_DRAW_FRAMEBUFFER_BINDING)
            self.core.set_target_fbo(current_fbo)
            
            dpr = self.devicePixelRatio()
            phys_w = int(self.width() * dpr)
            phys_h = int(self.height() * dpr)
            self.core.update_video(phys_w, phys_h)
            vx, vy, vw, vh = self.core.view_rect
            self.input_mgr.update_viewport(vx, vy, vw, vh)
            
            self.core.run()
        else:
            from OpenGL.GL import glClear, glClearColor, GL_COLOR_BUFFER_BIT
            glClearColor(0, 0, 0, 1)
            glClear(GL_COLOR_BUFFER_BIT)

    def keyPressEvent(self, event):
        if self.input_mgr:
            self.input_mgr.handle_key_press(event.key())

    def keyReleaseEvent(self, event):
        if self.input_mgr:
            self.input_mgr.handle_key_release(event.key())
            
    def mousePressEvent(self, event):
        self.setFocus()
        if self.input_mgr:
            dpr = self.devicePixelRatio()
            self.input_mgr.handle_mouse_press(event.pos().x() * dpr, event.pos().y() * dpr)
        event.accept()
            
    def mouseReleaseEvent(self, event):
        if self.input_mgr:
            dpr = self.devicePixelRatio()
            self.input_mgr.handle_mouse_release(event.pos().x() * dpr, event.pos().y() * dpr)
        event.accept()
        
    def mouseMoveEvent(self, event):
        if self.input_mgr:
            dpr = self.devicePixelRatio()
            self.input_mgr.handle_mouse_move(event.pos().x() * dpr, event.pos().y() * dpr)
        event.accept()

    def closeEvent(self, event):
        self.unload_game()
        super().closeEvent(event)
