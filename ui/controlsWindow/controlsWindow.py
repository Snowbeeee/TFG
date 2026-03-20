import os
import json
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from ui.controlsWindow.controlsWindowUI import ControlsWindowUI

# Nombre legible para teclas de Qt
_QT_KEY_NAMES = {v: k.replace("Key_", "") for k, v in vars(Qt.Key).items() if k.startswith("Key_")}

# Nombre legible para botones de gamepad (SDL‐style usados por QGamepad / joystick)
_GAMEPAD_BUTTON_NAMES = {
    0: "GP A", 1: "GP B", 2: "GP X", 3: "GP Y",
    4: "GP Back", 5: "GP Guide", 6: "GP Start",
    7: "GP L3", 8: "GP R3",
    9: "GP LB", 10: "GP RB",
    11: "GP Up", 12: "GP Down", 13: "GP Left", 14: "GP Right",
}

_GAMEPAD_AXIS_NAMES = {
    0: "GP LStick X", 1: "GP LStick Y",
    2: "GP RStick X", 3: "GP RStick Y",
    4: "GP LTrigger", 5: "GP RTrigger",
}

_GAMEPAD_HAT_NAMES = {
    (0, 1): "GP DPad Up", (0, -1): "GP DPad Down",
    (-1, 0): "GP DPad Left", (1, 0): "GP DPad Right",
}

# Valores por defecto: tecla Qt (int) para cada botón
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


def _friendly_name(binding):
    """Devuelve un nombre legible para una asignación.
    binding es un dict: {"type": "key", "value": int}  o  {"type": "gamepad_button", ...}
    """
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


class ControlsWindow(QWidget):
    """Página de asignación de controles para DS y 3DS."""

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
        self._rescan_timer = None
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

    def set_config_path(self, path):
        """Establece la ruta del archivo config.json y carga los controles."""
        self._config_path = path
        self._cargar_config()
        self._refresh_all_labels()

    # ── Defaults ──

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

    # ── Binding flow ──

    def _start_binding(self, console, key, btn):
        """Inicia la captura de una tecla/botón para asignar."""
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

    def _finish_binding(self, binding):
        """Completa la asignación con el binding dado."""
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

    def _cancel_binding(self):
        """Cancela la captura sin cambiar nada."""
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

    # ── Conflict detection ──

    def _bindings_equal(self, b1, b2):
        """Comprueba si dos bindings representan la misma entrada."""
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

    def _remove_conflicts(self, console, key, binding):
        """Si el binding ya está asignado a otro botón de la misma consola, lo desasigna."""
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

    # ── Keyboard capture ──

    def keyPressEvent(self, event):
        if self._waiting_for_input:
            key = event.key()
            if key == Qt.Key.Key_Escape:
                self._cancel_binding()
                return
            self._finish_binding({"type": "key", "value": key})
            return
        super().keyPressEvent(event)

    # ── Gamepad support (pygame-based polling) ──

    def _init_gamepad(self):
        """Intenta inicializar pygame.joystick para leer gamepads."""
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

        # Timer para re-escanear gamepads cada 3s (hot-plug)
        if self._rescan_timer is None:
            self._rescan_timer = QTimer(self)
            self._rescan_timer.setInterval(3000)
            self._rescan_timer.timeout.connect(self._rescan_gamepad)
        self._rescan_timer.start()

    def _rescan_gamepad(self):
        """Re-escanea gamepads solo si no hay ninguno conectado."""
        if self._gamepad is not None:
            # Ya tenemos uno, verificar que sigue vivo
            try:
                import pygame
                pygame.event.pump()
                self._gamepad.get_init()
            except Exception:
                self._gamepad = None
            return
        # No hay gamepad, intentar detectar uno nuevo
        try:
            import pygame
            pygame.joystick.quit()
            pygame.joystick.init()
            if pygame.joystick.get_count() > 0:
                self._gamepad = pygame.joystick.Joystick(0)
                self._gamepad.init()
        except Exception:
            pass

    def _snapshot_gamepad(self):
        """Guarda el estado actual del gamepad para detectar cambios."""
        self._prev_gamepad_buttons = {}
        self._prev_gamepad_axes = {}
        self._prev_gamepad_hats = {}
        if not self._gamepad:
            return
        try:
            import pygame
            pygame.event.pump()
            for i in range(self._gamepad.get_numbuttons()):
                self._prev_gamepad_buttons[i] = self._gamepad.get_button(i)
            for i in range(self._gamepad.get_numaxes()):
                self._prev_gamepad_axes[i] = self._gamepad.get_axis(i)
            for i in range(self._gamepad.get_numhats()):
                self._prev_gamepad_hats[i] = self._gamepad.get_hat(i)
        except Exception:
            pass

    def _poll_gamepad(self):
        """Comprueba si se ha pulsado un botón o movido un eje del gamepad."""
        if not self._waiting_for_input or not self._gamepad:
            return
        try:
            import pygame
            pygame.event.pump()

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

    def showEvent(self, event):
        super().showEvent(event)
        # Re-escanear por si se conectó un mando mientras no estábamos visibles
        self._rescan_gamepad()
        if self._gamepad_timer:
            self._gamepad_timer.start()
        if self._rescan_timer:
            self._rescan_timer.start()

    def hideEvent(self, event):
        super().hideEvent(event)
        if self._gamepad_timer:
            self._gamepad_timer.stop()
        if self._rescan_timer:
            self._rescan_timer.stop()
        if self._waiting_for_input:
            self._cancel_binding()

    # ── Persistencia ──

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

    @property
    def ds_bindings(self):
        return dict(self._ds_bindings)

    @property
    def n3ds_bindings(self):
        return dict(self._n3ds_bindings)
