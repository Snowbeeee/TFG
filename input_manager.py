import pygame
from pygame.locals import *
from retro_definitions import *

class InputManager:
    def __init__(self):
        self.KEY_MAP = {
            0: K_z,      # B
            1: K_a,      # Y
            2: K_RSHIFT, # SELECT
            3: K_RETURN, # START
            4: K_UP,     # UP
            5: K_DOWN,   # DOWN
            6: K_LEFT,   # LEFT
            7: K_RIGHT,  # RIGHT
            8: K_x,      # A
            9: K_s,      # X
            10: K_q,     # L
            11: K_w,     # R
        }
        self.touch_pressed = False
        self.touch_x = 0
        self.touch_y = 0
        self.core_width = 0
        self.core_height = 0
        self.seen_inputs = set()

    def update_geometry(self, width, height, aspect_ratio):
        self.core_width = width
        self.core_height = height
        self.aspect_ratio = aspect_ratio

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.touch_pressed = True
            self.touch_x, self.touch_y = event.pos
        elif event.type == pygame.MOUSEBUTTONUP:
            self.touch_pressed = False
        elif event.type == pygame.MOUSEMOTION and self.touch_pressed:
            self.touch_x, self.touch_y = event.pos

    def poll(self):
        pygame.event.pump()

    def get_state(self, port, device, index, id_val):
        # Obtener estado del mouse al inicio
        x, y = pygame.mouse.get_pos()
        buttons = pygame.mouse.get_pressed()
        is_pressed = buttons[0] # Click izquierdo

        if port == 0:
            dev_type = device & RETRO_DEVICE_MASK

            if dev_type == RETRO_DEVICE_JOYPAD:
                keys = pygame.key.get_pressed()
                if id_val in self.KEY_MAP and keys[self.KEY_MAP[id_val]]:
                    return 1
            
            elif dev_type == RETRO_DEVICE_POINTER:
                # Pointer (Pantalla Táctil) - Index 0 es el primer dedo/ratón
                if index == 0:
                    win_w, win_h = pygame.display.get_window_size()
                    
                    # Calcular el área real donde se dibuja el juego (Letterboxing)
                    # Usamos la resolución del core si está disponible, si no, la ventana completa
                    
                    if self.aspect_ratio > 0:
                        target_aspect = self.aspect_ratio
                    else:
                        target_aspect = self.core_width / self.core_height if self.core_height > 0 else 1.0

                    window_aspect = win_w / win_h if win_h > 0 else 1.0
                    
                    if window_aspect > target_aspect:
                        # Ventana más ancha que el juego (barras laterales)
                        view_h = win_h
                        view_w = win_h * target_aspect
                    else:
                        # Ventana más alta que el juego (barras arriba/abajo)
                        view_w = win_w
                        view_h = win_w / target_aspect
                    
                    # Offsets (barras negras)
                    off_x = (win_w - view_w) / 2
                    off_y = (win_h - view_h) / 2

                    # Coordenadas absolutas del pointer
                    # Rango Libretro: [-0x8000, 0x7fff] (-32768 a 32767)
                    if id_val == RETRO_DEVICE_ID_POINTER_X:
                        if view_w <= 0: return 0
                        # Escalar coord x al viewport
                        norm_x = (x - off_x) / view_w
                        val = int(norm_x * 65535) - 32768
                        res = max(-32768, min(32767, val))
                        return res
                        
                    elif id_val == RETRO_DEVICE_ID_POINTER_Y:
                        if view_h <= 0: return 0
                        norm_y = (y - off_y) / view_h
                        val = int(norm_y * 65535) - 32768
                        res = max(-32768, min(32767, val))
                        return res
                        
                    elif id_val == RETRO_DEVICE_ID_POINTER_PRESSED:
                        return 1 if is_pressed else 0
            
            elif dev_type == RETRO_DEVICE_MOUSE:
                # Mouse (Ratón) - Fallback si el core prefiere esto
                if id_val == RETRO_DEVICE_ID_MOUSE_LEFT:
                    return 1 if is_pressed else 0
                
        return 0
