# ── Imports ──────────────────────────────────────────────────────────────────
# Qt.Key: enumeración de teclas del teclado usadas para mapear controles
# QMouseEvent, QKeyEvent: tipos de eventos de ratón/teclado de Qt (no se usan directamente aquí)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QMouseEvent, QKeyEvent
# RETRO_DEVICE_MASK: máscara (0xFF) para extraer el tipo base de dispositivo libretro
# (el core puede enviar subclases con bits extra, ej: 262 = (1<<8)|6)
from libretro.retro_definitions import RETRO_DEVICE_MASK

# ── Constantes ───────────────────────────────────────────────────────────────
# Diccionario que traduce nombres de botón (usados en la config JSON)
# a sus IDs numéricos de libretro (RETRO_DEVICE_ID_JOYPAD_*).
# Estos IDs son los que el core espera recibir en la callback input_state.
_BUTTON_ID = {
    "b": 0, "y": 1, "select": 2, "start": 3,
    "up": 4, "down": 5, "left": 6, "right": 7,
    "a": 8, "x": 9, "l": 10, "r": 11,
    "zl": 14, "zr": 15,
}

# Mapeado de teclado por defecto: Qt.Key → ID de botón libretro.
# Se usa si el usuario no ha configurado controles personalizados.
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

# Teclas por defecto para el Circle Pad (stick analógico de 3DS).
# Al pulsar estas teclas se envía el valor máximo del eje correspondiente.
_DEFAULT_ANALOG_KEYS = {
    "circle_up":    Qt.Key.Key_I,
    "circle_down":  Qt.Key.Key_K,
    "circle_left":  Qt.Key.Key_J,
    "circle_right": Qt.Key.Key_L,
}


# ── Clase principal de gestión de entrada ────────────────────────────────────
# Gestiona todo el input del emulador: teclado, gamepad (via pygame) y pantalla táctil.
# El core libretro llama a get_state() cada frame para consultar el estado de los controles.
class QtInputManager:
    def __init__(self):
        # KEY_MAP: diccionario Qt.Key (int) → ID de botón libretro (int)
        # Permite buscar rápidamente qué botón corresponde a cada tecla pulsada
        self.KEY_MAP = dict(_DEFAULT_KEY_MAP)
        # ID_TO_KEYS: diccionario inverso, ID de botón → lista de Qt.Key
        # Se usa para consultar si alguna tecla asociada a un botón está pulsada
        self.ID_TO_KEYS = {}
        self._rebuild_id_to_keys()

        # Mapeado de teclas analógicas (Circle Pad): nombre → Qt.Key (int)
        self._analog_keys = {k: int(v) for k, v in _DEFAULT_ANALOG_KEYS.items()}

        # ── Bindings de gamepad (mando físico) ──
        # Cada diccionario mapea un ID de botón libretro a la entrada del gamepad correspondiente.
        # Se configuran desde la ventana de controles y se cargan con load_bindings().
        self._gamepad_button_map = {}   # ID libretro → índice de botón del gamepad
        self._gamepad_axis_map = {}     # ID libretro → (índice_eje, dirección "+" o "-")
        self._gamepad_hat_map = {}      # ID libretro → (índice_hat, hx, hy)
        self._gamepad_analog_keys = {}  # nombre circle pad → {"type":..., "value":..., ...}

        # ── Estado actual del gamepad (actualizado externamente via pygame polling) ──
        # Estos diccionarios se actualizan cada frame desde el hilo de polling de pygame.
        self._gamepad_buttons = {}   # índice_botón → True/False (pulsado o no)
        self._gamepad_axes = {}      # índice_eje → float (-1.0 a 1.0)
        self._gamepad_hats = {}      # índice_hat → (hx, hy) donde hx/hy ∈ {-1, 0, 1}

        # ── Estado del teclado y pantalla táctil ──
        self.pressed_keys = set()      # Conjunto de Qt.Key actualmente pulsadas
        self.touch_pressed = False     # True mientras el ratón está pulsado (touch activo)
        self._touch_latched = False    # Latch: garantiza que el core detecte el toque al menos 1 frame
        self.touch_x = 0               # Coordenada X del toque en rango libretro [-0x7FFF, 0x7FFF]
        self.touch_y = 0               # Coordenada Y del toque en rango libretro [-0x7FFF, 0x7FFF]
        self.core_width = 0            # Ancho del framebuffer del core (píxeles)
        self.core_height = 0           # Alto del framebuffer del core (píxeles)
        self.aspect_ratio = 0.0        # Relación de aspecto reportada por el core

        # Geometría del viewport (actualizada cuando el widget OpenGL cambia de tamaño).
        # Define el área visible donde se renderiza el juego dentro del widget.
        self.view_x = 0                # Offset X del viewport dentro del widget
        self.view_y = 0                # Offset Y del viewport dentro del widget
        self.view_w = 1                # Ancho del viewport en píxeles
        self.view_h = 1                # Alto del viewport en píxeles

    # Reconstruir el diccionario inverso ID_TO_KEYS a partir de KEY_MAP.
    # Se llama cada vez que cambian los bindings de teclado.
    def _rebuild_id_to_keys(self):
        self.ID_TO_KEYS = {}
        for k, v in self.KEY_MAP.items():
            if v not in self.ID_TO_KEYS:
                self.ID_TO_KEYS[v] = []
            self.ID_TO_KEYS[v].append(k)

    # Carga las asignaciones de controles desde la ventana de configuración.
    # Cada binding es un diccionario con el formato:
    #   {"type": "key", "value": int}                          → tecla de teclado
    #   {"type": "gamepad_button", "value": int}                → botón de gamepad
    #   {"type": "gamepad_axis", "value": int, "direction": "+"/"-"} → eje de gamepad
    #   {"type": "gamepad_hat", "hat": int, "hx": int, "hy": int}    → hat/D-pad de gamepad
    # ds_bindings: controles de DS, n3ds_bindings: controles adicionales de 3DS.
    def load_bindings(self, ds_bindings, n3ds_bindings):
        # Diccionarios temporales para construir los nuevos mapeos.
        # Se crean vacíos y se rellenan con los bindings recibidos.
        new_key_map = {}              # Qt.Key → ID libretro (teclado)
        new_gp_button_map = {}        # ID libretro → índice botón gamepad
        new_gp_axis_map = {}          # ID libretro → (eje, dirección)
        new_gp_hat_map = {}           # ID libretro → (hat, hx, hy)
        new_analog_keys = dict(self._analog_keys)  # Copiar analógicos actuales como base
        new_gp_analog = {}            # Circle pad gamepad bindings

        # Fusionar los bindings de DS y 3DS en un solo diccionario.
        # Se aplican primero los de DS y luego los de 3DS, así los de 3DS
        # tienen prioridad si hay conflicto (ej: botones extra como ZL/ZR).
        combined = {}
        combined.update(ds_bindings)
        combined.update(n3ds_bindings)

        # Recorrer todos los bindings combinados y clasificarlos según su tipo
        for cfg_key, binding in combined.items():
            if binding is None:
                continue
            btype = binding.get("type")    # Tipo de entrada: "key", "gamepad_button", etc.
            bval = binding.get("value")    # Valor: código de tecla o índice de botón/eje

            # Los botones del Circle Pad se tratan aparte porque generan valores analógicos,
            # no digitales (on/off) como los botones normales del joypad
            if cfg_key in ("circle_up", "circle_down", "circle_left", "circle_right"):
                if btype == "key":
                    # Tecla de teclado → guardar en analog_keys
                    new_analog_keys[cfg_key] = bval
                else:
                    # Entrada de gamepad (botón/eje/hat) → guardar como binding completo
                    new_gp_analog[cfg_key] = binding
                continue

            # Para botones normales del joypad: traducir nombre → ID libretro
            lid = _BUTTON_ID.get(cfg_key)
            if lid is None:
                continue  # Nombre de botón desconocido, ignorar

            # Clasificar el binding según su tipo de entrada
            if btype == "key":
                new_key_map[bval] = lid           # Tecla → ID libretro
            elif btype == "gamepad_button":
                new_gp_button_map[lid] = bval     # ID libretro → botón de gamepad
            elif btype == "gamepad_axis":
                # Guardar eje y dirección ("+" = positivo, "-" = negativo)
                new_gp_axis_map[lid] = (bval, binding.get("direction", "+"))
            elif btype == "gamepad_hat":
                # Guardar índice de hat y dirección (hx/hy ∈ {-1, 0, 1})
                new_gp_hat_map[lid] = (binding.get("hat", 0), binding.get("hx", 0), binding.get("hy", 0))

        # Aplicar todos los nuevos mapeos y reconstruir el diccionario inverso
        self.KEY_MAP = new_key_map
        self._rebuild_id_to_keys()
        self._analog_keys = new_analog_keys
        self._gamepad_button_map = new_gp_button_map
        self._gamepad_axis_map = new_gp_axis_map
        self._gamepad_hat_map = new_gp_hat_map
        self._gamepad_analog_keys = new_gp_analog

    # Actualiza el estado del gamepad con los datos del polling de pygame.
    # Se llama cada frame desde el hilo de polling externo.
    # buttons: dict {índice_botón: bool}   → estado de cada botón (pulsado/no)
    # axes:    dict {índice_eje: float}     → valor de cada eje (-1.0 a 1.0)
    # hats:    dict {índice_hat: (hx, hy)}  → dirección del D-pad
    def update_gamepad_state(self, buttons, axes, hats=None):
        self._gamepad_buttons = buttons
        self._gamepad_axes = axes
        if hats is not None:
            self._gamepad_hats = hats

    # Actualiza las dimensiones del framebuffer del core (llamado desde environment callback)
    def update_geometry(self, width, height, aspect_ratio):
        self.core_width = width
        self.core_height = height
        self.aspect_ratio = aspect_ratio
    
    # Actualiza la geometría del viewport (posición y tamaño del área de juego dentro del widget)
    def update_viewport(self, x, y, w, h):
        self.view_x = x
        self.view_y = y
        self.view_w = w
        self.view_h = h

    # Registrar una tecla como pulsada (se llama desde el evento keyPressEvent del widget)
    def handle_key_press(self, key):
        self.pressed_keys.add(key)

    # Registrar una tecla como soltada (se llama desde el evento keyReleaseEvent del widget)
    def handle_key_release(self, key):
        if key in self.pressed_keys:
            self.pressed_keys.remove(key)

    # ── Eventos de ratón (simulan la pantalla táctil de la consola) ──
    # El ratón simula el toque en la pantalla inferior de DS/3DS.
    # Se usa un "latch" para garantizar que el core detecte el toque al menos durante 1 frame,
    # incluso si el polling ocurre entre el press y el siguiente frame.

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
            
    # Convierte las coordenadas del ratón en el widget a coordenadas libretro.
    # Proceso:
    #   1) Restar el offset del viewport para obtener posición relativa al área de juego
    #   2) Normalizar a rango [0.0, 1.0] dividiendo por el tamaño del viewport
    #   3) Clampear para evitar valores fuera del área visible
    #   4) Escalar al rango libretro [-0x7FFF, 0x7FFF] (-32767 a 32767)
    # El core (Citra/melonDS) determina internamente si el punto cae en la pantalla táctil.
    def _update_touch(self, screen_x, screen_y):
        # Paso 1: posición relativa al viewport
        rel_x = screen_x - self.view_x
        norm_x = rel_x / self.view_w if self.view_w > 0 else 0

        rel_y = screen_y - self.view_y
        norm_y = rel_y / self.view_h if self.view_h > 0 else 0

        # Paso 2: clamp a [0, 1] para no salirse del viewport
        norm_x = max(0.0, min(1.0, norm_x))
        norm_y = max(0.0, min(1.0, norm_y))

        # Paso 3: convertir a rango libretro [-0x7FFF, 0x7FFF]
        # range_size = 0xFFFE (65534) = rango total de -0x7FFF a 0x7FFF
        range_size = 0xFFFE
        min_val = -0x7FFF

        self.touch_x = int(norm_x * range_size) + min_val
        self.touch_y = int(norm_y * range_size) + min_val

    # Callback de polling de libretro. No hace nada porque el estado
    # se actualiza en tiempo real desde los eventos de Qt y pygame.
    def poll(self):
        pass

    # ── Callback principal de estado de entrada (input_state) ────────────────
    # Llamada por el core libretro cada frame para consultar el estado de un control.
    # Parámetros:
    #   port:    puerto del jugador (0 = jugador 1)
    #   device:  tipo de dispositivo (JOYPAD, ANALOG, POINTER, MOUSE)
    #   index:   sub-índice (ej: stick izquierdo/derecho para ANALOG)
    #   id_val:  ID del botón/eje específico dentro del dispositivo
    # Retorna: 1/0 para digitales, valor int para analógicos/puntero
    def get_state(self, port, device, index, id_val):
        # Constantes locales de tipos de dispositivo libretro
        RETRO_DEVICE_JOYPAD = 1     # Botones digitales (A, B, Start, D-pad...)
        RETRO_DEVICE_ANALOG = 5     # Sticks analógicos (Circle Pad, C-Stick)
        RETRO_DEVICE_POINTER = 6    # Puntero/pantalla táctil
        RETRO_DEVICE_MOUSE = 2      # Ratón (usado por Citra para touch)
        RETRO_DEVICE_ID_MOUSE_LEFT = 2     # Botón izquierdo del ratón
        RETRO_DEVICE_INDEX_ANALOG_LEFT = 0 # Stick izquierdo (Circle Pad)
        RETRO_DEVICE_ID_ANALOG_X = 0       # Eje X del stick
        RETRO_DEVICE_ID_ANALOG_Y = 1       # Eje Y del stick
        
        # Aplicar máscara 0xFF para obtener el tipo base del dispositivo.
        # El core puede enviar subclases con bits extra (ej: 262 = (1<<8)|6 = POINTER con flags)
        dev_type = device & RETRO_DEVICE_MASK

        if dev_type == RETRO_DEVICE_JOYPAD:
            # ── 1) Comprobar teclado ──
            # Buscar todas las teclas asociadas a este botón y ver si alguna está pulsada
            keys = self.ID_TO_KEYS.get(id_val, [])
            for k in keys:
                if k in self.pressed_keys:
                    return 1

            # ── 2) Comprobar botón de gamepad ──
            # Si hay un botón de gamepad mapeado a este ID, comprobar si está pulsado
            gp_btn = self._gamepad_button_map.get(id_val)
            if gp_btn is not None and self._gamepad_buttons.get(gp_btn, False):
                return 1

            # ── 3) Comprobar eje de gamepad ──
            # Permite usar ejes analógicos como botones digitales (ej: gatillos LT/RT)
            gp_axis_info = self._gamepad_axis_map.get(id_val)
            if gp_axis_info is not None:
                axis_idx, direction = gp_axis_info
                axis_val = self._gamepad_axes.get(axis_idx, 0.0)
                # Los triggers (ejes 4 y 5) tienen reposo en -1.0 y máximo en +1.0,
                # por eso usan un umbral más bajo (0.3) que los sticks normales (0.5)
                is_trigger = axis_idx in (4, 5)
                if is_trigger:
                    if direction == "+" and axis_val > 0.3:
                        return 1
                else:
                    if direction == "+" and axis_val > 0.5:
                        return 1
                    if direction == "-" and axis_val < -0.5:
                        return 1

            # ── 4) Comprobar hat/D-pad de gamepad ──
            # Los hats devuelven (hx, hy) donde cada valor es -1, 0 o 1
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
            # ── Sticks analógicos (Circle Pad / C-Stick) ──
            # index 0 = stick izquierdo (Circle Pad en 3DS)
            # index 1 = stick derecho (C-Stick en New 3DS)
            # id_val 0 = eje X, id_val 1 = eje Y
            # Devuelve valor en rango [-32768, 32767] (0 = centrado)
            if index == RETRO_DEVICE_INDEX_ANALOG_LEFT:
                val = 0
                if id_val == RETRO_DEVICE_ID_ANALOG_X:
                    # ── Eje X: derecha (+32767) / izquierda (-32768) ──
                    # Primero comprobar teclado: cada tecla aporta el valor máximo
                    right_key = self._analog_keys.get("circle_right")
                    left_key = self._analog_keys.get("circle_left")
                    if right_key and right_key in self.pressed_keys:
                        val += 32767    # Máximo positivo (derecha)
                    if left_key and left_key in self.pressed_keys:
                        val -= 32768    # Máximo negativo (izquierda)
                    # Luego comprobar gamepad: se suman ambas direcciones para combinar entradas
                    # direction_mult: 1 = positivo (derecha), -1 = negativo (izquierda)
                    for name, direction_mult in [("circle_right", 1), ("circle_left", -1)]:
                        gp = self._gamepad_analog_keys.get(name)
                        if gp:
                            # Botón digital del gamepad → valor máximo en esa dirección
                            if gp["type"] == "gamepad_button" and self._gamepad_buttons.get(gp["value"], False):
                                val += 32767 * direction_mult
                            elif gp["type"] == "gamepad_axis":
                                # Eje analógico → usar el valor proporcional del eje
                                # Umbral de 0.15 (zona muerta) para ignorar ruido del stick
                                ax = self._gamepad_axes.get(gp["value"], 0.0)
                                if gp.get("direction", "+") == "+":
                                    if ax > 0.15:
                                        val += int(ax * 32767)
                                else:
                                    if ax < -0.15:
                                        val += int(ax * 32768)
                            elif gp["type"] == "gamepad_hat":
                                # Hat/D-pad → valor máximo en esa dirección
                                hat_val = self._gamepad_hats.get(gp.get("hat", 0), (0, 0))
                                hx = gp.get("hx", 0)
                                if hx != 0 and hat_val[0] == hx:
                                    val += 32767 * direction_mult
                elif id_val == RETRO_DEVICE_ID_ANALOG_Y:
                    # ── Eje Y: abajo (+32767) / arriba (-32768) ──
                    # Misma lógica que el eje X pero con las teclas de arriba/abajo
                    down_key = self._analog_keys.get("circle_down")
                    up_key = self._analog_keys.get("circle_up")
                    if down_key and down_key in self.pressed_keys:
                        val += 32767    # Máximo positivo (abajo)
                    if up_key and up_key in self.pressed_keys:
                        val -= 32768    # Máximo negativo (arriba)
                    # Comprobar gamepad en ambas direcciones del eje Y
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
                # Clampear el resultado final al rango válido de libretro
                return max(-32768, min(32767, val))

        elif dev_type == RETRO_DEVICE_POINTER:
            # ── Pantalla táctil (dispositivo POINTER) ──
            # Usado por melonDS para la pantalla táctil de DS
            if id_val == 0:     # Coordenada X del toque
                return self.touch_x
            elif id_val == 1:   # Coordenada Y del toque
                return self.touch_y
            elif id_val == 2:   # ¿Está tocando? (1 = sí, 0 = no)
                # Usar latch para garantizar al menos 1 frame de detección
                pressed = self.touch_pressed or self._touch_latched
                self._touch_latched = False  # Consumir el latch después de leerlo
                return 1 if pressed else 0
            
        elif dev_type == RETRO_DEVICE_MOUSE:
            # ── Ratón (dispositivo MOUSE) ──
            # Usado por el core de Citra para simular la pantalla táctil de 3DS
            # (Citra usa MOUSE en lugar de POINTER para la detección táctil)
            if id_val == RETRO_DEVICE_ID_MOUSE_LEFT:
                pressed = self.touch_pressed or self._touch_latched
                self._touch_latched = False  # Consumir latch
                return 1 if pressed else 0

        return 0
