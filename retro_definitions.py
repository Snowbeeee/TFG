import ctypes

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
RETRO_ENVIRONMENT_GET_LANGUAGE = 39

RETRO_LANGUAGE_SPANISH = 3

RETRO_MEMORY_SAVE_RAM = 0
RETRO_MEMORY_RTC = 1

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

RETRO_DEVICE_INDEX_ANALOG_LEFT = 0
RETRO_DEVICE_INDEX_ANALOG_RIGHT = 1
RETRO_DEVICE_INDEX_ANALOG_BUTTON = 2
RETRO_DEVICE_ID_MOUSE_LEFT = 2

# Definición de tipos para callbacks
c_video_refresh_t = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint, ctypes.c_size_t)
c_environment_t = ctypes.CFUNCTYPE(ctypes.c_bool, ctypes.c_uint, ctypes.c_void_p)
c_audio_sample_t = ctypes.CFUNCTYPE(None, ctypes.c_int16, ctypes.c_int16)
c_audio_sample_batch_t = ctypes.CFUNCTYPE(ctypes.c_size_t, ctypes.POINTER(ctypes.c_int16), ctypes.c_size_t)
c_input_poll_t = ctypes.CFUNCTYPE(None)
c_input_state_t = ctypes.CFUNCTYPE(ctypes.c_int16, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint)
c_log_printf_t = ctypes.CFUNCTYPE(None, ctypes.c_int, ctypes.c_char_p)
c_hw_context_reset_t = ctypes.CFUNCTYPE(None)
c_hw_get_current_framebuffer_t = ctypes.CFUNCTYPE(ctypes.c_size_t)
c_hw_get_proc_address_t = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_char_p)

# Estructuras
class RetroGameInfo(ctypes.Structure):
    _fields_ = [
        ("path", ctypes.c_char_p),
        ("data", ctypes.c_void_p),
        ("size", ctypes.c_size_t),
        ("meta", ctypes.c_char_p),
    ]

class RetroSystemInfo(ctypes.Structure):
    _fields_ = [
        ("library_name", ctypes.c_char_p),
        ("library_version", ctypes.c_char_p),
        ("valid_extensions", ctypes.c_char_p),
        ("need_fullpath", ctypes.c_bool),
        ("block_extract", ctypes.c_bool),
    ]

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
    
class RetroInputDescriptor(ctypes.Structure):
    _fields_ = [
        ("port", ctypes.c_uint),
        ("device", ctypes.c_uint),
        ("index", ctypes.c_uint),
        ("id", ctypes.c_uint),
        ("description", ctypes.c_char_p),
    ]
