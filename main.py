import sys
import os
from PyQt6 import uic
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtCore import QTimer, Qt
from retro_core import RetroCore
from audio_manager import AudioManager
from input_manager import QtInputManager

def get_base_path():
    """Devuelve la ruta base del proyecto, compatible con PyInstaller."""
    if getattr(sys, 'frozen', False):
        # Ejecutando como exe empaquetado
        return os.path.dirname(sys.executable)
    else:
        # Ejecutando como script
        return os.path.dirname(os.path.abspath(__file__))

def get_resource_path(relative_path):
    """Devuelve la ruta a un recurso empaquetado (ej: ui/)."""
    if getattr(sys, 'frozen', False):
        # PyInstaller extrae datos a _MEIPASS
        return os.path.join(sys._MEIPASS, relative_path)
    else:
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)

class RetroOpenGLWidget(QOpenGLWidget):
    def __init__(self, parent=None, core_path=None, rom_path=None):
        super().__init__(parent)
        self.core_path = core_path
        self.rom_path = rom_path
        self.core = None
        self.audio_mgr = None
        self.input_mgr = None
        self.initialized = False
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus) # Accept key events
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        
    def initializeGL(self):
        if self.initialized:
            return
            
        print("Inicializando GL en RetroWidget...")
        
        # Rutas por defecto si no se pasan
        base = get_base_path()
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
        self.input_mgr = QtInputManager() # Use our new manager
        
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
            # Usar coordenadas físicas para el core/viewport para soportar HiDPI correctamente
            phys_w = int(w * dpr)
            phys_h = int(h * dpr)
            
            # print(f"ResizeGL (Logical): {w}x{h}, DPR: {dpr} -> Physical: {phys_w}x{phys_h}")
            
            self.core.update_video(phys_w, phys_h)
            # Update viewport in input manager for touch mapping
            vx, vy, vw, vh = self.core.view_rect
            # print(f"Resize Viewport (Phys): {vx},{vy} {vw}x{vh}")
            
            # El input manager también recibirá coordenadas físicas del evento de mouse
            self.input_mgr.update_viewport(vx, vy, vw, vh)

    def paintGL(self):
        if self.initialized and self.core:
            # Capturar el FBO de Qt antes de ejecutar el core
            # Qt usa un FBO interno para los QOpenGLWidget
            from OpenGL.GL import glGetIntegerv, GL_DRAW_FRAMEBUFFER_BINDING
            current_fbo = glGetIntegerv(GL_DRAW_FRAMEBUFFER_BINDING)
            self.core.set_target_fbo(current_fbo)
            
            # Recalcular viewport antes de correr el core por si la geometría cambió
            # (melonDS puede cambiar el layout de pantallas en cualquier momento)
            dpr = self.devicePixelRatio()
            phys_w = int(self.width() * dpr)
            phys_h = int(self.height() * dpr)
            self.core.update_video(phys_w, phys_h)
            vx, vy, vw, vh = self.core.view_rect
            self.input_mgr.update_viewport(vx, vy, vw, vh)
            
            self.core.run()
        else:
            # Clear black if not running
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


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # Cargar UI
        ui_path = get_resource_path(os.path.join("ui", "principal.ui"))
        uic.loadUi(ui_path, self)
        
        # Encontrar widgets clave
        self.scroll_area = self.findChild(object, "scrollArea") # QScrollArea
        
        # Eliminamos la imposición de layouts manuales que forzaban a ocupar toda la ventana.
        # Ahora se respetará la geometría definida en el archivo .ui (o los layouts que definas allí).
        
        # Reemplazar el openGLWidget placeholder por el nuestro
        # openGLWidget está dentro de scrollAreaWidgetContents
        self.old_widget = self.findChild(QOpenGLWidget, "openGLWidget")
        if self.old_widget:
            parent = self.old_widget.parent()
            
            self.old_widget.setParent(None) 
            self.old_widget.deleteLater()
            
            # Crear nueva instancia directamente como hijo de centralWidget
            self.game_widget = RetroOpenGLWidget(self.centralWidget())
            
            self.game_widget.show()
            self.game_widget.setFocus()
            
            # Posicionar con márgenes iniciales
            self._update_game_widget_geometry()
            
            # Timer para actualizar renderizado (60 FPS approx)
            self.timer = QTimer()
            self.timer.timeout.connect(self.game_widget.update)
            self.timer.start(16)
        else:
            print("Error: No se encontró 'openGLWidget' en la UI.")

    def _update_game_widget_geometry(self):
        """Recalcula la geometría del widget de juego con 200px de margen en los 4 lados."""
        if not hasattr(self, 'game_widget'):
            return
        cw = self.centralWidget()
        margin_top = 100
        margin_bottom = 100
        margin_left = 200
        margin_right = 200
        x = margin_left
        y = margin_top
        w = cw.width() - margin_left - margin_right
        h = cw.height() - margin_top - margin_bottom
        if w < 1:
            w = 1
        if h < 1:
            h = 1
        self.game_widget.setGeometry(x, y, w, h)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_game_widget_geometry()

    def closeEvent(self, event):
        if hasattr(self, 'game_widget'):
            self.game_widget.closeEvent(event)
        super().closeEvent(event)

if __name__ == "__main__":
    # Establecer CWD al directorio del exe/script para que las rutas relativas funcionen
    os.chdir(get_base_path())
    
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
