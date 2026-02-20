import ctypes
import struct
import os
import sys

# Intentar importar PyGame para el contexto OpenGL
try:
    import pygame
    from pygame.locals import *
    
except ImportError:
    print("Error: Necesitas instalar pygame para crear el contexto OpenGL (pip install pygame)")
    sys.exit(1)
    
from OpenGL.GL import glViewport

try:
    import pyaudio
except ImportError:
    pyaudio = None

# Constantes de libretro.h
RETRO_ENVIRONMENT_GET_SYSTEM_DIRECTORY = 9
RETRO_ENVIRONMENT_SET_PIXEL_FORMAT = 10
RETRO_ENVIRONMENT_SET_INPUT_DESCRIPTORS = 11
RETRO_ENVIRONMENT_SET_HW_RENDER = 14
RETRO_ENVIRONMENT_GET_VARIABLE = 15
RETRO_ENVIRONMENT_SET_VARIABLES = 16
RETRO_ENVIRONMENT_GET_VARIABLE_UPDATE = 17
RETRO_ENVIRONMENT_GET_LOG_INTERFACE = 27
RETRO_ENVIRONMENT_GET_INPUT_DEVICE_CAPABILITIES = 24
RETRO_ENVIRONMENT_GET_SAVE_DIRECTORY = 31
RETRO_ENVIRONMENT_SET_GEOMETRY = 37
RETRO_ENVIRONMENT_SET_CORE_OPTIONS = 53
RETRO_ENVIRONMENT_SET_CORE_OPTIONS_V2 = 67
RETRO_ENVIRONMENT_GET_PREFERRED_HW_RENDER = 56
RETRO_PIXEL_FORMAT_0RGB1555 = 0
RETRO_PIXEL_FORMAT_XRGB8888 = 1
RETRO_PIXEL_FORMAT_RGB565 = 2
RETRO_DEVICE_TYPE_SHIFT = 8
RETRO_DEVICE_MASK = (1 << RETRO_DEVICE_TYPE_SHIFT) - 1
RETRO_DEVICE_JOYPAD = 1
RETRO_DEVICE_MOUSE = 2
RETRO_DEVICE_ANALOG = 5
RETRO_DEVICE_POINTER = 6
RETRO_DEVICE_ID_POINTER_X = 0
RETRO_DEVICE_ID_POINTER_Y = 1
RETRO_DEVICE_ID_POINTER_PRESSED = 2
RETRO_DEVICE_ID_ANALOG_X = 0
RETRO_DEVICE_ID_ANALOG_Y = 1
RETRO_DEVICE_ID_MOUSE_LEFT = 2

# 1. Cargar el Core
# Asegúrate de usar un core de 3DS (ej. citra_libretro)
lib = ctypes.CDLL('cores/citra_libretro.dll')

# Definir tipos basados en libretro.h
c_video_refresh_t = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint, ctypes.c_size_t)
c_environment_t = ctypes.CFUNCTYPE(ctypes.c_bool, ctypes.c_uint, ctypes.c_void_p)
c_audio_sample_t = ctypes.CFUNCTYPE(None, ctypes.c_int16, ctypes.c_int16)
c_audio_sample_batch_t = ctypes.CFUNCTYPE(ctypes.c_size_t, ctypes.POINTER(ctypes.c_int16), ctypes.c_size_t)
c_input_poll_t = ctypes.CFUNCTYPE(None)
c_input_state_t = ctypes.CFUNCTYPE(ctypes.c_int16, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint)
# Callback de log (simplificado, ignora argumentos variables)
c_log_printf_t = ctypes.CFUNCTYPE(None, ctypes.c_int, ctypes.c_char_p)
c_hw_context_reset_t = ctypes.CFUNCTYPE(None)
c_hw_get_current_framebuffer_t = ctypes.CFUNCTYPE(ctypes.c_size_t)
c_hw_get_proc_address_t = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_char_p)

# Estructura retro_game_info
class RetroGameInfo(ctypes.Structure):
    _fields_ = [
        ("path", ctypes.c_char_p),
        ("data", ctypes.c_void_p),
        ("size", ctypes.c_size_t),
        ("meta", ctypes.c_char_p),
    ]

# Estructura retro_system_info
class RetroSystemInfo(ctypes.Structure):
    _fields_ = [
        ("library_name", ctypes.c_char_p),
        ("library_version", ctypes.c_char_p),
        ("valid_extensions", ctypes.c_char_p),
        ("need_fullpath", ctypes.c_bool),
        ("block_extract", ctypes.c_bool),
    ]

# Estructuras para AV Info
class RetroGameGeometry(ctypes.Structure):
    _fields_ = [
        ("base_width", ctypes.c_uint),
        ("base_height", ctypes.c_uint),
        ("max_width", ctypes.c_uint),
        ("max_height", ctypes.c_uint),
        ("aspect_ratio", ctypes.c_float),
    ]

class RetroSystemTiming(ctypes.Structure):
    _fields_ = [("fps", ctypes.c_double), ("sample_rate", ctypes.c_double)]

class RetroSystemAVInfo(ctypes.Structure):
    _fields_ = [("geometry", RetroGameGeometry), ("timing", RetroSystemTiming)]

# Estructura para Log Callback
class RetroLogCallback(ctypes.Structure):
    _fields_ = [("log", ctypes.c_void_p)]

class RetroVariable(ctypes.Structure):
    _fields_ = [("key", ctypes.c_char_p), ("value", ctypes.c_char_p)]

class RetroHWRenderCallback(ctypes.Structure):
    _fields_ = [
        ("context_type", ctypes.c_int),
        ("context_reset", c_hw_context_reset_t),
        ("get_current_framebuffer", c_hw_get_current_framebuffer_t),
        ("get_proc_address", c_hw_get_proc_address_t),
        ("depth", ctypes.c_bool),
        ("stencil", ctypes.c_bool),
        ("bottom_left_origin", ctypes.c_bool),
        ("version_major", ctypes.c_uint),
        ("version_minor", ctypes.c_uint),
        ("cache_context", ctypes.c_bool),
        ("context_destroy", c_hw_context_reset_t),
        ("debug_context", ctypes.c_bool),
    ]


# 5. Callback: Aquí llega la imagen desde el Core
def video_refresh_callback(data, width, height, pitch):
    if data is None:
        return # Frame duplicado o nulo
    
    # Aquí es donde "Muestras la imagen"
    # data es un puntero a los bytes de la imagen.
    # Podrías usar: buffer = ctypes.string_at(data, height * pitch)
    # print(f"Recibido frame: {width}x{height}, Pitch: {pitch}")
    # ... código para pintar en pantalla con PyGame/OpenGL ...
    pass

# Callback para logs del core
def log_printf_callback(level, fmt):
    try:
        # fmt viene como bytes, lo decodificamos para leerlo
        msg = fmt.decode('utf-8', errors='replace').strip()
        print(f"[CORE LOG {level}]: {msg}")
    except:
        pass

# Cargar librería OpenGL para Windows para resolver símbolos
if os.name == 'nt':
    _gl_lib = ctypes.windll.opengl32
    _wgl_get_proc = _gl_lib.wglGetProcAddress
    _wgl_get_proc.restype = ctypes.c_void_p
    _wgl_get_proc.argtypes = [ctypes.c_char_p]

def get_current_framebuffer_callback():
    # Retornar 0 indica que renderizamos en el framebuffer por defecto de la ventana
    return 0

def get_proc_address_callback(sym):
    # Citra necesita punteros reales a funciones OpenGL
    addr = 0
    if os.name == 'nt':
        # 1. Intentar obtener extensión (wglGetProcAddress)
        addr = _wgl_get_proc(sym)
        # 2. Si falla, intentar función estándar (GetProcAddress/dlsym implícito)
        if not addr:
            try:
                addr = ctypes.cast(getattr(_gl_lib, sym.decode('utf-8')), ctypes.c_void_p).value
            except AttributeError:
                pass
    return addr if addr else 0

_hw_refs = [] # Para mantener referencias a los callbacks de HW
context_reset_cb = None # Para guardar el callback de reset del core
audio_stream = None # Stream de audio global

seen_inputs = set() # Para evitar spam en la consola
g_core_width = 0
g_core_height = 0



# Callback para environment (CRUCIAL PARA 3DS)
def environment_callback(cmd, data):
    # DEBUG: Imprimir comandos excepto el 17 (GET_VARIABLE_UPDATE) que es spam constante
    if cmd != RETRO_ENVIRONMENT_GET_VARIABLE_UPDATE:
        print(f"[ENV DEBUG] CMD Recibido: {cmd}")

    if cmd == RETRO_ENVIRONMENT_GET_SYSTEM_DIRECTORY:
        # El core pide dónde guardar sus archivos de sistema (claves, saves, etc.)
        # Debemos devolver un puntero a un string con la ruta.
        sys_dir = os.path.abspath("./system").encode('utf-8')
        if not os.path.exists("./system"):
            os.makedirs("./system")
        
        # data es const char **
        p_str = ctypes.cast(data, ctypes.POINTER(ctypes.c_char_p))
        p_str[0] = sys_dir
        print(f"Environment: System Directory -> {sys_dir}")
        return True
    
    elif cmd == RETRO_ENVIRONMENT_SET_PIXEL_FORMAT:
        # El core nos dice qué formato de pixel usará.
        # data es enum retro_pixel_format *
        p_fmt = ctypes.cast(data, ctypes.POINTER(ctypes.c_int))
        fmt = p_fmt[0]
        print(f"Environment: Set Pixel Format -> {fmt}")
        # Aceptamos el formato (normalmente XRGB8888 para 3DS)
        return True

    elif cmd == RETRO_ENVIRONMENT_GET_SAVE_DIRECTORY:
        save_dir = os.path.abspath("./saves").encode('utf-8')
        if not os.path.exists("./saves"):
            os.makedirs("./saves")
        p_str = ctypes.cast(data, ctypes.POINTER(ctypes.c_char_p))
        p_str[0] = save_dir
        # print(f"Environment: Save Directory -> {save_dir}")
        return True

    elif cmd == RETRO_ENVIRONMENT_GET_LOG_INTERFACE:
        # El core pide una función para imprimir logs
        cb_struct = ctypes.cast(data, ctypes.POINTER(RetroLogCallback))
        # Asignamos nuestro callback convertido a void*
        cb_struct.contents.log = ctypes.cast(c_log_cb, ctypes.c_void_p)
        print("[ENV] GET_LOG_INTERFACE -> Callback de log asignado")
        return True

    elif cmd == RETRO_ENVIRONMENT_GET_VARIABLE:
        var = ctypes.cast(data, ctypes.POINTER(RetroVariable)).contents
        # Devolvemos True para indicar que soportamos variables, 
        # pero dejamos value en None para usar defaults del core.
        var.value = None
        return True

    elif cmd == RETRO_ENVIRONMENT_SET_HW_RENDER:
        hw = ctypes.cast(data, ctypes.POINTER(RetroHWRenderCallback)).contents
        # Rellenamos los callbacks obligatorios
        hw.get_current_framebuffer = c_hw_get_current_framebuffer_t(get_current_framebuffer_callback)
        hw.get_proc_address = c_hw_get_proc_address_t(get_proc_address_callback)
        
        global context_reset_cb
        context_reset_cb = hw.context_reset

        # Guardamos referencias para evitar GC
        _hw_refs.append((hw.get_current_framebuffer, hw.get_proc_address))
        print("Environment: Set HW Render (Aceptado)")
        return True

    elif cmd == RETRO_ENVIRONMENT_SET_GEOMETRY:
        geo = ctypes.cast(data, ctypes.POINTER(RetroGameGeometry)).contents
    
        global g_core_width, g_core_height
        g_core_width = geo.base_width
        g_core_height = geo.base_height
        
        return True

    elif cmd == RETRO_ENVIRONMENT_GET_INPUT_DEVICE_CAPABILITIES:
        # Informar al core que soportamos Joypad, Analog, Pointer y Mouse
        caps = (1 << RETRO_DEVICE_JOYPAD) | (1 << RETRO_DEVICE_ANALOG) | (1 << RETRO_DEVICE_POINTER) | (1 << RETRO_DEVICE_MOUSE)
        p_caps = ctypes.cast(data, ctypes.POINTER(ctypes.c_uint64))
        p_caps[0] = caps
        print(f"[ENV] GET_INPUT_DEVICE_CAPABILITIES -> Reportando caps: {bin(caps)}")
        return True

    elif cmd == RETRO_ENVIRONMENT_GET_VARIABLE_UPDATE:
        # El core pregunta cada frame si las opciones han cambiado
        p_bool = ctypes.cast(data, ctypes.POINTER(ctypes.c_bool))
        p_bool[0] = False
        return True

    elif cmd == RETRO_ENVIRONMENT_GET_PREFERRED_HW_RENDER:
        # El core pregunta qué API gráfica preferimos. Devolvemos OpenGL (1).
        p_uint = ctypes.cast(data, ctypes.POINTER(ctypes.c_uint))
        p_uint[0] = 1 # RETRO_HW_CONTEXT_OPENGL
        return True

    # Aceptar configuraciones de opciones/controles para que el core no falle silenciosamente
    elif cmd in [RETRO_ENVIRONMENT_SET_INPUT_DESCRIPTORS, RETRO_ENVIRONMENT_SET_VARIABLES, RETRO_ENVIRONMENT_SET_CORE_OPTIONS, RETRO_ENVIRONMENT_SET_CORE_OPTIONS_V2]:
        return True

    print(f"[ENV] Comando NO MANEJADO: {cmd}")
    return False

def audio_sample_batch_callback(data, frames):
    global audio_stream
    if audio_stream:
        size = frames * 4
        buf = ctypes.string_at(data, size)
        # Escribir al stream de PyAudio
        audio_stream.write(buf)
    return frames

def audio_sample_callback(left, right):
    pass

def input_poll_callback():
    pygame.event.pump()

KEY_MAP = {
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

def map_axis(pos, size):
    return int((pos / size) * 2 * 0x7FFF - 0x7FFF)

touch_pressed = False
touch_x = 0
touch_y = 0

def input_state_callback(port, device, index, id):
    global seen_inputs
    global g_core_width, g_core_height
    
    # Obtener estado del mouse al inicio
    x, y = pygame.mouse.get_pos()
    buttons = pygame.mouse.get_pressed()
    is_pressed = buttons[0] # Click izquierdo

    if port == 0:
        dev_type = device & RETRO_DEVICE_MASK

        if dev_type == RETRO_DEVICE_JOYPAD:
            keys = pygame.key.get_pressed()
            if id in KEY_MAP and keys[KEY_MAP[id]]:
                return 1
        
        elif dev_type == RETRO_DEVICE_POINTER:
            # Pointer (Pantalla Táctil) - Index 0 es el primer dedo/ratón
            if index == 0:
                surface = pygame.display.get_surface()
                win_w, win_h = surface.get_size()
                
                # Calcular el área real donde se dibuja el juego (Letterboxing)
                # Usamos la resolución del core si está disponible, si no, la ventana completa
                cw = g_core_width if g_core_width > 0 else win_w
                ch = g_core_height if g_core_height > 0 else win_h
                
                # Factor de escala manteniendo aspect ratio
                scale = min(win_w / cw, win_h / ch)
                view_w = cw * scale
                view_h = ch * scale
                
                # Offsets (barras negras)
                off_x = (win_w - view_w) / 2
                off_y = (win_h - view_h) / 2

                # Coordenadas absolutas del pointer
                if id == RETRO_DEVICE_ID_POINTER_X:
                    # Restar el offset y normalizar respecto al tamaño de la vista (no de la ventana)
                    val = int(((x - off_x) / view_w) * 0xFFFF) - 0x7FFF
                    return max(-0x7FFF, min(0x7FFF, val))
                elif id == RETRO_DEVICE_ID_POINTER_Y:
                    val = int(((y - off_y) / view_h) * 0xFFFF) - 0x7FFF
                    return max(-0x7FFF, min(0x7FFF, val))
                elif id == RETRO_DEVICE_ID_POINTER_PRESSED:
                    return 1 if is_pressed else 0
        
        elif dev_type == RETRO_DEVICE_MOUSE:
            # Mouse (Ratón) - Fallback si el core prefiere esto
            if id == RETRO_DEVICE_ID_MOUSE_LEFT:
                return 1 if is_pressed else 0
            
    return 0

# Instanciar callbacks para que no sean recolectados por el GC
video_cb = c_video_refresh_t(video_refresh_callback)
env_cb = c_environment_t(environment_callback)
audio_sample_cb = c_audio_sample_t(audio_sample_callback)
audio_cb = c_audio_sample_batch_t(audio_sample_batch_callback)
input_poll_cb = c_input_poll_t(input_poll_callback)
input_state_cb = c_input_state_t(input_state_callback)
c_log_cb = c_log_printf_t(log_printf_callback)

# 2. Inicialización
lib.retro_set_environment(env_cb)
lib.retro_set_video_refresh(video_cb)
lib.retro_set_audio_sample(audio_sample_cb) # Obligatorio aunque se use batch
lib.retro_set_audio_sample_batch(audio_cb)
lib.retro_set_input_poll(input_poll_cb)
lib.retro_set_input_state(input_state_cb)

# Inicializar PyGame y Contexto OpenGL ANTES de cargar el juego
pygame.init()
pygame.display.set_mode((400, 480), OPENGL | DOUBLEBUF | RESIZABLE)

lib.retro_init()

# Configurar puerto del mando (Jugador 1 = Joypad)
lib.retro_set_controller_port_device(0, RETRO_DEVICE_JOYPAD)

# Obtener información del sistema antes de cargar
lib.retro_get_system_info.argtypes = [ctypes.POINTER(RetroSystemInfo)]
sys_info = RetroSystemInfo()
lib.retro_get_system_info(ctypes.byref(sys_info))
print(f"Core cargado: {sys_info.library_name.decode()} ({sys_info.library_version.decode()})")

# 3. Cargar Juego
rom_path = r"C:\Users\griva\Desktop\TFG\TFG\games\PokemonSol.3ds" # Ruta a tu juego
full_path = os.path.abspath(rom_path).encode('utf-8')

game_info = RetroGameInfo()
game_info.path = full_path
game_info.meta = None

# Lógica de carga según need_fullpath
if sys_info.need_fullpath:
    # El core carga el archivo por su cuenta desde el disco
    game_info.data = None
    game_info.size = 0
else:
    # Debemos leer el archivo en memoria (menos común para 3DS)
    with open(rom_path, "rb") as f:
        rom_data = f.read()
    game_info.data = ctypes.cast(ctypes.create_string_buffer(rom_data), ctypes.c_void_p)
    game_info.size = len(rom_data)

lib.retro_load_game.argtypes = [ctypes.POINTER(RetroGameInfo)]
lib.retro_load_game.restype = ctypes.c_bool
loaded = lib.retro_load_game(ctypes.byref(game_info))

if loaded:
    print("Juego cargado exitosamente.")
    
    # Asegurar que el puerto 0 usa Joypad (algunos cores resetean esto al cargar)
    lib.retro_set_controller_port_device(0, RETRO_DEVICE_JOYPAD)

    # Notificar al core que el contexto OpenGL está listo
    if context_reset_cb:
        context_reset_cb()

    # Obtener información de Video/Audio (Resolución, FPS)
    lib.retro_get_system_av_info.argtypes = [ctypes.POINTER(RetroSystemAVInfo)]
    av_info = RetroSystemAVInfo()
    lib.retro_get_system_av_info(ctypes.byref(av_info))
    
    # Guardar resolución base para los cálculos del ratón
    g_core_width = av_info.geometry.base_width
    g_core_height = av_info.geometry.base_height
    print(f"Resolución base: {av_info.geometry.base_width}x{av_info.geometry.base_height}, FPS: {av_info.timing.fps}")
    
    # Re-inicializar el mixer de audio con la frecuencia correcta del core
    sample_rate = int(av_info.timing.sample_rate)
    
    if pyaudio:
        p = pyaudio.PyAudio()
        audio_stream = p.open(format=pyaudio.paInt16, channels=2, rate=sample_rate, output=True)
        print(f"Audio inicializado con PyAudio a {sample_rate} Hz")
    else:
        print("Advertencia: PyAudio no encontrado.")

    # 4. Bucle de ejecución (simulado)
    try:
        running = True
        while running:

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    
                if event.type == pygame.MOUSEBUTTONDOWN:
                    touch_pressed = True
                    touch_x, touch_y = event.pos
                elif event.type == pygame.MOUSEBUTTONUP:
                    touch_pressed = False
                elif event.type == pygame.MOUSEMOTION and touch_pressed:
                    touch_x, touch_y = event.pos
            
            # Esto ejecutará un frame y disparará video_refresh_callback
            lib.retro_run() 
            
            # Intercambiar buffers para mostrar el frame renderizado por Citra
            pygame.display.flip()
    except KeyboardInterrupt:
        pass

    lib.retro_unload_game()

lib.retro_deinit()
