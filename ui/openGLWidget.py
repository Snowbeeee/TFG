# ── Imports ──────────────────────────────────────────────────────────
import os
import sys
# QOpenGLWidget: widget de Qt que crea y gestiona un contexto OpenGL.
# Permite renderizar directamente con OpenGL dentro de una ventana Qt.
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtCore import Qt, QTimer
from libretro.retro_core import RetroCore
from audio.audio_manager import AudioManager
from input.input_manager import QtInputManager


# Devuelve la ruta base del proyecto, compatible con PyInstaller.
# PyInstaller empaqueta todo en un ejecutable; sys.frozen indica si estamos en ese modo.
def _get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        # Subimos un nivel porque este archivo está en ui/
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Widget OpenGL que integra el core libretro con la interfaz de Qt.
# Hereda de QOpenGLWidget, que proporciona un contexto OpenGL embebido
# dentro de la jerarquía de widgets de Qt. Esto permite que el core
# renderice con OpenGL mientras el resto de la UI usa el sistema de
# ventanas normal de Qt.
class OpenGLWidget(QOpenGLWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.core_path = None          # Ruta a la DLL del core libretro
        self.rom_path = None           # Ruta al archivo ROM del juego
        self.core = None               # Instancia de RetroCore (wrapper del core)
        self.audio_mgr = None          # Instancia de AudioManager (salida de audio)
        self.input_mgr = None          # Instancia de QtInputManager (gestión de controles)
        self.initialized = False       # True cuando el juego se ha cargado correctamente
        self.gl_ready = False          # True cuando el contexto OpenGL de Qt está listo
        self.core_options_extra = {}   # Opciones del frontend (resolución, renderizador, etc.)
        self._pending_volume = 1.0     # Volumen a aplicar cuando se cree el AudioManager
        # StrongFocus: el widget recibe pulsaciones de teclado al hacer clic
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        # Tracking de ratón: recibir mouseMoveEvent incluso sin botón pulsado
        self.setMouseTracking(True)
        # WA_OpaquePaintEvent: indica a Qt que este widget pinta toda su área (optimización)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        # WA_NoSystemBackground: evita que Qt pinte un fondo antes de nuestro paintGL
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)

        # ── Gamepad polling ──
        # Pygame lee el estado del mando cada 16ms (~60 Hz) con un QTimer
        self._pygame_joystick = None
        self._gamepad_poll_timer = QTimer(self)
        self._gamepad_poll_timer.setInterval(16)  # ~60 Hz
        self._gamepad_poll_timer.timeout.connect(self._poll_gamepad)
        # Bindings pendientes: se aplican cuando se crea un nuevo input_mgr
        self._pending_bindings = None

    # Callback de Qt: se llama una sola vez cuando el contexto GL está listo.
    # No se puede usar OpenGL antes de que este método se ejecute.
    def initializeGL(self):
        self.gl_ready = True
        # Si hay un juego pendiente de cargar, cargarlo ahora
        if self.core_path and self.rom_path and not self.initialized:
            self._load_core()

    # Carga un juego. Si el contexto GL ya existe, carga inmediatamente.
    # Si no, se cargará cuando initializeGL sea llamado por Qt.
    def load_game(self, core_path, rom_path):
        # Descargar juego anterior si lo hay
        self.unload_game()
        self.core_path = core_path
        self.rom_path = rom_path
        if self.gl_ready:
            self._load_core()

    # Lógica interna de carga del core y el juego.
    def _load_core(self):
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

        # makeCurrent(): activa el contexto OpenGL de este widget.
        # Necesario antes de cualquier operación GL porque Qt puede tener
        # múltiples contextos y OpenGL es una máquina de estados global.
        self.makeCurrent()

        self.audio_mgr = AudioManager()
        self.audio_mgr.volume = self._pending_volume
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

    # Descarga el core y el audio, dejando el widget GL vivo.
    # El contexto OpenGL del widget NO se destruye aquí; se reutiliza
    # para el siguiente juego o se destruye con el widget.
    def unload_game(self):
        self._gamepad_poll_timer.stop()
        self._pygame_joystick = None
        if self.core:
            # makeCurrent() antes de unload: es necesario porque los recursos
            # OpenGL (FBOs, texturas, shaders) solo se pueden liberar con el
            # contexto activo. Si no, quedarían como "leaks" en la GPU.
            self.makeCurrent()
            self.core.unload()
            # Restablecer estado OpenGL limpio para el próximo core.
            # Citra deja activados depth test, blending, scissor, etc.
            # que interferirían con melonDS u otro core posterior.
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
                # Desactivar todos los estados GL que Citra deja activos
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
            # doneCurrent(): desactiva el contexto GL de este widget,
            # devolviendo el contexto nulo para evitar operaciones GL accidentales
            self.doneCurrent()
            self.core = None
        if self.audio_mgr:
            self.audio_mgr.stop()
            self.audio_mgr = None
        self.input_mgr = None
        self.initialized = False
        self.core_path = None
        self.rom_path = None

    # Guarda bindings para aplicar cuando se cree el input_mgr.
    # Si ya existe, los aplica inmediatamente.
    def set_pending_bindings(self, ds_bindings, n3ds_bindings):
        self._pending_bindings = (ds_bindings, n3ds_bindings)
        if self.input_mgr:
            self.input_mgr.load_bindings(ds_bindings, n3ds_bindings)

    # Intenta inicializar pygame.joystick y arranca el timer de polling.
    # pygame usa SDL2 internamente para detectar gamepads conectados.
    def _init_gamepad_polling(self):
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

    # Lee el estado actual del gamepad (botones, ejes, hats) y lo pasa al InputManager.
    # También gestiona hot-plug: detecta conexión/desconexión de mandos via eventos SDL2
    # sin necesidad de reinicializar pygame.
    def _poll_gamepad(self):
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

    # Callback de Qt: se llama cuando el widget cambia de tamaño.
    # w, h son coordenadas lógicas; hay que multiplicar por devicePixelRatio()
    # para obtener píxeles físicos reales (importante en pantallas HiDPI/Retina).
    def resizeGL(self, w, h):
        if self.core:
            # devicePixelRatio(): factor de escala de la pantalla (1.0 en 1080p, 2.0 en Retina)
            dpr = self.devicePixelRatio()
            phys_w = int(w * dpr)
            phys_h = int(h * dpr)
            
            self.core.update_video(phys_w, phys_h)
            vx, vy, vw, vh = self.core.view_rect
            self.input_mgr.update_viewport(vx, vy, vw, vh)

    # Callback de Qt: se llama cada vez que el widget debe repintarse.
    # Aquí se ejecuta un frame completo del emulador (retro_run).
    def paintGL(self):
        if self.initialized and self.core and self.core.lib:
            # defaultFramebufferObject(): devuelve el ID del FBO que Qt usa
            # para este widget. El core renderiza aquí y Qt lo muestra en pantalla.
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

    # ── Eventos de teclado ──
    # Qt llama a estos métodos cuando se pulsa/suelta una tecla mientras
    # este widget tiene el foco. Se delegan al InputManager.
    def keyPressEvent(self, event):
        if self.input_mgr:
            self.input_mgr.handle_key_press(event.key())

    def keyReleaseEvent(self, event):
        if self.input_mgr:
            self.input_mgr.handle_key_release(event.key())

    # ── Eventos de ratón (simulan pantalla táctil) ──
    # Las coordenadas del ratón se multiplican por dpr para convertir
    # de píxeles lógicos a físicos (necesario en pantallas HiDPI).
    def mousePressEvent(self, event):
        self.setFocus()  # Capturar foco para recibir teclas también
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

    # Al cerrar el widget, descargar el juego para liberar recursos
    def closeEvent(self, event):
        self.unload_game()
        super().closeEvent(event)
