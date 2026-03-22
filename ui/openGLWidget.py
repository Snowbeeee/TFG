import os
import sys
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtCore import Qt, QTimer
from libretro.retro_core import RetroCore
from audio.audio_manager import AudioManager
from input.input_manager import QtInputManager


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
        self.core_options_extra = {}  # Opciones adicionales del frontend (resolución, etc.)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)

        # Gamepad polling
        self._pygame_joystick = None
        self._gamepad_poll_timer = QTimer(self)
        self._gamepad_poll_timer.setInterval(16)  # ~60 Hz
        self._gamepad_poll_timer.timeout.connect(self._poll_gamepad)
        # Pending bindings: se aplican cuando se crea un nuevo input_mgr
        self._pending_bindings = None

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

        # Asegurar contexto GL activo para la inicialización del core
        self.makeCurrent()

        self.audio_mgr = AudioManager()
        self.input_mgr = QtInputManager()
        self.core = RetroCore(self.core_path, self.audio_mgr, self.input_mgr)
        # Aplicar opciones extra del frontend (resolución, etc.)
        for key, val in self.core_options_extra.items():
            self.core.set_option(key, val)

        if self.core.load_game(self.rom_path):
            self.initialized = True
            print("Juego iniciado en Qt!")
            # Aplicar bindings pendientes antes de empezar
            if self._pending_bindings and self.input_mgr:
                ds_b, n3ds_b = self._pending_bindings
                self.input_mgr.load_bindings(ds_b, n3ds_b)
            self._init_gamepad_polling()
        else:
            print("Fallo al iniciar el juego")

        self.doneCurrent()

    def unload_game(self):
        """Descarga el core y el audio, dejando el widget GL vivo."""
        self._gamepad_poll_timer.stop()
        self._pygame_joystick = None
        if self.core:
            # Activar el contexto GL antes de descargar para que los
            # recursos OpenGL se liberen correctamente.
            self.makeCurrent()
            self.core.unload()
            # Restablecer estado OpenGL limpio para el próximo core
            from OpenGL.GL import (
                glBindFramebuffer, glBindTexture, glBindRenderbuffer,
                glUseProgram, glBindVertexArray, glBindBuffer,
                GL_FRAMEBUFFER, GL_TEXTURE_2D, GL_RENDERBUFFER,
                GL_ARRAY_BUFFER, GL_ELEMENT_ARRAY_BUFFER,
            )
            try:
                from OpenGL.GL import (
                    glBindFramebuffer, glBindTexture, glBindRenderbuffer,
                    glUseProgram, glBindVertexArray, glBindBuffer,
                    glActiveTexture, glViewport, glDisable, glColorMask,
                    glDepthMask, glScissor, glDepthFunc, glBlendFunc,
                    GL_FRAMEBUFFER, GL_TEXTURE_2D, GL_RENDERBUFFER,
                    GL_ARRAY_BUFFER, GL_ELEMENT_ARRAY_BUFFER,
                    GL_UNIFORM_BUFFER, GL_TEXTURE0, GL_TEXTURE1, GL_TEXTURE2,
                    GL_TEXTURE3, GL_TEXTURE4, GL_TEXTURE5, GL_TEXTURE6, GL_TEXTURE7,
                    GL_DEPTH_TEST, GL_BLEND, GL_SCISSOR_TEST, GL_STENCIL_TEST,
                    GL_CULL_FACE, GL_TRUE, GL_FALSE, GL_LESS, GL_SRC_ALPHA,
                    GL_ONE_MINUS_SRC_ALPHA,
                )
                glBindFramebuffer(GL_FRAMEBUFFER, 0)
                glUseProgram(0)
                try:
                    glBindVertexArray(0)
                except Exception:
                    pass
                glBindBuffer(GL_ARRAY_BUFFER, 0)
                glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)
                try:
                    glBindBuffer(GL_UNIFORM_BUFFER, 0)
                except Exception:
                    pass
                # Desvincular texturas en todas las unidades que Citra pueda haber usado
                for unit in (GL_TEXTURE0, GL_TEXTURE1, GL_TEXTURE2, GL_TEXTURE3,
                             GL_TEXTURE4, GL_TEXTURE5, GL_TEXTURE6, GL_TEXTURE7):
                    glActiveTexture(unit)
                    glBindTexture(GL_TEXTURE_2D, 0)
                glActiveTexture(GL_TEXTURE0)
                glBindRenderbuffer(GL_RENDERBUFFER, 0)
                # Restablecer estado GL al por defecto para que el siguiente core
                # parta de un contexto limpio (Citra deja depth/blend/scissor activos)
                glDisable(GL_DEPTH_TEST)
                glDisable(GL_BLEND)
                glDisable(GL_SCISSOR_TEST)
                glDisable(GL_STENCIL_TEST)
                glDisable(GL_CULL_FACE)
                glColorMask(GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE)
                glDepthMask(GL_TRUE)
                glDepthFunc(GL_LESS)
                glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
                # Viewport al tamaño del widget para que el próximo core empiece limpio
                w = max(1, self.width())
                h = max(1, self.height())
                glViewport(0, 0, w, h)
            except Exception as e:
                print(f"Aviso: Error reseteando estado GL: {e}")
            self.doneCurrent()
            self.core = None
        if self.audio_mgr:
            self.audio_mgr.stop()
            self.audio_mgr = None
        self.input_mgr = None
        self.initialized = False
        self.core_path = None
        self.rom_path = None

    def set_pending_bindings(self, ds_bindings, n3ds_bindings):
        """Guarda bindings para aplicar cuando se cree el input_mgr."""
        self._pending_bindings = (ds_bindings, n3ds_bindings)
        # Si ya hay input_mgr activo, aplicar inmediatamente
        if self.input_mgr:
            self.input_mgr.load_bindings(ds_bindings, n3ds_bindings)

    def _init_gamepad_polling(self):
        """Intenta inicializar pygame.joystick y arranca el timer de polling."""
        try:
            import pygame
            if not pygame.get_init():
                pygame.init()
            if not pygame.joystick.get_init():
                pygame.joystick.init()
            if pygame.joystick.get_count() > 0:
                self._pygame_joystick = pygame.joystick.Joystick(0)
                self._pygame_joystick.init()
            else:
                self._pygame_joystick = None
        except ImportError:
            self._pygame_joystick = None
        self._gamepad_poll_timer.start()

    def _poll_gamepad(self):
        """Lee estado del gamepad y lo pasa al InputManager, gestionando hot-plug via eventos SDL2."""
        if not self.input_mgr:
            return
        try:
            import pygame
            # Procesar eventos SDL2: detecta conexión/desconexión sin reinicializar
            for event in pygame.event.get():
                if event.type == pygame.JOYDEVICEADDED and self._pygame_joystick is None:
                    self._pygame_joystick = pygame.joystick.Joystick(event.device_index)
                    self._pygame_joystick.init()
                elif event.type == pygame.JOYDEVICEREMOVED:
                    self._pygame_joystick = None

            if not self._pygame_joystick:
                return

            buttons = {}
            for i in range(self._pygame_joystick.get_numbuttons()):
                buttons[i] = bool(self._pygame_joystick.get_button(i))
            axes = {}
            for i in range(self._pygame_joystick.get_numaxes()):
                axes[i] = self._pygame_joystick.get_axis(i)
            hats = {}
            for i in range(self._pygame_joystick.get_numhats()):
                hats[i] = self._pygame_joystick.get_hat(i)
            self.input_mgr.update_gamepad_state(buttons, axes, hats)
        except Exception:
            pass

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
            current_fbo = self.defaultFramebufferObject()
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
