import ctypes       # Permite interactuar con librerías en C/C++ (.dll/.so) desde Python
import os
import sys
from libretro.retro_definitions import *       # Constantes y estructuras C de la API Libretro
from OpenGL.GL import *                        # Funciones de OpenGL para renderizado gráfico
from OpenGL.GL.framebufferobjects import *     # Soporte para Framebuffer Objects (FBO) de OpenGL

# Variables globales para acceder a la instancia desde los callbacks de C
# Variable global que mantiene una referencia a la instancia actual del núcleo (RetroCore).
# Esto es necesario porque los callbacks de C son funciones estáticas/globales y no tienen acceso a 'self'.
_current_core = None

# Callback utilizado por el contexto de renderizado por hardware.
# Devuelve el ID del framebuffer OpenGL (FBO) que el núcleo debe usar para renderizar.
def get_current_framebuffer_callback():
    if _current_core:
        return _current_core.get_framebuffer()
    return 0

# Cargar librería OpenGL para Windows para resolver símbolos
# Carga dinámica de la librería OpenGL en Windows.
# Se utiliza para resolver símbolos y direcciones de funciones OpenGL necesarias para el contexto por hardware.
_gl_lib = None
_wgl_get_proc = None

# Solo se ejecuta en Windows (os.name == 'nt')
if os.name == 'nt':
    try:
        # Cargar la DLL del sistema de OpenGL (opengl32.dll)
        _gl_lib = ctypes.windll.opengl32
        # Obtener referencia a wglGetProcAddress, función de Windows para
        # resolver extensiones de OpenGL en tiempo de ejecución
        _wgl_get_proc = _gl_lib.wglGetProcAddress
        _wgl_get_proc.restype = ctypes.c_void_p      # Devuelve un puntero genérico
        _wgl_get_proc.argtypes = [ctypes.c_char_p]    # Recibe el nombre de la función como cadena C
    except Exception as e:
        print(f"Error cargando OpenGL lib: {e}")
        
        
# ----------------------------------------------------------------------------------------------------------------
#   Callbacks y funciones puente (thunks) para conectar el núcleo con Python
# ----------------------------------------------------------------------------------------------------------------



# Callback que permite al núcleo obtener direcciones de funciones OpenGL (proc address).
# Es crucial para que el núcleo pueda llamar a funciones modernas de OpenGL de forma compatible entre plataformas.
def get_proc_address_callback(sym):
    # Citra necesita punteros reales a funciones OpenGL
    addr = 0
    if os.name == 'nt' and _gl_lib:
        # 1. Intentar obtener extensión (wglGetProcAddress)
        addr = _wgl_get_proc(sym)
        # 2. Si falla, intentar función estándar (GetProcAddress/dlsym implícito)
        if not addr:
            try:
                addr = ctypes.cast(getattr(_gl_lib, sym.decode('utf-8')), ctypes.c_void_p).value
            except AttributeError:
                pass
    return addr if addr else 0

# Callbacks puente
# Funciones "trampolín" (thunks) que actúan como puente entre el mundo C y Python.
# Reciben la llamada desde la DLL del núcleo y redirigen la ejecución al método correspondiente de la instancia _current_core.

# Redirige la actualización de video al método de la instancia.
def video_refresh_thunk(data, width, height, pitch):
    if _current_core:
        _current_core.video_refresh(data, width, height, pitch)

# Redirige las consultas de entorno al método de la instancia.
def environment_thunk(cmd, data):
    if _current_core:
        return _current_core.environment(cmd, data)
    return False

# Redirige el envío de lotes de audio al método de la instancia.
def audio_sample_batch_thunk(data, frames):
    if _current_core:
        return _current_core.audio_sample_batch(data, frames)
    return 0

# Redirige el envío de una muestra de audio individual al método de la instancia.
def audio_sample_thunk(left, right):
    if _current_core:
        _current_core.audio_sample(left, right)

# Redirige la solicitud de sondeo de entrada (poll) al método de la instancia.
def input_poll_thunk():
    if _current_core:
        _current_core.input_poll()

# Redirige la consulta de estado de entrada de un dispositivo específico al método de la instancia.
def input_state_thunk(port, device, index, id_val):
    if _current_core:
        return _current_core.input_state(port, device, index, id_val)
    return 0

# Callback para manejar los mensajes de registro (logs) generados por el núcleo y mostrarlos en la consola.
def log_printf_thunk(level, fmt):
    try:
        msg = fmt.decode('utf-8', errors='replace').strip()
        print(f"[CORE LOG {level}]: {msg}")
    except:
        pass


# ----------------------------------------------------------------------------------------------------------------
#   Clase principal RetroCore
# ----------------------------------------------------------------------------------------------------------------


# Clase principal que encapsula la lógica de carga, ejecución y gestión de un núcleo Libretro.
# Maneja la interacción con la DLL, los contextos gráficos y los dispositivos de entrada/salida.
class RetroCore:
    # Constructor de la clase. Inicializa los gestores de audio e input,
    # carga la librería dinámica del núcleo y configura los callbacks necesarios.
    def __init__(self, lib_path, audio_manager, input_manager):
        global _current_core
        _current_core = self

        # --- Declaración de todas las variables de instancia ---
        self.lib_path = lib_path                  # Ruta a la DLL del core
        self.audio_manager = audio_manager        # Gestor de audio (PyAudio)
        self.input_manager = input_manager        # Gestor de entrada (teclado/ratón)
        self.lib = None                           # Referencia a la DLL cargada con ctypes
        self.context_reset_cb = None              # Callback del core para reiniciar contexto GL
        self._hw_refs = []                        # Referencias para evitar que el GC limpie los callbacks de HW
        self.video_cb = None                      # Callback C de refresco de video
        self.env_cb = None                        # Callback C de entorno
        self.audio_sample_cb = None               # Callback C de muestra de audio individual
        self.audio_batch_cb = None                # Callback C de lote de audio
        self.input_poll_cb = None                 # Callback C de sondeo de entrada
        self.input_state_cb = None                # Callback C de estado de entrada
        self.log_cb = None                        # Callback C de log
        self.aspect_ratio = 0.0                   # Relación de aspecto del juego
        self.base_width = 0                       # Ancho base de la resolución del juego
        self.base_height = 0                      # Alto base de la resolución del juego
        self.fbo_id = 0                           # ID del Framebuffer Object de OpenGL
        self.tex_id = 0                           # ID de la textura asociada al FBO
        self.rbo_id = 0                           # ID del Renderbuffer (profundidad/stencil)
        self.view_rect = (0, 0, 1, 1)             # Rectángulo de visualización (x, y, ancho, alto)
        self.hw_render_depth = False              # Si el core necesita buffer de profundidad
        self.hw_render_stencil = False            # Si el core necesita buffer de stencil
        self.bottom_left_origin = True            # Origen de coordenadas del core (abajo-izquierda)
        self.last_win_size = (-1, -1)             # Último tamaño de ventana conocido
        self.pixel_format = RETRO_PIXEL_FORMAT_0RGB1555   # Formato de píxel actual
        self.fbo_width = 0                        # Ancho actual del FBO
        self.fbo_height = 0                       # Alto actual del FBO
        self.target_fbo = None                    # FBO destino (para integración con Qt)
        self.save_path = None                     # Ruta del archivo de guardado (SRAM)
        self._option_refs = {}                    # Referencias a opciones para evitar limpieza del GC
        self.core_options = {}                    # Opciones de configuración del core
        self._variable_updated = False            # Flag: si alguna opción cambió desde la última consulta
        self.available_options = {}               # Opciones disponibles del core {key: {desc, values[], default}}
        self._pending_sample_rate = 0             # sample rate pendiente de aplicar (SET_SYSTEM_AV_INFO)
        self._current_sample_rate = 0             # sample rate actualmente inicializado

        # --- Carga de la librería y configuración ---
        # ctypes.CDLL carga la DLL del core como si fuera una librería C estándar
        self.lib = ctypes.CDLL(lib_path)

        # Diccionario de opciones del core (variables).
        # IMPORTANTE: debe estar poblado ANTES de retro_init() para que cuando
        # el core llame GET_VARIABLE durante su inicialización (ej: Citra al crear
        # el config del firmware) ya reciba los valores correctos de idioma/región.
        self.core_options = {
            # melonDS DS - Idioma del firmware
            'melonds_firmware_language': 'es',
            # Citra - Idioma del sistema 3DS
            'citra_language': 'Spanish',
            # Citra - Región del sistema 3DS (Auto para que se aplique el idioma)
            'citra_region_value': 'Auto',
        }
        self._variable_updated = False

        print("Registrando input callbacks")
        
        # Instanciar los wrappers ctypes que convierten las funciones Python en punteros
        # a función C compatibles. Cada tipo (c_video_refresh_t, etc) está definido 
        # en retro_definitions.py con la firma exacta que espera la API Libretro.
        self.video_cb = c_video_refresh_t(video_refresh_thunk)
        self.env_cb = c_environment_t(environment_thunk)
        self.audio_sample_cb = c_audio_sample_t(audio_sample_thunk)
        self.audio_batch_cb = c_audio_sample_batch_t(audio_sample_batch_thunk)
        self.input_poll_cb = c_input_poll_t(input_poll_thunk)
        self.input_state_cb = c_input_state_t(input_state_thunk)
        self.log_cb = c_log_printf_t(log_printf_thunk)
        
        # Registrar cada callback en el core. Estas funciones de la API Libretro
        # almacenan los punteros para llamarlos durante la emulación.
        self.lib.retro_set_environment(self.env_cb)
        self.lib.retro_set_video_refresh(self.video_cb)
        self.lib.retro_set_audio_sample(self.audio_sample_cb)
        self.lib.retro_set_audio_sample_batch(self.audio_batch_cb)
        self.lib.retro_set_input_poll(self.input_poll_cb)
        self.lib.retro_set_input_state(self.input_state_cb)
        
        # Inicializar el core (equivalente a "encenderlo")
        self.lib.retro_init()
        # Configurar puerto 0 como mando estándar (joypad)
        self.lib.retro_set_controller_port_device(0, RETRO_DEVICE_JOYPAD)
        
        # Configurar los tipos de retorno y argumentos para las funciones de acceso
        # a la memoria del core (SRAM, RTC, etc). Esto es necesario porque ctypes
        # por defecto asume que todas las funciones devuelven int.
        self.lib.retro_get_memory_data.restype = ctypes.c_void_p
        self.lib.retro_get_memory_data.argtypes = [ctypes.c_uint]

        self.lib.retro_get_memory_size.restype = ctypes.c_size_t
        self.lib.retro_get_memory_size.argtypes = [ctypes.c_uint]

    def set_option(self, key, value):
        """Establece una opción del core y marca que hubo actualización."""
        self.core_options[key] = value
        self._variable_updated = True

    def set_target_fbo(self, fbo):
        self.target_fbo = fbo

    # Devuelve el ID numérico del Framebuffer Object (FBO) actual.
    def get_framebuffer(self):
        return int(self.fbo_id)

    # Inicializa o reinicializa el Framebuffer Object (FBO) de OpenGL.
    # Crea las texturas y buffers de profundidad/stencil necesarios según la resolución del juego.
    def init_framebuffer(self, width, height):
        # Si ya existían recursos previos, liberarlos antes de crear nuevos
        if self.fbo_id:
            glDeleteFramebuffers(1, [self.fbo_id])
        if self.tex_id:
            glDeleteTextures(1, [self.tex_id])
        if self.rbo_id:
            glDeleteRenderbuffers(1, [self.rbo_id])
        
        # Generar nuevos objetos de OpenGL    
        self.fbo_id = int(glGenFramebuffers(1))     # Crear un nuevo Framebuffer
        self.tex_id = int(glGenTextures(1))          # Crear una nueva textura para el color
        self.fbo_width = width
        self.fbo_height = height
        
        # Vincular el FBO como destino de renderizado activo
        glBindFramebuffer(GL_FRAMEBUFFER, self.fbo_id)
        
        # Crear y adjuntar la textura de color al FBO.
        # Esta textura recibirá los píxeles renderizados por el core.
        glBindTexture(GL_TEXTURE_2D, self.tex_id)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, None)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)   # Filtrado bilineal al reducir
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)   # Filtrado bilineal al ampliar
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, self.tex_id, 0)
        
        # Adjuntar buffer de profundidad y/o stencil si el core los solicita.
        # Algunos cores 3D (como Citra) necesitan depth/stencil para renderizar correctamente.
        if self.hw_render_depth or self.hw_render_stencil:
            self.rbo_id = int(glGenRenderbuffers(1))
            glBindRenderbuffer(GL_RENDERBUFFER, self.rbo_id)
            if self.hw_render_depth and self.hw_render_stencil:
                # Formato combinado: 24 bits de profundidad + 8 bits de stencil
                glRenderbufferStorage(GL_RENDERBUFFER, GL_DEPTH24_STENCIL8, width, height)
                glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_DEPTH_STENCIL_ATTACHMENT, GL_RENDERBUFFER, self.rbo_id)
            elif self.hw_render_depth:
                # Solo profundidad: 24 bits
                glRenderbufferStorage(GL_RENDERBUFFER, GL_DEPTH_COMPONENT24, width, height)
                glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_RENDERBUFFER, self.rbo_id)
        
        # Verificar que el FBO esté completo y listo para usar
        status = glCheckFramebufferStatus(GL_FRAMEBUFFER)
        if status != GL_FRAMEBUFFER_COMPLETE:
            print(f"Error: Framebuffer incompleto (Status: {status})")
            
        glBindFramebuffer(GL_FRAMEBUFFER, 0)
        print(f"FBO Inicializado: {width}x{height} (ID: {self.fbo_id})")

    # Carga la partida guardada (SRAM) desde disco a la memoria del núcleo
    def load_sram(self):
        if not self.save_path:
            return
        
        # Obtener el tamaño de la zona de memoria SRAM del core    
        size = self.lib.retro_get_memory_size(RETRO_MEMORY_SAVE_RAM)
        if size == 0:
            return
        
        # Si existe un archivo de guardado previo, leerlo y copiarlo a la memoria del core    
        if os.path.exists(self.save_path):
            with open(self.save_path, "rb") as f:
                data = f.read()
                # Truncar si el archivo es mayor que la memoria disponible del core
                if len(data) > size:
                    print(f"Warning: Save file larger than core memory ({len(data)} > {size}). Truncating.")
                    data = data[:size]
                
                # Obtener el puntero a la zona de memoria SRAM del core
                ptr = self.lib.retro_get_memory_data(RETRO_MEMORY_SAVE_RAM)
                if ptr:
                    # Copiar los bytes del archivo directamente a la memoria del core
                    ctypes.memmove(ptr, data, len(data))
                    print(f"SRAM cargada desde {self.save_path}")

    # Guarda la partida (SRAM) de la memoria del núcleo al disco
    def save_sram(self):
        if not self.save_path:
            return
        
        # Obtener tamaño y puntero de la memoria SRAM del core    
        size = self.lib.retro_get_memory_size(RETRO_MEMORY_SAVE_RAM)
        ptr = self.lib.retro_get_memory_data(RETRO_MEMORY_SAVE_RAM)
        
        if size > 0 and ptr:
            # Leer los bytes de la memoria del core como cadena de bytes
            data = ctypes.string_at(ptr, size)
            
            # Crear el directorio de guardado si no existe
            save_dir = os.path.dirname(self.save_path)
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)
            
            # Escribir los datos al archivo de guardado    
            with open(self.save_path, "wb") as f:
                f.write(data)
            print(f"SRAM guardada en {self.save_path}")

    # Carga un archivo de juego (ROM) en el núcleo.
    # Lee los datos del archivo, configura la memoria y establece los parámetros iniciales del sistema.
    def load_game(self, rom_path):
        # Calcular path de guardado
        # Usamos .sav para compatibilidad general (aunque algunos usan .dsv)
        rom_name = os.path.splitext(os.path.basename(rom_path))[0]
        self.save_path = os.path.abspath(os.path.join("saves", rom_name + ".dsv"))
        # Si usas Desmume, a veces prefiere .dsv. Si usas otros, .srm o .sav.
        # Libretro suele estandarizar a .srm, pero dejaremos .dsv para DS si prefieres.
        # Ajuste dinámico: Si rom es .nds -> .dsv. Si .3ds -> .sav
        if rom_path.lower().endswith('.nds'):
             self.save_path = os.path.abspath(os.path.join("saves", rom_name + ".dsv"))
        else:
             self.save_path = os.path.abspath(os.path.join("saves", rom_name + ".sav"))

        # Obtener información del sistema (nombre del core, versión, si necesita ruta completa, etc.)
        self.lib.retro_get_system_info.argtypes = [ctypes.POINTER(RetroSystemInfo)]
        sys_info = RetroSystemInfo()
        self.lib.retro_get_system_info(ctypes.byref(sys_info))
        print(f"Core cargado: {sys_info.library_name.decode()} ({sys_info.library_version.decode()})")
        
        # Preparar la estructura RetroGameInfo con la ruta y los datos del juego
        full_path = os.path.abspath(rom_path).encode('utf-8')
        game_info = RetroGameInfo()
        game_info.path = full_path
        game_info.meta = None
        
        rom_data = None # Mantener referencia para que el GC no libere los datos
        
        # Si el core necesita la ruta completa (need_fullpath=True), no es necesario
        # pasar los datos en memoria; el core abrirá el archivo por su cuenta.
        # Si no, hay que leer el archivo y pasarlo como buffer.
        if sys_info.need_fullpath:
            game_info.data = None
            game_info.size = 0
        else:
            with open(rom_path, "rb") as f:
                rom_data = f.read()
            # Crear un buffer C con los datos de la ROM y convertirlo a puntero genérico
            game_info.data = ctypes.cast(ctypes.create_string_buffer(rom_data), ctypes.c_void_p)
            game_info.size = len(rom_data)
        
        # Configurar tipos de la función y llamar a retro_load_game
        self.lib.retro_load_game.argtypes = [ctypes.POINTER(RetroGameInfo)]
        self.lib.retro_load_game.restype = ctypes.c_bool
        
        if not self.lib.retro_load_game(ctypes.byref(game_info)):
            print("Fallo al cargar el juego")
            return False
            
        print("Juego cargado exitosamente.")
        
        # Reasignar mando tras la carga (algunos cores lo reinician)
        self.lib.retro_set_controller_port_device(0, RETRO_DEVICE_JOYPAD)
        
        # Obtener información de Audio/Vídeo del core.
        # Se obtiene ANTES de context_reset para crear el FBO al tamaño correcto.
        self.lib.retro_get_system_av_info.argtypes = [ctypes.POINTER(RetroSystemAVInfo)]
        av_info = RetroSystemAVInfo()
        self.lib.retro_get_system_av_info(ctypes.byref(av_info))
        
        # Guardar dimensiones base y relación de aspecto del juego
        self.base_width = av_info.geometry.base_width
        self.base_height = av_info.geometry.base_height
        self.aspect_ratio = av_info.geometry.aspect_ratio

        # Actualizar el gestor de entrada con las nuevas dimensiones (para calcular coordenadas táctiles)
        self.input_manager.update_geometry(self.base_width, self.base_height, self.aspect_ratio)
        # Inicializar el stream de audio con la frecuencia de muestreo del core
        self._current_sample_rate = int(av_info.timing.sample_rate)
        self.audio_manager.init_stream(self._current_sample_rate)
        
        # Crear el FBO solo si aún no existe.
        # SET_SYSTEM_AV_INFO (llamado desde retro_load_game) puede haberlo creado
        # ya al tamaño correcto (p.ej. upscaled 512×768 para DS 2x).
        # Si se recrea aquí forzando las dimensiones base, el core renderiza fuera
        # del FBO demasiado pequeño y la imagen aparece cortada.
        if self.fbo_id == 0:
            self.init_framebuffer(self.base_width, self.base_height)
        print(f"[FBO] Usando FBO id={self.fbo_id} {self.fbo_width}x{self.fbo_height} "
              f"(base {self.base_width}x{self.base_height})")
        
        if self.context_reset_cb:
            # Preparar el estado GL antes de que el core inicialice su renderer:
            # - Viewport exactamente al tamaño del FBO, para que el core vea el
            #   área de render correcta (Citra puede haber dejado otro viewport).
            # - FBO propio vinculado como destino (el core lo leerá con get_current_framebuffer).
            glBindFramebuffer(GL_FRAMEBUFFER, self.fbo_id)
            glViewport(0, 0, self.fbo_width, self.fbo_height)
            glDisable(GL_SCISSOR_TEST)
            glDisable(GL_DEPTH_TEST)
            glDisable(GL_BLEND)
            glColorMask(GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE)
            glDepthMask(GL_TRUE)
            glClearColor(0, 0, 0, 1)
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            glBindFramebuffer(GL_FRAMEBUFFER, 0)
            print(f"[FBO] Llamando context_reset_cb (fbo_id={self.fbo_id} {self.fbo_width}x{self.fbo_height})")
            self.context_reset_cb()
        
        # Cargar partida salvada si existe
        self.load_sram()
        
        print(f"Resolución base: {av_info.geometry.base_width}x{av_info.geometry.base_height}, FPS: {av_info.timing.fps}")
        return True

    # Actualiza el rectángulo de visualización (viewport) basándose en el tamaño de la ventana y el aspect ratio.
    # Calcula el escalado correcto tipo "Letterboxing" para mantener la proporción de la imagen.
    def update_video(self, win_width, win_height):
        if self.last_win_size != (win_width, win_height):
            print(f"[DEBUG] Window Resized: {win_width}x{win_height} | Core Base: {self.base_width}x{self.base_height}")
            self.last_win_size = (win_width, win_height)

        # Determinar la relación de aspecto objetivo (la del juego)
        if self.aspect_ratio > 0:
            target_aspect = self.aspect_ratio
        else:
            target_aspect = self.base_width / self.base_height if self.base_height > 0 else 1.0
        
        # Relación de aspecto actual de la ventana
        window_aspect = win_width / win_height if win_height > 0 else 1.0

        # Cálculo de letterboxing/pillarboxing:
        # Si la ventana es más ancha que el juego -> barras laterales (pillarbox)
        # Si la ventana es más alta que el juego -> barras arriba/abajo (letterbox)
        if window_aspect > target_aspect:
            view_h = win_height
            view_w = win_height * target_aspect
        else:
            view_w = win_width
            view_h = win_width / target_aspect
        
        # Centrar la imagen en la ventana
        x = int((win_width - view_w) / 2)
        y = int((win_height - view_h) / 2)
        w = int(view_w)
        h = int(view_h)
        
        if self.view_rect != (x, y, w, h):
             print(f"[DEBUG] New View Rect: x={x}, y={y}, w={w}, h={h}")

        self.view_rect = (x, y, w, h)
        # No llamamos glViewport aquí, lo haremos en el blit

    # Ejecuta un ciclo (frame) del núcleo emulado.
    # Llama a la función principal retro_run() de la librería.
    def run(self):
        # Aplicar sample rate pendiente (diferido desde SET_SYSTEM_AV_INFO para no
        # reinicializar audio desde dentro de un callback de C).
        if self._pending_sample_rate:
            sr = self._pending_sample_rate
            self._pending_sample_rate = 0
            self._current_sample_rate = sr
            self.audio_manager.init_stream(sr)
        self.lib.retro_run()

    # Serializa el estado completo del juego (savestate) a un buffer en memoria.
    # Devuelve bytes con el estado, o None si falla o no está soportado.
    def save_state(self):
        try:
            self.lib.retro_serialize_size.restype = ctypes.c_size_t
            size = self.lib.retro_serialize_size()
            if size == 0:
                print("[Savestate] retro_serialize_size devolvió 0, no soportado")
                return None
            buf = ctypes.create_string_buffer(size)
            self.lib.retro_serialize.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
            self.lib.retro_serialize.restype = ctypes.c_bool
            ok = self.lib.retro_serialize(buf, size)
            if ok:
                print(f"[Savestate] Estado guardado ({size} bytes)")
                return bytes(buf)
            else:
                print("[Savestate] retro_serialize falló")
                return None
        except Exception as e:
            print(f"[Savestate] Error al serializar: {e}")
            return None

    # Restaura el estado del juego desde un buffer previamente guardado con save_state().
    def load_state(self, data):
        if not data:
            return False
        try:
            buf = ctypes.create_string_buffer(data, len(data))
            self.lib.retro_unserialize.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
            self.lib.retro_unserialize.restype = ctypes.c_bool
            ok = self.lib.retro_unserialize(buf, len(data))
            if ok:
                print(f"[Savestate] Estado restaurado ({len(data)} bytes)")
            else:
                print("[Savestate] retro_unserialize falló")
            return ok
        except Exception as e:
            print(f"[Savestate] Error al deserializar: {e}")
            return False

    # Descarga el juego actual y desinicializa el núcleo, liberando recursos.
    def unload(self):
        if not self.lib:
            return

        global _current_core

        # Guardar partida antes de descargar
        self.save_sram()

        # Descargar el juego y desinicializar el core (en orden inverso a la carga)
        self.lib.retro_unload_game()
        self.lib.retro_deinit()

        # Liberar recursos OpenGL (FBO, textura, RBO)
        # El contexto GL debe estar activo (makeCurrent) antes de llamar a esto.
        try:
            if self.fbo_id:
                glDeleteFramebuffers(1, [self.fbo_id])
                self.fbo_id = 0
            if self.tex_id:
                glDeleteTextures(1, [self.tex_id])
                self.tex_id = 0
            if self.rbo_id:
                glDeleteRenderbuffers(1, [self.rbo_id])
                self.rbo_id = 0
        except Exception as e:
            print(f"Aviso: Error liberando recursos GL: {e}")

        # Descargar la DLL del proceso para evitar conflictos entre cores.
        # FreeLibrary se llama en bucle porque ctypes.CDLL y el propio core
        # pueden haber incrementado el refcount de LoadLibrary más de una vez.
        try:
            handle = self.lib._handle      # Guardar el handle nativo antes de eliminar el objeto
            del self.lib                   # Eliminar la referencia Python
            if os.name == 'nt':
                # En Windows: usar FreeLibrary del kernel32 para decrementar el refcount
                kernel32 = ctypes.windll.kernel32
                for _ in range(10):
                    if not kernel32.FreeLibrary(ctypes.c_void_p(handle)):
                        break
            else:
                # En Linux/Mac: usar dlclose para descargar la librería
                import _ctypes
                _ctypes.dlclose(handle)
        except Exception as e:
            print(f"Aviso: No se pudo descargar la DLL: {e}")

        # Resetear todas las variables de instancia a su estado inicial
        self.lib = None
        self.context_reset_cb = None
        self._hw_refs.clear()
        self._option_refs.clear()
        self.fbo_width = 0
        self.fbo_height = 0
        self.last_win_size = (-1, -1)
        self._pending_sample_rate = 0
        self._current_sample_rate = 0
        if hasattr(self, '_blit_logged'):
            del self._blit_logged

        # Limpiar referencia global para que los callbacks no intenten acceder a este core
        if _current_core is self:
            _current_core = None

    # Implementación de callbacks
    # Callback llamado por el núcleo cuando hay un nuevo frame de video listo para mostrar.
    # Realiza el blit (copiado) del FBO interno a la pantalla principal, aplicando el escalado calculado.
    def video_refresh(self, data, width, height, pitch):
        if width == 0 or height == 0:
            return

        # Manejar renderizado por Software (Desmume, etc) vs Hardware (Citra)
        # Si data es un puntero válido (no NULL y no RETRO_HW_FRAME_BUFFER_VALID/-1), es software.
        is_software = False
        data_addr = 0
        if data: 
            # Detección robusta de dirección de memoria
            if isinstance(data, int):
                data_addr = data
            elif hasattr(data, 'value'):
                data_addr = data.value
            else:
                try:
                    data_addr = int(data)
                except:
                    pass
        
        # RETRO_HW_FRAME_BUFFER_VALID suele ser -1 (hardware rendering).
        # También verificamos 0 y valores de puntero inválido comunes.
        # Citra (HW) enviará -1 (u oscilará como unsigned). Desmume (SW) enviará una dirección RAM válida.
        if data_addr not in (0, -1, 0xFFFFFFFF, 0xFFFFFFFFFFFFFFFF):
            is_software = True
        
        # Si es modo Software, necesitamos subir la textura a OpenGL
        if is_software:
            # Inicializar FBO si no existe o si el tamaño cambió
            if self.fbo_id == 0 or self.fbo_width != width or self.fbo_height != height:
                self.init_framebuffer(width, height)
                self.fbo_width = width
                self.fbo_height = height
                # Actualizar geometría base si cambió
                self.input_manager.update_geometry(width, height, self.aspect_ratio)
            
            # Determinar el formato de píxel y bytes por píxel según lo que el core indicó.
            # Cada formato requiere una combinación específica de gl_fmt y gl_type.
            gl_fmt = GL_BGRA
            gl_type = GL_UNSIGNED_BYTE
            bpp = 4    # Bytes por píxel
            
            if self.pixel_format == RETRO_PIXEL_FORMAT_RGB565:
                 gl_fmt = GL_RGB
                 gl_type = GL_UNSIGNED_SHORT_5_6_5
                 bpp = 2
            elif self.pixel_format == RETRO_PIXEL_FORMAT_0RGB1555:
                 # 0RGB1555: 1 bit vacio (A), R, G, B.
                 # GL_UNSIGNED_SHORT_1_5_5_5_REV + GL_BGRA mapea correctamente A(15) R(14-10) G(9-5) B(4-0)
                 gl_fmt = GL_BGRA
                 gl_type = GL_UNSIGNED_SHORT_1_5_5_5_REV
                 bpp = 2
            elif self.pixel_format == RETRO_PIXEL_FORMAT_XRGB8888:
                 # XRGB8888: Byte order B G R X en Little Endian.
                 # GL_BGRA + GL_UNSIGNED_BYTE lee Byte0=B, Byte1=G, Byte2=R, Byte3=A(X)
                 gl_fmt = GL_BGRA
                 gl_type = GL_UNSIGNED_BYTE
                 bpp = 4

            # Vincular la textura del FBO para subir los píxeles
            glBindTexture(GL_TEXTURE_2D, self.tex_id)
            
            # Alineación de 1 byte para evitar problemas con filas que no son múltiplo de 4
            glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
            
            # El pitch (stride) es la cantidad de bytes entre el inicio de una fila y la siguiente.
            # Puede ser mayor que width*bpp si hay padding. GL_UNPACK_ROW_LENGTH lo indica.
            if pitch > 0:
                glPixelStorei(GL_UNPACK_ROW_LENGTH, pitch // bpp)
            
            # Subir los datos de la imagen de la RAM a la textura de OpenGL
            glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, width, height, gl_fmt, gl_type, ctypes.c_void_p(data_addr))
            
            # Restaurar valores por defecto de alineación
            glPixelStorei(GL_UNPACK_ROW_LENGTH, 0)
            glPixelStorei(GL_UNPACK_ALIGNMENT, 4)
            glBindTexture(GL_TEXTURE_2D, 0)

        # Si no tenemos FBO (ni por HW init ni por SW init), salimos
        if self.fbo_id == 0: 
            return
        
        # Limpiar errores GL pendientes del core antes de hacer blit
        while glGetError() != GL_NO_ERROR:
            pass

        # Blit del FBO a pantalla
        glDisable(GL_SCISSOR_TEST)
        
        # Obtener el FBO actual (importante para integración con Qt/SDL donde el buffer por defecto no es 0)
        prev_fbo = 0
        if self.target_fbo is not None:
             prev_fbo = self.target_fbo
        else:    
             prev_fbo = glGetIntegerv(GL_DRAW_FRAMEBUFFER_BINDING)
        
        # Debug
        # print(f"Blit: ID {self.fbo_id} -> {prev_fbo} | Size {width}x{height}")
        
        # Configurar el blit: vincular FBO fuente (lectura) y destino (escritura)
        glBindFramebuffer(GL_READ_FRAMEBUFFER, self.fbo_id)
        glBindFramebuffer(GL_DRAW_FRAMEBUFFER, prev_fbo)
        
        # Limpiar el framebuffer destino con negro antes del blit
        # (así las barras de letterbox/pillarbox quedan negras)
        glClearColor(0,0,0,1)
        glClear(GL_COLOR_BUFFER_BIT)
        
        # Coordenadas del rectángulo destino (calculadas en update_video)
        dst_x, dst_y, dst_w, dst_h = self.view_rect
        
        # Calcular coordenadas de origen (flip vertical)
        # HW Render: Depende de bottom_left_origin (True = Normal, False = Flipped/Top-Left)
        # SW Render: Datos cargados Bottom-Up o Top-Down?
        # En la version anterior estaba "src_y0=0, src_y1=height" (NO Flip) y salia invertido.
        # Por lo tanto, debemos invertirlo.
        must_flip_y = is_software or (not self.bottom_left_origin)

        # Para HW rendering: usar las dimensiones reales del FBO como fuente del blit.
        # El core puede reportar en video_refresh las dimensiones BASE (sin upscale)
        # aunque haya renderizado a un FBO upscaled → usar fbo_width/fbo_height evita
        # que el blit lea solo una fracción del FBO y muestre la imagen cortada.
        # Para SW rendering: width/height del callback corresponden exactamente a los
        # píxeles subidos a la textura → se usan directamente.
        if not is_software and self.fbo_width > 0 and self.fbo_height > 0:
            blit_w = self.fbo_width
            blit_h = self.fbo_height
        else:
            blit_w = width
            blit_h = height

        # Log solo en el primer frame para diagnóstico
        if self.fbo_id and not hasattr(self, '_blit_logged'):
            self._blit_logged = True
            print(f"[BLIT] is_sw={is_software} callback=({width}x{height}) "
                  f"fbo=({self.fbo_width}x{self.fbo_height}) "
                  f"src=({blit_w}x{blit_h}) dst={self.view_rect}")

        # Coordenadas Y de origen para el blit
        src_y0 = 0
        src_y1 = blit_h
        
        # Si hay que invertir verticalmente, intercambiar las coordenadas Y de origen
        if must_flip_y:
             src_y0 = blit_h
             src_y1 = 0
        
        # Ejecutar el blit: copiar el contenido del FBO fuente al rectángulo destino
        # con escalado bilineal (GL_LINEAR) para suavizar la imagen
        glBlitFramebuffer(0, src_y0, blit_w, src_y1, 
                          dst_x, dst_y, dst_x + dst_w, dst_y + dst_h, 
                          GL_COLOR_BUFFER_BIT, GL_LINEAR)
        
        # Desvincular el framebuffer de lectura
        glBindFramebuffer(GL_READ_FRAMEBUFFER, 0)

    # Callback principal para la comunicación bidireccional entre el núcleo y el frontend (este script).
    # Maneja comandos para configuración, directorios, renderizado, logs y capacidades del sistema.
    def environment(self, cmd, data):
        # El core solicita el directorio de sistema (BIOS, firmware, etc.)
        if cmd == RETRO_ENVIRONMENT_GET_SYSTEM_DIRECTORY:
            sys_dir = os.path.abspath("./system").encode('utf-8')
            if not os.path.exists("./system"):
                os.makedirs("./system")
            # Escribir la ruta en el puntero que nos pasa el core
            p_str = ctypes.cast(data, ctypes.POINTER(ctypes.c_char_p))
            p_str[0] = sys_dir
            print(f"Environment: System Directory -> {sys_dir}")
            return True
        
        # El core informa del formato de píxel que usará para el video
        elif cmd == RETRO_ENVIRONMENT_SET_PIXEL_FORMAT:
            p_fmt = ctypes.cast(data, ctypes.POINTER(ctypes.c_int))
            self.pixel_format = p_fmt[0]
            print(f"Environment: Set Pixel Format -> {p_fmt[0]}")
            return True

        # El core solicita el directorio de guardado (SRAM, saves, etc.)
        elif cmd == RETRO_ENVIRONMENT_GET_SAVE_DIRECTORY:
            # Citra almacena en el directorio de saves toda su estructura de usuario
            # (NAND, shaders, config binario, sdmc...). La redirigimos a system/ para
            # separar datos del sistema de los saves reales de los juegos DS.
            if 'citra' in self.lib_path.lower():
                target_dir = os.path.abspath("./system")
            else:
                target_dir = os.path.abspath("./saves")
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)
            save_dir = target_dir.encode('utf-8')
            p_str = ctypes.cast(data, ctypes.POINTER(ctypes.c_char_p))
            p_str[0] = save_dir
            return True

        # El core solicita la interfaz de log para enviar mensajes de depuración
        elif cmd == RETRO_ENVIRONMENT_GET_LOG_INTERFACE:
            # Asignar nuestro callback de log a la estructura del core
            cb_struct = ctypes.cast(data, ctypes.POINTER(RetroLogCallback))
            cb_struct.contents.log = ctypes.cast(self.log_cb, ctypes.c_void_p)
            print("[ENV] GET_LOG_INTERFACE -> Callback de log asignado")
            return True

        # El core consulta el valor de una opción de configuración (idioma, región, etc.)
        elif cmd == RETRO_ENVIRONMENT_GET_VARIABLE:
            var = ctypes.cast(data, ctypes.POINTER(RetroVariable)).contents
            key = var.key.decode('utf-8') if var.key else ''
            if key in self.core_options:
                val = self.core_options[key].encode('utf-8')
                # Mantener referencia para evitar que el GC libere la memoria
                # antes de que el core la lea.
                self._option_refs[key] = ctypes.c_char_p(val)
                var.value = self._option_refs[key]
                return True
            # Si la opción no está configurada, devolver None
            var.value = None
            return True

        # El core solicita configurar renderizado por hardware (OpenGL).
        # Se asignan los callbacks de get_framebuffer y get_proc_address.
        elif cmd == RETRO_ENVIRONMENT_SET_HW_RENDER:
            hw = ctypes.cast(data, ctypes.POINTER(RetroHWRenderCallback)).contents
            # Asignar las funciones que el core usará para obtener el FBO y resolver funciones GL
            hw.get_current_framebuffer = c_hw_get_current_framebuffer_t(get_current_framebuffer_callback)
            hw.get_proc_address = c_hw_get_proc_address_t(get_proc_address_callback)

            # Guardar el callback de reinicio de contexto y las opciones de renderizado
            self.context_reset_cb = hw.context_reset
            self.hw_render_depth = hw.depth
            self.hw_render_stencil = hw.stencil
            self.bottom_left_origin = hw.bottom_left_origin

            # Guardar referencias para que el GC no libere los punteros a función
            self._hw_refs.append((hw.get_current_framebuffer, hw.get_proc_address))
            print("Environment: Set HW Render (Aceptado)")
            return True

        elif cmd == RETRO_ENVIRONMENT_SET_SYSTEM_AV_INFO:
            # El core solicita actualizar toda la info AV (resolución + timing).
            # Ocurre típicamente al cambiar de renderizador SW→GL.
            av = ctypes.cast(data, ctypes.POINTER(RetroSystemAVInfo)).contents
            new_w = av.geometry.base_width
            new_h = av.geometry.base_height
            new_ar = av.geometry.aspect_ratio
            new_sr = av.timing.sample_rate
            print(f"[ENV] SET_SYSTEM_AV_INFO → {new_w}x{new_h} ar={new_ar:.4f} sr={new_sr:.0f}")
            self.base_width = new_w
            self.base_height = new_h
            self.aspect_ratio = new_ar
            self.input_manager.update_geometry(new_w, new_h, new_ar)
            self.last_win_size = (-1, -1)  # forzar recalculo del viewport
            # Recrear FBO con las dimensiones y flags depth/stencil actualizados.
            # Esto es seguro: estamos en el hilo GL (llamado desde paintGL → retro_run),
            # y el core llamaá su propio context_reset_cb DESPUÉS de este callback,
            # por lo que necesita el FBO válido ya disponible en get_current_framebuffer().
            self.init_framebuffer(new_w, new_h)
            # Diferir reinicio de audio (PyAudio crea hilos; hacerlo aquí es inseguro).
            if new_sr > 0 and int(new_sr) != self._current_sample_rate:
                self._pending_sample_rate = int(new_sr)
            return True

        # El core actualiza la geometría del video (resolución, aspect ratio) sin cambiar timing
        elif cmd == RETRO_ENVIRONMENT_SET_GEOMETRY:
            geo = ctypes.cast(data, ctypes.POINTER(RetroGameGeometry)).contents
            self.base_width = geo.base_width
            self.base_height = geo.base_height
            self.aspect_ratio = geo.aspect_ratio
            self.input_manager.update_geometry(geo.base_width, geo.base_height, geo.aspect_ratio)
            # Redimensionar el FBO si ya existe
            if self.fbo_id:
                  self.init_framebuffer(self.base_width, self.base_height)
            return True

        # El core consulta qué dispositivos de entrada soportamos (joypad, analog, puntero, ratón)
        elif cmd == RETRO_ENVIRONMENT_GET_INPUT_DEVICE_CAPABILITIES:
            # Crear una máscara de bits con los dispositivos soportados
            caps = (1 << RETRO_DEVICE_JOYPAD) | (1 << RETRO_DEVICE_ANALOG) | (1 << RETRO_DEVICE_POINTER) | (1 << RETRO_DEVICE_MOUSE)
            p_caps = ctypes.cast(data, ctypes.POINTER(ctypes.c_uint64))
            p_caps[0] = caps
            print(f"[ENV] GET_INPUT_DEVICE_CAPABILITIES -> Reportando caps: {bin(caps)}")
            return True

        # El core pregunta si alguna variable/opción ha sido modificada desde la última consulta
        elif cmd == RETRO_ENVIRONMENT_GET_VARIABLE_UPDATE:
            p_bool = ctypes.cast(data, ctypes.POINTER(ctypes.c_bool))
            p_bool[0] = self._variable_updated
            self._variable_updated = False   # Resetear el flag tras la consulta
            return True

        # El core consulta el idioma preferido del usuario
        elif cmd == RETRO_ENVIRONMENT_GET_LANGUAGE:
            p_lang = ctypes.cast(data, ctypes.POINTER(ctypes.c_uint))
            p_lang[0] = RETRO_LANGUAGE_SPANISH
            print("[ENV] GET_LANGUAGE -> Español (3)")
            return True

        # El core pregunta qué contexto de renderizado por hardware preferimos
        elif cmd == RETRO_ENVIRONMENT_GET_PREFERRED_HW_RENDER:
            p_uint = ctypes.cast(data, ctypes.POINTER(ctypes.c_uint))
            p_uint[0] = 1 # RETRO_HW_CONTEXT_OPENGL
            return True

        # El core pregunta qué versión de opciones soportamos (V2 = más rica en metadatos)
        elif cmd == RETRO_ENVIRONMENT_GET_CORE_OPTIONS_VERSION:
            p_uint = ctypes.cast(data, ctypes.POINTER(ctypes.c_uint))
            p_uint[0] = 2  # Soportamos SET_CORE_OPTIONS_V2
            return True

        # El core envía descriptores de entrada (nombres de botones). Aceptamos sin procesar.
        elif cmd == RETRO_ENVIRONMENT_SET_INPUT_DESCRIPTORS:
            return True

        # El core registra sus opciones de configuración (formato V1 con cadenas "desc; val1|val2|...")
        elif cmd == RETRO_ENVIRONMENT_SET_VARIABLES:
            # Parsear retro_variable[] (key + "desc; val1|val2|...")
            try:
                arr = ctypes.cast(data, ctypes.POINTER(RetroVariable))
                i = 0
                while arr[i].key:
                    key = arr[i].key.decode('utf-8')
                    raw = arr[i].value.decode('utf-8') if arr[i].value else ''
                    # Formato: "Description; val1|val2|val3"
                    desc, _, vals_str = raw.partition(';')
                    vals = [v.strip() for v in vals_str.strip().split('|')] if vals_str.strip() else []
                    self.available_options[key] = {
                        'desc': desc.strip(),
                        'values': vals,
                        'default': vals[0] if vals else '',
                    }
                    i += 1
                print(f"[ENV] SET_VARIABLES -> {len(self.available_options)} opciones registradas")
            except Exception as e:
                print(f"[ENV] SET_VARIABLES error parsing: {e}")
            return True

        # El core registra sus opciones con estructura retro_core_option_definition[] (V1 tipada)
        # El core registra sus opciones con estructura retro_core_option_definition[] (V1 tipada)
        elif cmd == RETRO_ENVIRONMENT_SET_CORE_OPTIONS:
            # Parsear retro_core_option_definition[]
            try:
                arr = ctypes.cast(data, ctypes.POINTER(RetroCoreOptionDefinition))
                i = 0
                while arr[i].key:
                    key = arr[i].key.decode('utf-8')
                    desc = arr[i].desc.decode('utf-8') if arr[i].desc else ''
                    default = arr[i].default_value.decode('utf-8') if arr[i].default_value else ''
                    vals = []
                    for v in arr[i].values:
                        if not v.value:
                            break
                        vals.append(v.value.decode('utf-8'))
                    self.available_options[key] = {
                        'desc': desc,
                        'values': vals,
                        'default': default or (vals[0] if vals else ''),
                    }
                    i += 1
                print(f"[ENV] SET_CORE_OPTIONS -> {len(self.available_options)} opciones registradas")
            except Exception as e:
                print(f"[ENV] SET_CORE_OPTIONS error parsing: {e}")
            return True

        # El core registra sus opciones con estructura V2 (más completa, con categorías)
        # El core registra sus opciones con estructura V2 (más completa, con categorías)
        elif cmd == RETRO_ENVIRONMENT_SET_CORE_OPTIONS_V2:
            # Parsear retro_core_options_v2
            try:
                opts_v2 = ctypes.cast(data, ctypes.POINTER(RetroCoreOptionsV2)).contents
                defs = opts_v2.definitions
                i = 0
                while defs[i].key:
                    key = defs[i].key.decode('utf-8')
                    desc = defs[i].desc.decode('utf-8') if defs[i].desc else ''
                    default = defs[i].default_value.decode('utf-8') if defs[i].default_value else ''
                    vals = []
                    for v in defs[i].values:
                        if not v.value:
                            break
                        vals.append(v.value.decode('utf-8'))
                    self.available_options[key] = {
                        'desc': desc,
                        'values': vals,
                        'default': default or (vals[0] if vals else ''),
                    }
                    i += 1
                print(f"[ENV] SET_CORE_OPTIONS_V2 -> {len(self.available_options)} opciones registradas")
            except Exception as e:
                print(f"[ENV] SET_CORE_OPTIONS_V2 error parsing: {e}")
            return True

        # Comando no reconocido: devolver False para indicar que no lo soportamos
        return False

    # Recibe un bloque de muestras de audio desde el núcleo y las envía al gestor de audio para su reproducción.
    def audio_sample_batch(self, data, frames):
        # Cada frame tiene 2 canales (estéreo) * 2 bytes (16 bits) = 4 bytes por frame
        size = frames * 4
        # Extraer los bytes de audio del puntero C y enviarlos al stream de PyAudio
        buf = ctypes.string_at(data, size)
        self.audio_manager.write(buf)
        return frames

    # Recibe una única muestra de audio estéreo (izquierda/derecha).
    # Actualmente no se usa porque preferimos la versión por lotes (batch) por rendimiento.
    def audio_sample(self, left, right):
        pass

    # Solicita al gestor de entrada que actualice el estado de los dispositivos (teclado, mouse, etc.).
    # Se llama una vez por frame antes de consultar los estados específicos.
    def input_poll(self):
        self.input_manager.poll()

    # Consulta el estado de un botón, eje o coordenada específica de un dispositivo de entrada.
    # Devuelve 1 si está presionado, 0 si no, o el valor del eje/coordenada.
    def input_state(self, port, device, index, id_val):
        return self.input_manager.get_state(port, device, index, id_val)
