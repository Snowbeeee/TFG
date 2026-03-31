# ── Imports ──────────────────────────────────────────────────────────
# ctypes: permite definir tipos de C (structs, callbacks, punteros) en Python.
# Se usa para interactuar con la DLL del core libretro.
import ctypes

# ══════════════════════════════════════════════════════════════════════
# Constantes de la API libretro (definidas en libretro.h).
# El core llama a environment_callback(cmd, data) con estos IDs
# para solicitar información o configurar el frontend.
# ══════════════════════════════════════════════════════════════════════

# ── Environment callbacks ────────────────────────────────────────────

# Obtiene la ruta del directorio de sistema (BIOS, firmware, etc.).
# El core lo usa para cargar archivos necesarios para la emulación.
RETRO_ENVIRONMENT_GET_SYSTEM_DIRECTORY = 9

# Establece el formato de píxel que el core usará para renderizar.
# Debe llamarse en retro_load_game(). Por defecto es 0RGB1555 (obsoleto).
RETRO_ENVIRONMENT_SET_PIXEL_FORMAT = 10

# Envía al frontend una lista de descriptores de los controles del core.
# El frontend puede mostrar estos nombres al usuario en su configuración.
RETRO_ENVIRONMENT_SET_INPUT_DESCRIPTORS = 11

# Solicita al frontend que active un contexto de renderizado por hardware (OpenGL, Vulkan, etc.).
# Si tiene éxito, el core puede renderizar directamente con la GPU.
# Debe llamarse en retro_load_game().
RETRO_ENVIRONMENT_SET_HW_RENDER = 14

# Obtiene el valor actual de una opción del core (retro_variable).
# El core usa esto para leer las opciones que configuró previamente.
RETRO_ENVIRONMENT_GET_VARIABLE = 15

# Notifica al frontend las opciones disponibles del core (versión 0, obsoleta).
# Cada opción es un par clave-valor con los posibles valores separados por '|'.
# Preferir SET_CORE_OPTIONS_V2 para código nuevo.
RETRO_ENVIRONMENT_SET_VARIABLES = 16

# Consulta si alguna opción del core fue modificada por el usuario desde la última lectura.
# El core suele llamarlo cada frame para detectar cambios en la configuración.
RETRO_ENVIRONMENT_GET_VARIABLE_UPDATE = 17

# Obtiene una interfaz de logging multiplataforma del frontend.
# Permite al core imprimir mensajes de depuración de forma portable.
RETRO_ENVIRONMENT_GET_LOG_INTERFACE = 27

# Obtiene un bitmask con los tipos de dispositivo de entrada soportados.
# Cada bit corresponde a un RETRO_DEVICE_* (ej: bit 1 = JOYPAD, bit 2 = MOUSE).
RETRO_ENVIRONMENT_GET_INPUT_DEVICE_CAPABILITIES = 24

# Obtiene la ruta del directorio de guardado (saves, SRAM, etc.).
# Separado del directorio de sistema para datos específicos del juego.
RETRO_ENVIRONMENT_GET_SAVE_DIRECTORY = 31

# Cambia los parámetros de audio/vídeo en tiempo de ejecución.
# Puede causar reinicialización completa del driver de vídeo/audio.
# Solo usar si cambian max_width/max_height. Para cambios menores, usar SET_GEOMETRY.
RETRO_ENVIRONMENT_SET_SYSTEM_AV_INFO = 32

# Redimensiona el viewport sin reinicializar el driver de vídeo.
# Útil para cambios dinámicos de resolución o layout de pantallas (ej: DS top/bottom).
RETRO_ENVIRONMENT_SET_GEOMETRY = 37

# Define las opciones del core (versión 1, obsoleta). Soporta más metadatos que SET_VARIABLES
# pero sin categorías. Preferir SET_CORE_OPTIONS_V2.
RETRO_ENVIRONMENT_SET_CORE_OPTIONS = 53

# Define las opciones del core (versión 2, actual).
# Soporta categorías, descripciones detalladas e internacionalización.
# El core debe verificar que GET_CORE_OPTIONS_VERSION devuelve >= 2 antes de usarlo.
RETRO_ENVIRONMENT_SET_CORE_OPTIONS_V2 = 67

# Consulta la versión de la API de opciones soportada por el frontend (0, 1 o 2).
# El core decide qué environment call usar según este valor.
RETRO_ENVIRONMENT_GET_CORE_OPTIONS_VERSION = 52

# Consulta la API de renderizado preferida por el frontend (OpenGL, Vulkan, etc.).
# El core usa esta info para decidir qué API solicitar con SET_HW_RENDER.
RETRO_ENVIRONMENT_GET_PREFERRED_HW_RENDER = 56

# Obtiene el idioma configurado en el frontend (retro_language).
# El core puede usarlo para localizar su interfaz o configurar el firmware emulado.
RETRO_ENVIRONMENT_GET_LANGUAGE = 39

# ── Idioma ───────────────────────────────────────────────────────────
# Valor de retro_language para español. Se envía al core cuando pide GET_LANGUAGE.
RETRO_LANGUAGE_SPANISH = 3

# ── Tipos de memoria ────────────────────────────────────────────────
# IDs para retro_get_memory_data() / retro_get_memory_size().
# Permiten al frontend acceder a regiones de memoria del sistema emulado.

# SRAM del cartucho (Save RAM). Memoria respaldada por batería
# donde los juegos guardan partidas. El frontend la carga/guarda a disco.
RETRO_MEMORY_SAVE_RAM = 0

# Reloj en tiempo real (RTC). Algunos juegos tienen un reloj interno
# para llevar la cuenta del tiempo (ej: Pokémon día/noche).
RETRO_MEMORY_RTC = 1

# ── Formatos de píxel ───────────────────────────────────────────────
# Definen cómo el core codifica cada píxel del framebuffer.
# Se configuran con SET_PIXEL_FORMAT.

# 0RGB1555: 16 bits, 5 bits por canal (R/G/B), bit 15 ignorado. Obsoleto.
RETRO_PIXEL_FORMAT_0RGB1555 = 0
# XRGB8888: 32 bits, 8 bits por canal (R/G/B), byte alto ignorado. Máxima calidad.
RETRO_PIXEL_FORMAT_XRGB8888 = 1
# RGB565: 16 bits, R=5 bits, G=6 bits, B=5 bits. El más usado actualmente.
RETRO_PIXEL_FORMAT_RGB565 = 2

# ── Tipos de dispositivo de entrada ─────────────────────────────────
# Identifican qué tipo de controlador está consultando el core.

# Número de bits para la subclase del dispositivo.
# Un dispositivo puede tener subtipos: device = (subtipo << 8) | tipo_base
RETRO_DEVICE_TYPE_SHIFT = 8
# Máscara para extraer el tipo base: device & MASK = tipo_base (bits 0-7)
RETRO_DEVICE_MASK = (1 << RETRO_DEVICE_TYPE_SHIFT) - 1

# Joypad digital: botones A/B/X/Y, D-pad, L/R, Start/Select
RETRO_DEVICE_JOYPAD = 1
# Ratón: movimiento relativo + botones. Usado por Citra para el touch.
RETRO_DEVICE_MOUSE = 2
# Joypad con sticks analógicos: Circle Pad, C-Stick, etc.
RETRO_DEVICE_ANALOG = 5
# Puntero/pantalla táctil: coordenadas absolutas [-0x7FFF, 0x7FFF] + pressed.
# Usado por melonDS para la pantalla táctil de DS.
RETRO_DEVICE_POINTER = 6

# ── IDs de ejes/botones dentro de cada dispositivo ──────────────────

# Puntero (POINTER): IDs para consultar coordenadas y estado
RETRO_DEVICE_ID_POINTER_X = 0         # Coordenada X del toque
RETRO_DEVICE_ID_POINTER_Y = 1         # Coordenada Y del toque
RETRO_DEVICE_ID_POINTER_PRESSED = 2   # 1 si está tocando, 0 si no

# Analógico (ANALOG): IDs de ejes dentro de un stick
RETRO_DEVICE_ID_ANALOG_X = 0          # Eje horizontal del stick
RETRO_DEVICE_ID_ANALOG_Y = 1          # Eje vertical del stick

# Analógico (ANALOG): índices para seleccionar qué stick consultar
RETRO_DEVICE_INDEX_ANALOG_LEFT = 0    # Stick izquierdo (Circle Pad en 3DS)
RETRO_DEVICE_INDEX_ANALOG_RIGHT = 1   # Stick derecho (C-Stick en New 3DS)
RETRO_DEVICE_INDEX_ANALOG_BUTTON = 2  # Botones como ejes (presión analógica)

# Ratón (MOUSE): ID del botón izquierdo
RETRO_DEVICE_ID_MOUSE_LEFT = 2

# ══════════════════════════════════════════════════════════════════════
# Tipos de callback de libretro (CFUNCTYPE = punteros a función de C).
# El frontend crea funciones Python que coinciden con estas firmas
# y las registra en el core mediante retro_set_*().
# ══════════════════════════════════════════════════════════════════════

# video_refresh(data, width, height, pitch): el core envía un frame renderizado.
# data = puntero al framebuffer, pitch = bytes por fila (puede incluir padding).
c_video_refresh_t = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint, ctypes.c_size_t)

# environment(cmd, data): el core solicita info o configura el frontend.
# cmd = ID del environment call, data = puntero a los datos (depende del cmd).
c_environment_t = ctypes.CFUNCTYPE(ctypes.c_bool, ctypes.c_uint, ctypes.c_void_p)

# audio_sample(left, right): el core envía una muestra de audio estéreo (poco usado).
c_audio_sample_t = ctypes.CFUNCTYPE(None, ctypes.c_int16, ctypes.c_int16)

# audio_sample_batch(data, frames): el core envía un bloque de muestras de audio.
# data = array de int16 intercalado (L,R,L,R,...), frames = número de frames estéreo.
# Retorna cuántos frames fueron consumidos por el frontend.
c_audio_sample_batch_t = ctypes.CFUNCTYPE(ctypes.c_size_t, ctypes.POINTER(ctypes.c_int16), ctypes.c_size_t)

# input_poll(): el frontend actualiza el estado de los controles (llamada cada frame).
c_input_poll_t = ctypes.CFUNCTYPE(None)

# input_state(port, device, index, id) → int16: el core consulta el estado de un control.
# port = jugador, device = tipo (JOYPAD/ANALOG/POINTER), index = sub-índice, id = botón/eje.
c_input_state_t = ctypes.CFUNCTYPE(ctypes.c_int16, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint)

# log_printf(level, msg): callback de logging del core (nivel + mensaje formateado).
c_log_printf_t = ctypes.CFUNCTYPE(None, ctypes.c_int, ctypes.c_char_p)

# hw_context_reset(): llamada cuando el contexto OpenGL se crea o destruye.
# El core debe (re)crear sus recursos GPU aquí.
c_hw_context_reset_t = ctypes.CFUNCTYPE(None)

# hw_get_current_framebuffer() → size_t: devuelve el ID del FBO activo.
# El core renderiza en este framebuffer y el frontend lo muestra en pantalla.
c_hw_get_current_framebuffer_t = ctypes.CFUNCTYPE(ctypes.c_size_t)

# hw_get_proc_address(name) → void*: obtiene punteros a funciones OpenGL por nombre.
# Equivalente a glXGetProcAddress / wglGetProcAddress.
c_hw_get_proc_address_t = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_char_p)

# ══════════════════════════════════════════════════════════════════════
# Estructuras de la API libretro (equivalentes a los structs de C).
# Usan ctypes.Structure para tener la misma disposición en memoria
# que sus contrapartes en C, permitiendo pasarlas directamente al core.
# ══════════════════════════════════════════════════════════════════════

# Información del juego que se pasa a retro_load_game().
# path = ruta al archivo ROM, data = contenido en memoria (si need_fullpath=False),
# size = tamaño de data, meta = metadatos opcionales (raramente usado).
class RetroGameInfo(ctypes.Structure):
    _fields_ = [
        ("path", ctypes.c_char_p),
        ("data", ctypes.c_void_p),
        ("size", ctypes.c_size_t),
        ("meta", ctypes.c_char_p),
    ]

# Información estática del core (nombre, versión, extensiones soportadas).
# need_fullpath: si True, el frontend pasa solo la ruta (no carga data en memoria).
# block_extract: si True, el frontend no debe descomprimir archivos antes de cargar.
class RetroSystemInfo(ctypes.Structure):
    _fields_ = [
        ("library_name", ctypes.c_char_p),
        ("library_version", ctypes.c_char_p),
        ("valid_extensions", ctypes.c_char_p),
        ("need_fullpath", ctypes.c_bool),
        ("block_extract", ctypes.c_bool),
    ]

# Geometría del vídeo: resolución base, máxima y relación de aspecto.
# base_width/height: resolución nominal del juego (puede cambiar dinámicamente).
# max_width/height: resolución máxima que el core puede producir (fija).
# aspect_ratio: si es 0.0, el frontend calcula width/height.
class RetroGameGeometry(ctypes.Structure):
    _fields_ = [
        ("base_width", ctypes.c_uint),
        ("base_height", ctypes.c_uint),
        ("max_width", ctypes.c_uint),
        ("max_height", ctypes.c_uint),
        ("aspect_ratio", ctypes.c_float),
    ]

# Temporización del sistema emulado.
# fps: frames por segundo del vídeo. sample_rate: frecuencia de audio en Hz.
class RetroSystemTiming(ctypes.Structure):
    _fields_ = [("fps", ctypes.c_double), ("sample_rate", ctypes.c_double)]

# Combina geometría de vídeo + temporización. Se obtiene con retro_get_system_av_info()
# después de cargar un juego y se usa para configurar el driver de vídeo/audio.
class RetroSystemAVInfo(ctypes.Structure):
    _fields_ = [("geometry", RetroGameGeometry), ("timing", RetroSystemTiming)]

# Callback de logging: contiene un puntero a la función de log del frontend.
# Se pasa al core cuando llama a GET_LOG_INTERFACE.
class RetroLogCallback(ctypes.Structure):
    _fields_ = [("log", ctypes.c_void_p)]

# Par clave-valor para opciones del core.
# En GET_VARIABLE: key = nombre de la opción, value = valor actual (rellenado por frontend).
# En SET_VARIABLES: key = nombre, value = "Descripción; opcion1|opcion2|opcion3".
class RetroVariable(ctypes.Structure):
    _fields_ = [("key", ctypes.c_char_p), ("value", ctypes.c_char_p)]

# Callback para renderizado por hardware (OpenGL, Vulkan, etc.).
# El core rellena context_type (qué API quiere) y el frontend rellena
# get_current_framebuffer y get_proc_address. context_reset se llama
# cuando el contexto GL está listo; context_destroy cuando se elimina.
# depth/stencil: si el core necesita buffers de profundidad/stencil.
# bottom_left_origin: True si el origen de coordenadas está abajo-izquierda (OpenGL).
# version_major/minor: versión mínima de OpenGL requerida.
# cache_context: si True, el frontend mantiene el contexto entre juegos.
class RetroHWRenderCallback(ctypes.Structure):
    _fields_ = [
        ("context_type", ctypes.c_int),              # Tipo de API (OpenGL, Vulkan...)
        ("context_reset", c_hw_context_reset_t),      # Callback: contexto creado
        ("get_current_framebuffer", c_hw_get_current_framebuffer_t),  # → ID del FBO
        ("get_proc_address", c_hw_get_proc_address_t),               # → puntero a función GL
        ("depth", ctypes.c_bool),                     # ¿Necesita depth buffer?
        ("stencil", ctypes.c_bool),                   # ¿Necesita stencil buffer?
        ("bottom_left_origin", ctypes.c_bool),        # Origen abajo-izquierda (OpenGL)
        ("version_major", ctypes.c_uint),             # Versión GL mayor requerida
        ("version_minor", ctypes.c_uint),             # Versión GL menor requerida
        ("cache_context", ctypes.c_bool),             # Mantener contexto entre juegos
        ("context_destroy", c_hw_context_reset_t),    # Callback: contexto destruido
        ("debug_context", ctypes.c_bool),             # Usar contexto de depuración GL
    ]
    
# Descriptor de un control de entrada del core.
# El core envía un array de estos al frontend con SET_INPUT_DESCRIPTORS
# para que el usuario vea los nombres legibles de cada botón/eje.
# port = jugador, device = tipo, index = sub-índice, id = botón concreto.
class RetroInputDescriptor(ctypes.Structure):
    _fields_ = [
        ("port", ctypes.c_uint),          # Puerto del jugador (0 = jugador 1)
        ("device", ctypes.c_uint),        # Tipo de dispositivo (JOYPAD, ANALOG...)
        ("index", ctypes.c_uint),         # Sub-índice (stick izq/der para ANALOG)
        ("id", ctypes.c_uint),            # ID del botón/eje
        ("description", ctypes.c_char_p), # Nombre legible (ej: "D-Pad Up", "A Button")
    ]

# ── Estructuras para opciones del core ──────────────────────────────
# El core define sus opciones configurables (resolución, filtros, etc.)
# usando estas estructuras. El frontend las muestra al usuario.

# Máximo de valores posibles por opción (definido en libretro.h).
RETRO_NUM_CORE_OPTION_VALUES_MAX = 128

# Un valor posible de una opción del core.
# value = ID interno (ej: "1x", "2x"), label = texto visible al usuario.
class RetroCoreOptionValue(ctypes.Structure):
    _fields_ = [
        ("value", ctypes.c_char_p),   # Valor interno de la opción
        ("label", ctypes.c_char_p),   # Etiqueta visible (None = usar value como etiqueta)
    ]

# Definición de una opción del core (versión 1, para SET_CORE_OPTIONS).
# Obsoleta: no soporta categorías. Usar RetroCoreOptionV2Definition para código nuevo.
class RetroCoreOptionDefinition(ctypes.Structure):
    _fields_ = [
        ("key", ctypes.c_char_p),       # Clave única de la opción (ej: "citra_resolution_factor")
        ("desc", ctypes.c_char_p),      # Descripción corta visible al usuario
        ("info", ctypes.c_char_p),      # Descripción larga/tooltip
        ("values", RetroCoreOptionValue * RETRO_NUM_CORE_OPTION_VALUES_MAX),  # Valores posibles
        ("default_value", ctypes.c_char_p),  # Valor por defecto
    ]

# Definición de una opción del core (versión 2, para SET_CORE_OPTIONS_V2).
# Añade soporte para categorías y descripciones contextuales.
class RetroCoreOptionV2Definition(ctypes.Structure):
    _fields_ = [
        ("key", ctypes.c_char_p),             # Clave única de la opción
        ("desc", ctypes.c_char_p),            # Descripción corta (vista global)
        ("desc_categorized", ctypes.c_char_p),# Descripción corta (dentro de su categoría)
        ("info", ctypes.c_char_p),            # Tooltip (vista global)
        ("info_categorized", ctypes.c_char_p),# Tooltip (dentro de su categoría)
        ("category_key", ctypes.c_char_p),    # Clave de la categoría a la que pertenece
        ("values", RetroCoreOptionValue * RETRO_NUM_CORE_OPTION_VALUES_MAX),  # Valores posibles
        ("default_value", ctypes.c_char_p),   # Valor por defecto
    ]

# Categoría de opciones del core (versión 2).
# Agrupa opciones relacionadas bajo un nombre común (ej: "Video", "Audio").
class RetroCoreOptionV2Category(ctypes.Structure):
    _fields_ = [
        ("key", ctypes.c_char_p),    # Clave única de la categoría
        ("desc", ctypes.c_char_p),   # Nombre visible de la categoría
        ("info", ctypes.c_char_p),   # Descripción de la categoría
    ]

# Estructura raíz para SET_CORE_OPTIONS_V2.
# Combina las categorías y las definiciones de opciones en un solo paquete.
class RetroCoreOptionsV2(ctypes.Structure):
    _fields_ = [
        ("categories", ctypes.POINTER(RetroCoreOptionV2Category)),     # Array de categorías (terminado en NULL)
        ("definitions", ctypes.POINTER(RetroCoreOptionV2Definition)),  # Array de opciones (terminado en NULL)
    ]
