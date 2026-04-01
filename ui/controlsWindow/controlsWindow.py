# ── Imports ──────────────────────────────────────────────────────
import os
import json
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from ui.controlsWindow.controlsWindowUI import ControlsWindowUI

# ── Constantes ───────────────────────────────────────────────────
# Mapeo inverso de las constantes Qt.Key a nombres legibles.
# vars(Qt.Key) devuelve {"Key_A": 65, "Key_B": 66, ...}
_QT_KEY_NAMES = {v: k.replace("Key_", "") for k, v in vars(Qt.Key).items() if k.startswith("Key_")}

# Nombres legibles para botones de gamepad (convención SDL/Xbox)
_GAMEPAD_BUTTON_NAMES = {
    0: "GP A", 1: "GP B", 2: "GP X", 3: "GP Y",
    4: "GP Back", 5: "GP Guide", 6: "GP Start",
    7: "GP L3", 8: "GP R3",
    9: "GP LB", 10: "GP RB",
    11: "GP Up", 12: "GP Down", 13: "GP Left", 14: "GP Right",
}

# Nombres legibles para ejes analógicos del gamepad
_GAMEPAD_AXIS_NAMES = {
    0: "GP LStick X", 1: "GP LStick Y",
    2: "GP RStick X", 3: "GP RStick Y",
    4: "GP LTrigger", 5: "GP RTrigger",
}

# Nombres legibles para hats (D-pad digital en SDL2)
_GAMEPAD_HAT_NAMES = {
    (0, 1): "GP DPad Up", (0, -1): "GP DPad Down",
    (-1, 0): "GP DPad Left", (1, 0): "GP DPad Right",
}

# Asignaciones por defecto de teclado para botones DS.
# Los valores son constantes Qt.Key (enteros) que se comparan con event.key().
DS_DEFAULTS = {
    "a":      Qt.Key.Key_X,
    "b":      Qt.Key.Key_Z,
    "x":      Qt.Key.Key_S,
    "y":      Qt.Key.Key_A,
    "l":      Qt.Key.Key_Q,
    "r":      Qt.Key.Key_W,
    "start":  Qt.Key.Key_Return,
    "select": Qt.Key.Key_Shift,
    "up":     Qt.Key.Key_Up,
    "down":   Qt.Key.Key_Down,
    "left":   Qt.Key.Key_Left,
    "right":  Qt.Key.Key_Right,
}

# Asignaciones por defecto de teclado para botones 3DS.
# Incluye botones extra: ZL, ZR y Circle Pad (stick analógico).
N3DS_DEFAULTS = {
    "a":            Qt.Key.Key_X,
    "b":            Qt.Key.Key_Z,
    "x":            Qt.Key.Key_S,
    "y":            Qt.Key.Key_A,
    "l":            Qt.Key.Key_Q,
    "r":            Qt.Key.Key_W,
    "zl":           Qt.Key.Key_1,
    "zr":           Qt.Key.Key_2,
    "start":        Qt.Key.Key_Return,
    "select":       Qt.Key.Key_Shift,
    "up":           Qt.Key.Key_Up,
    "down":         Qt.Key.Key_Down,
    "left":         Qt.Key.Key_Left,
    "right":        Qt.Key.Key_Right,
    "circle_up":    Qt.Key.Key_I,
    "circle_down":  Qt.Key.Key_K,
    "circle_left":  Qt.Key.Key_J,
    "circle_right": Qt.Key.Key_L,
}


# Devuelve un nombre legible para mostrar en el botón de la UI.
# binding es un dict con "type" y "value", por ejemplo:
#   {"type": "key", "value": 88}  → tecla X
#   {"type": "gamepad_button", "value": 0}  → botón A del mando
#   {"type": "gamepad_axis", "value": 4, "direction": "+"}  → gatillo izquierdo
#   {"type": "gamepad_hat", "value": 0, "hx": 0, "hy": 1}  → D-pad arriba
def _friendly_name(binding):
    if binding is None:
        return "Sin asignar"
    t = binding.get("type")
    v = binding.get("value")
    if t == "key":
        return _QT_KEY_NAMES.get(v, f"Key {v}")
    if t == "gamepad_button":
        return _GAMEPAD_BUTTON_NAMES.get(v, f"GP Btn {v}")
    if t == "gamepad_axis":
        direction = binding.get("direction", "+")
        name = _GAMEPAD_AXIS_NAMES.get(v, f"GP Axis {v}")
        return f"{name} {direction}"
    if t == "gamepad_hat":
        hat_idx = binding.get("hat", 0)
        hx = binding.get("hx", 0)
        hy = binding.get("hy", 0)
        name = _GAMEPAD_HAT_NAMES.get((hx, hy), f"GP Hat{hat_idx} ({hx},{hy})")
        return name
    return str(v)


# Página de asignación de controles para DS y 3DS.
# Permite reasignar cada botón a una tecla de teclado o botón/eje de gamepad.
# Usa un flujo de captura: el usuario hace clic en un botón, se activa la espera
# de input (teclado o gamepad), y al detectarlo se guarda la asignación.
class ControlsWindow(QWidget):

    # Señal emitida cuando cambia cualquier asignación de controles
    controles_cambiados = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.ui = None
        self._config_path = None
        self._waiting_for_input = False
        self._waiting_button = None   # QPushButton que espera input
        self._waiting_key = None      # clave config ("a", "b", ...)
        self._waiting_console = None  # "ds" o "3ds"
        self._timeout_timer = None

        # Mapeos actuales: clave_config → {"type": "key"|"gamepad_button"|"gamepad_axis", "value": int, ...}
        self._ds_bindings = {}
        self._n3ds_bindings = {}

        # Gamepad polling
        self._gamepad = None
        self._gamepad_timer = None
        self._prev_gamepad_buttons = {}
        self._prev_gamepad_axes = {}
        self._prev_gamepad_hats = {}

        # --- UI ---
        self.ui = ControlsWindowUI()
        self.ui.setupUi(self)

        # Conectar botones DS
        for key, btn in self.ui.ds_bind_buttons.items():
            btn.clicked.connect(lambda checked, k=key, b=btn: self._start_binding("ds", k, b))

        # Conectar botones 3DS
        for key, btn in self.ui.n3ds_bind_buttons.items():
            btn.clicked.connect(lambda checked, k=key, b=btn: self._start_binding("3ds", k, b))

        # Botones reset
        self.ui.ds_reset_btn.clicked.connect(lambda: self._reset_defaults("ds"))
        self.ui.n3ds_reset_btn.clicked.connect(lambda: self._reset_defaults("3ds"))

        # Timeout
        self._timeout_timer = QTimer(self)
        self._timeout_timer.setSingleShot(True)
        self._timeout_timer.timeout.connect(self._cancel_binding)

        # Init defaults
        self._apply_defaults()

        # Intentar inicializar gamepad
        self._init_gamepad()

    # ── Config path ──

    # Establece la ruta de config.json y carga los controles guardados
    def set_config_path(self, path):
        self._config_path = path
        self._cargar_config()
        self._refresh_all_labels()

    # ── Defaults ──
    # Aplica los controles por defecto a ambos mapeos
    def _apply_defaults(self):
        for k, v in DS_DEFAULTS.items():
            self._ds_bindings[k] = {"type": "key", "value": int(v)}
        for k, v in N3DS_DEFAULTS.items():
            self._n3ds_bindings[k] = {"type": "key", "value": int(v)}
        self._refresh_all_labels()

    def _reset_defaults(self, console):
        if console == "ds":
            for k, v in DS_DEFAULTS.items():
                self._ds_bindings[k] = {"type": "key", "value": int(v)}
        else:
            for k, v in N3DS_DEFAULTS.items():
                self._n3ds_bindings[k] = {"type": "key", "value": int(v)}
        self._refresh_all_labels()
        self._guardar_config()
        self.controles_cambiados.emit()

    # ── Label refresh ──
    # Actualiza el texto de todos los botones con el nombre legible del binding.
    # También resetea la propiedad CSS "conflict" y reaplica estilos.
    # unpolish/polish: Qt necesita reaplicar el QSS al cambiar propiedades dinámicas.
    def _refresh_all_labels(self):
        for key, btn in self.ui.ds_bind_buttons.items():
            binding = self._ds_bindings.get(key)
            btn.setText(_friendly_name(binding))
            btn.setProperty("conflict", False)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        for key, btn in self.ui.n3ds_bind_buttons.items():
            binding = self._n3ds_bindings.get(key)
            btn.setText(_friendly_name(binding))
            btn.setProperty("conflict", False)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    # ── Flujo de captura de controles ──

    # Inicia la captura: marca el botón como "esperando", captura el teclado
    # con grabKeyboard() (todo input de teclado va a este widget),
    # guarda un snapshot del estado del gamepad para detectar cambios,
    # y arranca un timeout de 5 segundos.
    def _start_binding(self, console, key, btn):
        # Si ya estábamos esperando, cancelar la anterior
        if self._waiting_for_input:
            self._cancel_binding()

        self._waiting_for_input = True
        self._waiting_button = btn
        self._waiting_key = key
        self._waiting_console = console
        btn.setText("Pulsa una tecla...")
        btn.setProperty("waiting", True)
        btn.setProperty("conflict", False)
        btn.style().unpolish(btn)
        btn.style().polish(btn)

        # Capturar gamepad state actual para detectar cambios
        self._snapshot_gamepad()

        # Timeout de 5 s
        self._timeout_timer.start(5000)

        # Capturar teclado
        self.setFocus()
        self.grabKeyboard()

    # Completa la asignación con el binding capturado.
    # releaseKeyboard(): devuelve el teclado al sistema normal de eventos Qt.
    def _finish_binding(self, binding):
        self._timeout_timer.stop()
        self.releaseKeyboard()

        # Desasignar la misma tecla/botón si ya estaba en otro sitio
        self._remove_conflicts(self._waiting_console, self._waiting_key, binding)

        if self._waiting_console == "ds":
            self._ds_bindings[self._waiting_key] = binding
        else:
            self._n3ds_bindings[self._waiting_key] = binding

        self._waiting_button.setText(_friendly_name(binding))
        self._waiting_button.setProperty("waiting", False)
        self._waiting_button.style().unpolish(self._waiting_button)
        self._waiting_button.style().polish(self._waiting_button)

        self._waiting_for_input = False
        self._waiting_button = None
        self._waiting_key = None
        self._waiting_console = None

        self._guardar_config()
        self.controles_cambiados.emit()

    # Cancela la captura sin modificar ningún binding
    def _cancel_binding(self):
        self._timeout_timer.stop()
        self.releaseKeyboard()

        if self._waiting_button:
            # Restaurar texto
            if self._waiting_console == "ds":
                binding = self._ds_bindings.get(self._waiting_key)
            else:
                binding = self._n3ds_bindings.get(self._waiting_key)
            self._waiting_button.setText(_friendly_name(binding))
            self._waiting_button.setProperty("waiting", False)
            self._waiting_button.style().unpolish(self._waiting_button)
            self._waiting_button.style().polish(self._waiting_button)

        self._waiting_for_input = False
        self._waiting_button = None
        self._waiting_key = None
        self._waiting_console = None

    # ── Detección de conflictos ──

    # Comprueba si dos bindings representan la misma entrada física
    def _bindings_equal(self, b1, b2):
        if b1 is None or b2 is None:
            return False
        if b1.get("type") != b2.get("type") or b1.get("value") != b2.get("value"):
            return False
        t = b1.get("type")
        if t == "gamepad_axis":
            return b1.get("direction") == b2.get("direction")
        if t == "gamepad_hat":
            return b1.get("hx") == b2.get("hx") and b1.get("hy") == b2.get("hy")
        return True

    # Si el binding ya está asignado a otro botón de la misma consola, lo desasigna.
    # Evita que dos botones tengan la misma tecla/botón del mando.
    def _remove_conflicts(self, console, key, binding):
        bindings = self._ds_bindings if console == "ds" else self._n3ds_bindings
        buttons = self.ui.ds_bind_buttons if console == "ds" else self.ui.n3ds_bind_buttons

        for k, existing in bindings.items():
            if k == key:
                continue
            if self._bindings_equal(existing, binding):
                bindings[k] = None
                btn = buttons.get(k)
                if btn:
                    btn.setText("Sin asignar")
                    btn.setProperty("conflict", True)
                    btn.style().unpolish(btn)
                    btn.style().polish(btn)

    # ── Captura de teclado ──
    # keyPressEvent se llama cuando hay una tecla pulsada y tenemos grabKeyboard.
    # Escape cancela la captura; cualquier otra tecla completa la asignación.
    def keyPressEvent(self, event):
        if self._waiting_for_input:
            key = event.key()
            if key == Qt.Key.Key_Escape:
                self._cancel_binding()
                return
            self._finish_binding({"type": "key", "value": key})
            return
        super().keyPressEvent(event)

    # ── Soporte de gamepad (polling con pygame/SDL2) ──

    # Inicializa pygame.joystick para leer gamepads conectados.
    # pygame.init() inicializa SDL2 internamente.
    def _init_gamepad(self):
        try:
            import pygame
            if not pygame.get_init():
                pygame.init()
            if not pygame.joystick.get_init():
                pygame.joystick.init()
            if pygame.joystick.get_count() > 0:
                self._gamepad = pygame.joystick.Joystick(0)
                self._gamepad.init()
            else:
                self._gamepad = None
        except ImportError:
            self._gamepad = None

        # Timer de polling a 60 Hz
        if self._gamepad_timer is None:
            self._gamepad_timer = QTimer(self)
            self._gamepad_timer.setInterval(16)
            self._gamepad_timer.timeout.connect(self._poll_gamepad)
        self._gamepad_timer.start()

    # Guarda el estado actual del gamepad (botones, ejes, hats) para
    # comparar después y detectar qué cambió (patrón "snapshot + diff").
    def _snapshot_gamepad(self):
        self._prev_gamepad_buttons = {}
        self._prev_gamepad_axes = {}
        self._prev_gamepad_hats = {}
        if not self._gamepad:
            return
        try:
            import pygame
            self._process_gamepad_events()
            for i in range(self._gamepad.get_numbuttons()):
                self._prev_gamepad_buttons[i] = self._gamepad.get_button(i)
            for i in range(self._gamepad.get_numaxes()):
                self._prev_gamepad_axes[i] = self._gamepad.get_axis(i)
            for i in range(self._gamepad.get_numhats()):
                self._prev_gamepad_hats[i] = self._gamepad.get_hat(i)
        except Exception:
            pass

    # Gestiona hot-plug de gamepads via eventos SDL2.
    # JOYDEVICEADDED/REMOVED se disparan cuando se conecta/desconecta un mando.
    def _process_gamepad_events(self):
        try:
            import pygame
            for event in pygame.event.get():
                if event.type == pygame.JOYDEVICEADDED and self._gamepad is None:
                    self._gamepad = pygame.joystick.Joystick(event.device_index)
                    self._gamepad.init()
                elif event.type == pygame.JOYDEVICEREMOVED:
                    self._gamepad = None
        except Exception:
            pass

    # Comprueba si se ha pulsado un botón, movido un hat (D-pad) o un eje (stick/trigger).
    # Para ejes: se usan dos umbrales distintos:
    #   - AXIS_THRESHOLD = 0.7: para sticks analógicos (reposo en 0.0)
    #   - TRIGGER_THRESHOLD = 0.3: para gatillos (reposo en -1.0 en SDL2)
    # Los triggers en SDL2 van de -1.0 (sin pulsar) a +1.0 (pulsado al máximo),
    # a diferencia de los sticks que van de -1.0 a +1.0 con centro en 0.0.
    def _poll_gamepad(self):
        self._process_gamepad_events()
        if not self._waiting_for_input or not self._gamepad:
            return
        try:
            import pygame

            # Comprobar botones
            for i in range(self._gamepad.get_numbuttons()):
                current = self._gamepad.get_button(i)
                prev = self._prev_gamepad_buttons.get(i, 0)
                if current and not prev:
                    self._finish_binding({"type": "gamepad_button", "value": i})
                    return

            # Comprobar hats (D-pad en Xbox)
            for i in range(self._gamepad.get_numhats()):
                current = self._gamepad.get_hat(i)
                prev = self._prev_gamepad_hats.get(i, (0, 0))
                if current != (0, 0) and current != prev:
                    hx, hy = current
                    self._finish_binding({"type": "gamepad_hat", "value": i, "hat": i, "hx": hx, "hy": hy})
                    return

            # Comprobar ejes (sticks y triggers)
            AXIS_THRESHOLD = 0.7
            TRIGGER_THRESHOLD = 0.3
            for i in range(self._gamepad.get_numaxes()):
                current = self._gamepad.get_axis(i)
                prev = self._prev_gamepad_axes.get(i, 0.0)
                # Triggers (axes 4,5 en Xbox): reposo en -1.0, pulsado hacia +1.0
                is_trigger = i in (4, 5)
                if is_trigger:
                    if current > TRIGGER_THRESHOLD and prev <= TRIGGER_THRESHOLD:
                        self._finish_binding({"type": "gamepad_axis", "value": i, "direction": "+"})
                        return
                else:
                    if abs(current) > AXIS_THRESHOLD and abs(prev) < AXIS_THRESHOLD:
                        direction = "+" if current > 0 else "-"
                        self._finish_binding({"type": "gamepad_axis", "value": i, "direction": direction})
                        return
        except Exception:
            pass

    # showEvent/hideEvent: Qt los llama al mostrar/ocultar el widget.
    # Se arranca/para el timer de polling para no consumir CPU cuando no es visible.
    def showEvent(self, event):
        super().showEvent(event)
        if self._gamepad_timer:
            self._gamepad_timer.start()

    def hideEvent(self, event):
        super().hideEvent(event)
        if self._gamepad_timer:
            self._gamepad_timer.stop()
        if self._waiting_for_input:
            self._cancel_binding()

    # ── Persistencia ──
    # Carga las asignaciones de controles desde config.json
    def _cargar_config(self):
        if not self._config_path or not os.path.exists(self._config_path):
            return
        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            ds_cfg = cfg.get("controls_ds")
            if ds_cfg and isinstance(ds_cfg, dict):
                for k in self._ds_bindings:
                    if k in ds_cfg:
                        self._ds_bindings[k] = ds_cfg[k]
            n3ds_cfg = cfg.get("controls_3ds")
            if n3ds_cfg and isinstance(n3ds_cfg, dict):
                for k in self._n3ds_bindings:
                    if k in n3ds_cfg:
                        self._n3ds_bindings[k] = n3ds_cfg[k]
        except Exception:
            pass

    # Guarda las asignaciones en config.json, preservando otras claves existentes
    def _guardar_config(self):
        if not self._config_path:
            return
        try:
            cfg = {}
            if os.path.exists(self._config_path):
                with open(self._config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
            cfg["controls_ds"] = dict(self._ds_bindings)
            cfg["controls_3ds"] = dict(self._n3ds_bindings)
            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
        except Exception:
            pass

    # ── API pública para InputManager ──
    # Devuelven copias de los bindings para que el InputManager sepa
    # qué tecla/botón corresponde a cada acción de la consola

    @property
    def ds_bindings(self):
        return dict(self._ds_bindings)

    @property
    def n3ds_bindings(self):
        return dict(self._n3ds_bindings)
