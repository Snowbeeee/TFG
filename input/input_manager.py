from PyQt6.QtCore import Qt
from PyQt6.QtGui import QMouseEvent, QKeyEvent
from libretro.retro_definitions import RETRO_DEVICE_MASK

# Mapping de clave config → id libretro para joypad
_BUTTON_ID = {
    "b": 0, "y": 1, "select": 2, "start": 3,
    "up": 4, "down": 5, "left": 6, "right": 7,
    "a": 8, "x": 9, "l": 10, "r": 11,
    "zl": 14, "zr": 15,
}

# Defaults usados si no se ha cargado ningún binding
_DEFAULT_KEY_MAP = {
    Qt.Key.Key_Z: 0,      # B
    Qt.Key.Key_A: 1,      # Y
    Qt.Key.Key_Shift: 2,  # SELECT
    Qt.Key.Key_Return: 3, # START
    Qt.Key.Key_Up: 4,     # UP
    Qt.Key.Key_Down: 5,   # DOWN
    Qt.Key.Key_Left: 6,   # LEFT
    Qt.Key.Key_Right: 7,  # RIGHT
    Qt.Key.Key_X: 8,      # A
    Qt.Key.Key_S: 9,      # X
    Qt.Key.Key_Q: 10,     # L
    Qt.Key.Key_W: 11,     # R
}

# Teclas por defecto para el Circle Pad (3DS analog)
_DEFAULT_ANALOG_KEYS = {
    "circle_up":    Qt.Key.Key_I,
    "circle_down":  Qt.Key.Key_K,
    "circle_left":  Qt.Key.Key_J,
    "circle_right": Qt.Key.Key_L,
}


class QtInputManager:
    def __init__(self):
        # KEY_MAP: Qt key (int) → libretro button id
        self.KEY_MAP = dict(_DEFAULT_KEY_MAP)
        # Inverse: button id → list of Qt keys
        self.ID_TO_KEYS = {}
        self._rebuild_id_to_keys()

        # Analog key mapping: name → Qt key (int)
        self._analog_keys = {k: int(v) for k, v in _DEFAULT_ANALOG_KEYS.items()}

        # Gamepad button bindings: libretro button id → gamepad button index
        self._gamepad_button_map = {}   # id → gp_btn
        # Gamepad axis bindings: libretro button id → (axis_index, direction "+"/"-")
        self._gamepad_axis_map = {}     # id → (axis, dir)
        # Gamepad hat bindings: libretro button id → (hat_index, hx, hy)
        self._gamepad_hat_map = {}      # id → (hat, hx, hy)
        # Gamepad analog bindings (circle pad)
        self._gamepad_analog_keys = {}  # name → {"type":..., "value":..., ...}

        # Gamepad state (actualizado externamente via pygame polling)
        self._gamepad_buttons = {}   # gp_btn_index → bool
        self._gamepad_axes = {}      # axis_index → float
        self._gamepad_hats = {}      # hat_index → (hx, hy)

        self.pressed_keys = set()
        self.touch_pressed = False
        self._touch_latched = False
        self.touch_x = 0
        self.touch_y = 0
        self.core_width = 0
        self.core_height = 0
        self.aspect_ratio = 0.0

        # Viewport geometry (set by widget resize)
        self.view_x = 0
        self.view_y = 0
        self.view_w = 1
        self.view_h = 1

    def _rebuild_id_to_keys(self):
        self.ID_TO_KEYS = {}
        for k, v in self.KEY_MAP.items():
            if v not in self.ID_TO_KEYS:
                self.ID_TO_KEYS[v] = []
            self.ID_TO_KEYS[v].append(k)

    def load_bindings(self, ds_bindings, n3ds_bindings):
        """Carga las asignaciones de controles desde la página de controles.
        Cada binding es un dict: {"type": "key", "value": int}
        o {"type": "gamepad_button", "value": int}
        o {"type": "gamepad_axis", "value": int, "direction": "+"/"-"}
        """
        new_key_map = {}
        new_gp_button_map = {}
        new_gp_axis_map = {}
        new_gp_hat_map = {}
        new_analog_keys = dict(self._analog_keys)
        new_gp_analog = {}

        # Fusionar DS + 3DS (3DS tiene prioridad por tener más botones)
        combined = {}
        combined.update(ds_bindings)
        combined.update(n3ds_bindings)

        for cfg_key, binding in combined.items():
            if binding is None:
                continue
            btype = binding.get("type")
            bval = binding.get("value")

            # Botón analógico (circle pad)
            if cfg_key in ("circle_up", "circle_down", "circle_left", "circle_right"):
                if btype == "key":
                    new_analog_keys[cfg_key] = bval
                else:
                    new_gp_analog[cfg_key] = binding
                continue

            # Botón joypad normal
            lid = _BUTTON_ID.get(cfg_key)
            if lid is None:
                continue

            if btype == "key":
                new_key_map[bval] = lid
            elif btype == "gamepad_button":
                new_gp_button_map[lid] = bval
            elif btype == "gamepad_axis":
                new_gp_axis_map[lid] = (bval, binding.get("direction", "+"))
            elif btype == "gamepad_hat":
                new_gp_hat_map[lid] = (binding.get("hat", 0), binding.get("hx", 0), binding.get("hy", 0))

        self.KEY_MAP = new_key_map
        self._rebuild_id_to_keys()
        self._analog_keys = new_analog_keys
        self._gamepad_button_map = new_gp_button_map
        self._gamepad_axis_map = new_gp_axis_map
        self._gamepad_hat_map = new_gp_hat_map
        self._gamepad_analog_keys = new_gp_analog

    def update_gamepad_state(self, buttons, axes, hats=None):
        """Actualiza el estado del gamepad (llamado desde el polling externo).
        buttons: dict {index: bool}
        axes: dict {index: float}
        hats: dict {index: (hx, hy)}
        """
        self._gamepad_buttons = buttons
        self._gamepad_axes = axes
        if hats is not None:
            self._gamepad_hats = hats

    def update_geometry(self, width, height, aspect_ratio):
        self.core_width = width
        self.core_height = height
        self.aspect_ratio = aspect_ratio
    
    def update_viewport(self, x, y, w, h):
        self.view_x = x
        self.view_y = y
        self.view_w = w
        self.view_h = h

    def handle_key_press(self, key):
        self.pressed_keys.add(key)

    def handle_key_release(self, key):
        if key in self.pressed_keys:
            self.pressed_keys.remove(key)

    def handle_mouse_press(self, x, y):
        self.touch_pressed = True
        self._touch_latched = True  # Latchar para que el core lo vea al menos 1 frame
        self._update_touch(x, y)

    def handle_mouse_release(self, x, y):
        self.touch_pressed = False
        self._touch_latched = False  # Limpiar latch al soltar
        self._update_touch(x, y)

    def handle_mouse_move(self, x, y):
        self._update_touch(x, y)
            
    def _update_touch(self, screen_x, screen_y):
        # Mapear coordenadas del widget al rango libretro [-0x7FFF, 0x7FFF]
        # Las coordenadas deben cubrir el FRAME COMPLETO (ambas pantallas).
        # Citra internamente determina si el punto cae en la pantalla táctil.
        
        rel_x = screen_x - self.view_x
        norm_x = rel_x / self.view_w if self.view_w > 0 else 0

        rel_y = screen_y - self.view_y
        norm_y = rel_y / self.view_h if self.view_h > 0 else 0

        # Clamp a [0, 1]
        norm_x = max(0.0, min(1.0, norm_x))
        norm_y = max(0.0, min(1.0, norm_y))

        # Convertir a rango libretro [-0x7FFF, 0x7FFF]
        range_size = 0xFFFE  # 65534
        min_val = -0x7FFF

        self.touch_x = int(norm_x * range_size) + min_val
        self.touch_y = int(norm_y * range_size) + min_val

    def poll(self):
        pass

    def get_state(self, port, device, index, id_val):
        RETRO_DEVICE_JOYPAD = 1
        RETRO_DEVICE_ANALOG = 5
        RETRO_DEVICE_POINTER = 6
        RETRO_DEVICE_MOUSE = 2
        RETRO_DEVICE_ID_MOUSE_LEFT = 2
        RETRO_DEVICE_INDEX_ANALOG_LEFT = 0
        RETRO_DEVICE_ID_ANALOG_X = 0
        RETRO_DEVICE_ID_ANALOG_Y = 1
        
        # Aplicar máscara para obtener el tipo base del dispositivo
        # El core puede enviar subclases (ej: 262 = (1<<8)|6) 
        dev_type = device & RETRO_DEVICE_MASK

        if dev_type == RETRO_DEVICE_JOYPAD:
            # Check keyboard
            keys = self.ID_TO_KEYS.get(id_val, [])
            for k in keys:
                if k in self.pressed_keys:
                    return 1
            # Check gamepad button binding
            gp_btn = self._gamepad_button_map.get(id_val)
            if gp_btn is not None and self._gamepad_buttons.get(gp_btn, False):
                return 1
            # Check gamepad axis binding
            gp_axis_info = self._gamepad_axis_map.get(id_val)
            if gp_axis_info is not None:
                axis_idx, direction = gp_axis_info
                axis_val = self._gamepad_axes.get(axis_idx, 0.0)
                # Triggers (axes 4,5): reposo en -1.0, pulsado hacia +1.0
                is_trigger = axis_idx in (4, 5)
                if is_trigger:
                    if direction == "+" and axis_val > 0.3:
                        return 1
                else:
                    if direction == "+" and axis_val > 0.5:
                        return 1
                    if direction == "-" and axis_val < -0.5:
                        return 1
            # Check gamepad hat binding (D-pad)
            gp_hat_info = self._gamepad_hat_map.get(id_val)
            if gp_hat_info is not None:
                hat_idx, hx, hy = gp_hat_info
                current_hat = self._gamepad_hats.get(hat_idx, (0, 0))
                if hx != 0 and current_hat[0] == hx:
                    return 1
                if hy != 0 and current_hat[1] == hy:
                    return 1
            return 0
        
        elif dev_type == RETRO_DEVICE_ANALOG:
            # Circle Pad / Analog Sticks
            # index: 0 = Left Stick (Circle Pad), 1 = Right Stick (C-Stick)
            # id_val: 0 = X Axis, 1 = Y Axis
            if index == RETRO_DEVICE_INDEX_ANALOG_LEFT:
                val = 0
                if id_val == RETRO_DEVICE_ID_ANALOG_X:
                    # Keyboard
                    right_key = self._analog_keys.get("circle_right")
                    left_key = self._analog_keys.get("circle_left")
                    if right_key and right_key in self.pressed_keys:
                        val += 32767
                    if left_key and left_key in self.pressed_keys:
                        val -= 32768
                    # Gamepad analog bindings
                    for name, direction_mult in [("circle_right", 1), ("circle_left", -1)]:
                        gp = self._gamepad_analog_keys.get(name)
                        if gp:
                            if gp["type"] == "gamepad_button" and self._gamepad_buttons.get(gp["value"], False):
                                val += 32767 * direction_mult
                            elif gp["type"] == "gamepad_axis":
                                ax = self._gamepad_axes.get(gp["value"], 0.0)
                                if gp.get("direction", "+") == "+":
                                    if ax > 0.15:
                                        val += int(ax * 32767)
                                else:
                                    if ax < -0.15:
                                        val += int(ax * 32768)
                            elif gp["type"] == "gamepad_hat":
                                hat_val = self._gamepad_hats.get(gp.get("hat", 0), (0, 0))
                                hx = gp.get("hx", 0)
                                if hx != 0 and hat_val[0] == hx:
                                    val += 32767 * direction_mult
                elif id_val == RETRO_DEVICE_ID_ANALOG_Y:
                    # Keyboard
                    down_key = self._analog_keys.get("circle_down")
                    up_key = self._analog_keys.get("circle_up")
                    if down_key and down_key in self.pressed_keys:
                        val += 32767
                    if up_key and up_key in self.pressed_keys:
                        val -= 32768
                    # Gamepad analog bindings
                    for name, direction_mult in [("circle_down", 1), ("circle_up", -1)]:
                        gp = self._gamepad_analog_keys.get(name)
                        if gp:
                            if gp["type"] == "gamepad_button" and self._gamepad_buttons.get(gp["value"], False):
                                val += 32767 * direction_mult
                            elif gp["type"] == "gamepad_axis":
                                ax = self._gamepad_axes.get(gp["value"], 0.0)
                                if gp.get("direction", "+") == "+":
                                    if ax > 0.15:
                                        val += int(ax * 32767)
                                else:
                                    if ax < -0.15:
                                        val += int(ax * 32768)
                            elif gp["type"] == "gamepad_hat":
                                hat_val = self._gamepad_hats.get(gp.get("hat", 0), (0, 0))
                                hy = gp.get("hy", 0)
                                if hy != 0 and hat_val[1] == hy:
                                    val += 32767 * direction_mult
                return max(-32768, min(32767, val))

        elif dev_type == RETRO_DEVICE_POINTER:
            if id_val == 0: # X
                return self.touch_x
            elif id_val == 1: # Y
                return self.touch_y
            elif id_val == 2: # Pressed
                pressed = self.touch_pressed or self._touch_latched
                self._touch_latched = False  # Consumir el latch
                return 1 if pressed else 0
            
        elif dev_type == RETRO_DEVICE_MOUSE:
            if id_val == RETRO_DEVICE_ID_MOUSE_LEFT:
                pressed = self.touch_pressed or self._touch_latched
                self._touch_latched = False  # Consumir latch (el core de Citra usa MOUSE, no POINTER)
                return 1 if pressed else 0

        return 0
