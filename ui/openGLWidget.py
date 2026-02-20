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
    def __init__(self, parent=None, core_path=None, rom_path=None):
        super().__init__(parent)
        self.core_path = core_path
        self.rom_path = rom_path
        self.core = None
        self.audio_mgr = None
        self.input_mgr = None
        self.initialized = False
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        
    def initializeGL(self):
        if self.initialized:
            return
            
        print("Inicializando GL en RetroWidget...")
        
        base = _get_base_path()
        if not self.core_path:
            self.core_path = os.path.join(base, 'cores/citra_libretro.dll')
            # self.core_path = os.path.join(base, 'cores/melondsds_libretro.dll')
        if not self.rom_path:
            self.rom_path = os.path.join(base, "games/PokemonSol.3ds")
            # self.rom_path = os.path.join(base, "games/LegendOfZeldaPhantomHourglass.nds")

        if not os.path.exists(self.core_path):
            print(f"Error: No se encuentra el core en {self.core_path}")
            return
            
        if not os.path.exists(self.rom_path):
            print(f"Error: ROM no encontrada (se verificará en load_game)")

        # Managers
        self.audio_mgr = AudioManager()
        self.input_mgr = QtInputManager()
        
        # Core
        self.core = RetroCore(self.core_path, self.audio_mgr, self.input_mgr)
        
        # Load Game
        if self.core.load_game(self.rom_path):
            self.initialized = True
            print("Juego iniciado en Qt!")
        else:
            print("Fallo al iniciar el juego")

    def resizeGL(self, w, h):
        if self.core:
            dpr = self.devicePixelRatio()
            phys_w = int(w * dpr)
            phys_h = int(h * dpr)
            
            self.core.update_video(phys_w, phys_h)
            vx, vy, vw, vh = self.core.view_rect
            self.input_mgr.update_viewport(vx, vy, vw, vh)

    def paintGL(self):
        if self.initialized and self.core:
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
        if self.core:
            self.core.unload()
        if self.audio_mgr:
            self.audio_mgr.stop()
        super().closeEvent(event)
