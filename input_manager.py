from PyQt6.QtCore import Qt
from PyQt6.QtGui import QMouseEvent, QKeyEvent
from retro_definitions import RETRO_DEVICE_MASK

class QtInputManager:
    def __init__(self):
        # Mapeo de teclas de Qt a ids de botones de Libretro
        # 0: B, 1: Y, 2: SELECT, 3: START, 4: UP, 5: DOWN, 6: LEFT, 7: RIGHT, 8: A, 9: X, 10: L, 11: R
        self.KEY_MAP = {
            Qt.Key.Key_Z: 0,      # B
            Qt.Key.Key_A: 1,      # Y
            Qt.Key.Key_Shift: 2,  # SELECT (Right Shift)
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
        # Invert map for faster lookup if needed, but here we look up by id_val so we need id -> key(s)
        self.ID_TO_KEYS = {}
        for k, v in self.KEY_MAP.items():
            if v not in self.ID_TO_KEYS:
                self.ID_TO_KEYS[v] = []
            self.ID_TO_KEYS[v].append(k)

        self.pressed_keys = set()
        self.touch_pressed = False
        self._touch_latched = False  # Latch para que un click rápido no se pierda entre frames
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
            keys = self.ID_TO_KEYS.get(id_val, [])
            for k in keys:
                if k in self.pressed_keys:
                    return 1
            return 0
        
        elif dev_type == RETRO_DEVICE_ANALOG:
            # Circle Pad / Analog Sticks
            # index: 0 = Left Stick (Circle Pad), 1 = Right Stick (C-Stick)
            # id_val: 0 = X Axis, 1 = Y Axis
            if index == RETRO_DEVICE_INDEX_ANALOG_LEFT:
                val = 0
                if id_val == RETRO_DEVICE_ID_ANALOG_X:
                    if Qt.Key.Key_Right in self.pressed_keys or Qt.Key.Key_L in self.pressed_keys:
                        val += 32767
                    if Qt.Key.Key_Left in self.pressed_keys or Qt.Key.Key_J in self.pressed_keys:
                        val -= 32768
                elif id_val == RETRO_DEVICE_ID_ANALOG_Y:
                    if Qt.Key.Key_Down in self.pressed_keys or Qt.Key.Key_K in self.pressed_keys:
                        val += 32767
                    if Qt.Key.Key_Up in self.pressed_keys or Qt.Key.Key_I in self.pressed_keys:
                        val -= 32768
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
