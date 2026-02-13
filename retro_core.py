import ctypes
import os
import sys
from retro_definitions import *
from OpenGL.GL import *
from OpenGL.GL.framebufferobjects import *

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

if os.name == 'nt':
    try:
        _gl_lib = ctypes.windll.opengl32
        _wgl_get_proc = _gl_lib.wglGetProcAddress
        _wgl_get_proc.restype = ctypes.c_void_p
        _wgl_get_proc.argtypes = [ctypes.c_char_p]
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
        
        self.lib_path = lib_path
        self.audio_manager = audio_manager
        self.input_manager = input_manager
        self.lib = ctypes.CDLL(lib_path)
        
        self.context_reset_cb = None
        self._hw_refs = [] # Para evitar GC
        
        print("Registrando input callbacks")
        
        # Instanciar callbacks
        self.video_cb = c_video_refresh_t(video_refresh_thunk)
        self.env_cb = c_environment_t(environment_thunk)
        self.audio_sample_cb = c_audio_sample_t(audio_sample_thunk)
        self.audio_batch_cb = c_audio_sample_batch_t(audio_sample_batch_thunk)
        self.input_poll_cb = c_input_poll_t(input_poll_thunk)
        self.input_state_cb = c_input_state_t(input_state_thunk)
        self.log_cb = c_log_printf_t(log_printf_thunk)
        
        # Setup inicial del core
        self.lib.retro_set_environment(self.env_cb)
        self.lib.retro_set_video_refresh(self.video_cb)
        self.lib.retro_set_audio_sample(self.audio_sample_cb)
        self.lib.retro_set_audio_sample_batch(self.audio_batch_cb)
        self.lib.retro_set_input_poll(self.input_poll_cb)
        self.lib.retro_set_input_state(self.input_state_cb)
        
        self.lib.retro_init()
        # Configurar puerto 0
        self.lib.retro_set_controller_port_device(0, RETRO_DEVICE_JOYPAD)
        
        # Configurar acceso a memoria (SRAM, RTC, etc)
        self.lib.retro_get_memory_data.restype = ctypes.c_void_p
        self.lib.retro_get_memory_data.argtypes = [ctypes.c_uint]

        self.lib.retro_get_memory_size.restype = ctypes.c_size_t
        self.lib.retro_get_memory_size.argtypes = [ctypes.c_uint]
        
        self.aspect_ratio = 0.0
        self.base_width = 0
        self.base_height = 0
        self.fbo_id = 0
        self.tex_id = 0
        self.rbo_id = 0
        self.view_rect = (0,0,1,1)
        self.hw_render_depth = False
        self.hw_render_stencil = False
        self.bottom_left_origin = True # Default GL
        self.last_win_size = (-1, -1)
        self.pixel_format = RETRO_PIXEL_FORMAT_0RGB1555 # Default
        self.fbo_width = 0
        self.fbo_height = 0
        self.target_fbo = None # None means auto-detect via glGetIntegerv

    def set_target_fbo(self, fbo):
        self.target_fbo = fbo

    # Devuelve el ID numérico del Framebuffer Object (FBO) actual.
    def get_framebuffer(self):
        return int(self.fbo_id)

    # Inicializa o reinicializa el Framebuffer Object (FBO) de OpenGL.
    # Crea las texturas y buffers de profundidad/stencil necesarios según la resolución del juego.
    def init_framebuffer(self, width, height):
        if self.fbo_id:
            glDeleteFramebuffers(1, [self.fbo_id])
        if self.tex_id:
            glDeleteTextures(1, [self.tex_id])
        if self.rbo_id:
            glDeleteRenderbuffers(1, [self.rbo_id])
            
        self.fbo_id = int(glGenFramebuffers(1))
        self.tex_id = int(glGenTextures(1))
        self.fbo_width = width
        self.fbo_height = height
        
        glBindFramebuffer(GL_FRAMEBUFFER, self.fbo_id)
        
        # Texture attachment (Color)
        glBindTexture(GL_TEXTURE_2D, self.tex_id)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, None)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, self.tex_id, 0)
        
        # Depth/Stencil attachment
        if self.hw_render_depth or self.hw_render_stencil:
            self.rbo_id = int(glGenRenderbuffers(1))
            glBindRenderbuffer(GL_RENDERBUFFER, self.rbo_id)
            if self.hw_render_depth and self.hw_render_stencil:
                glRenderbufferStorage(GL_RENDERBUFFER, GL_DEPTH24_STENCIL8, width, height)
                glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_DEPTH_STENCIL_ATTACHMENT, GL_RENDERBUFFER, self.rbo_id)
            elif self.hw_render_depth:
                glRenderbufferStorage(GL_RENDERBUFFER, GL_DEPTH_COMPONENT24, width, height)
                glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_RENDERBUFFER, self.rbo_id)
            
        status = glCheckFramebufferStatus(GL_FRAMEBUFFER)
        if status != GL_FRAMEBUFFER_COMPLETE:
            print(f"Error: Framebuffer incompleto (Status: {status})")
            
        glBindFramebuffer(GL_FRAMEBUFFER, 0)
        print(f"FBO Inicializado: {width}x{height} (ID: {self.fbo_id})")

    # Carga la partida guardada (SRAM) desde disco a la memoria del núcleo
    def load_sram(self):
        if not self.save_path:
            return
            
        size = self.lib.retro_get_memory_size(RETRO_MEMORY_SAVE_RAM)
        if size == 0:
            return
            
        if os.path.exists(self.save_path):
            with open(self.save_path, "rb") as f:
                data = f.read()
                if len(data) > size:
                    print(f"Warning: Save file larger than core memory ({len(data)} > {size}). Truncating.")
                    data = data[:size]
                
                ptr = self.lib.retro_get_memory_data(RETRO_MEMORY_SAVE_RAM)
                if ptr:
                    # Copiar datos
                    ctypes.memmove(ptr, data, len(data))
                    print(f"SRAM cargada desde {self.save_path}")

    # Guarda la partida (SRAM) de la memoria del núcleo al disco
    def save_sram(self):
        if not self.save_path:
            return
            
        size = self.lib.retro_get_memory_size(RETRO_MEMORY_SAVE_RAM)
        ptr = self.lib.retro_get_memory_data(RETRO_MEMORY_SAVE_RAM)
        
        if size > 0 and ptr:
            # Leer memoria
            data = ctypes.string_at(ptr, size)
            
            # Verificar si el directorio saves existe
            save_dir = os.path.dirname(self.save_path)
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)
                
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

        # Obtener info del sistema
        self.lib.retro_get_system_info.argtypes = [ctypes.POINTER(RetroSystemInfo)]
        sys_info = RetroSystemInfo()
        self.lib.retro_get_system_info(ctypes.byref(sys_info))
        print(f"Core cargado: {sys_info.library_name.decode()} ({sys_info.library_version.decode()})")
        
        full_path = os.path.abspath(rom_path).encode('utf-8')
        game_info = RetroGameInfo()
        game_info.path = full_path
        game_info.meta = None
        
        rom_data = None # Mantener referencia
        
        if sys_info.need_fullpath:
            game_info.data = None
            game_info.size = 0
        else:
            with open(rom_path, "rb") as f:
                rom_data = f.read()
            game_info.data = ctypes.cast(ctypes.create_string_buffer(rom_data), ctypes.c_void_p)
            game_info.size = len(rom_data)
        
        self.lib.retro_load_game.argtypes = [ctypes.POINTER(RetroGameInfo)]
        self.lib.retro_load_game.restype = ctypes.c_bool
        
        if not self.lib.retro_load_game(ctypes.byref(game_info)):
            print("Fallo al cargar el juego")
            return False
            
        print("Juego cargado exitosamente.")
        
        # Re-set controller port
        self.lib.retro_set_controller_port_device(0, RETRO_DEVICE_JOYPAD)
        
        if self.context_reset_cb:
            self.context_reset_cb()
            
        # AV Info
        self.lib.retro_get_system_av_info.argtypes = [ctypes.POINTER(RetroSystemAVInfo)]
        av_info = RetroSystemAVInfo()
        self.lib.retro_get_system_av_info(ctypes.byref(av_info))
        
        self.base_width = av_info.geometry.base_width
        self.base_height = av_info.geometry.base_height
        self.aspect_ratio = av_info.geometry.aspect_ratio

        # Configurar InputManager y Audio
        self.input_manager.update_geometry(self.base_width, self.base_height, self.aspect_ratio)
        self.audio_manager.init_stream(int(av_info.timing.sample_rate))
        
        # Inicializar FBO
        self.init_framebuffer(self.base_width, self.base_height)
        
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

        if self.aspect_ratio > 0:
            target_aspect = self.aspect_ratio
        else:
            target_aspect = self.base_width / self.base_height if self.base_height > 0 else 1.0
        
        window_aspect = win_width / win_height if win_height > 0 else 1.0

        if window_aspect > target_aspect:
            view_h = win_height
            view_w = win_height * target_aspect
        else:
            view_w = win_width
            view_h = win_width / target_aspect
        
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
        self.lib.retro_run()

    # Descarga el juego actual y desinicializa el núcleo, liberando recursos.
    def unload(self):
        # Guardar partida antes de descargar
        self.save_sram()
        
        self.lib.retro_unload_game()
        self.lib.retro_deinit()

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
            
            # Subir textura
            gl_fmt = GL_BGRA
            gl_type = GL_UNSIGNED_BYTE
            bpp = 4
            
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

            glBindTexture(GL_TEXTURE_2D, self.tex_id)
            
            # Asegurar alineación de 1 byte
            glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
            
            if pitch > 0:
                glPixelStorei(GL_UNPACK_ROW_LENGTH, pitch // bpp)
            
            glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, width, height, gl_fmt, gl_type, ctypes.c_void_p(data_addr))
            
            glPixelStorei(GL_UNPACK_ROW_LENGTH, 0)
            glPixelStorei(GL_UNPACK_ALIGNMENT, 4)
            glBindTexture(GL_TEXTURE_2D, 0)

        # Si no tenemos FBO (ni por HW init ni por SW init), salimos
        if self.fbo_id == 0: 
            return
        
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
        
        glBindFramebuffer(GL_READ_FRAMEBUFFER, self.fbo_id)
        glBindFramebuffer(GL_DRAW_FRAMEBUFFER, prev_fbo)
        
        # Si estamos dibujando en un FBO de Qt, NO debemos hacer glClear completo si no queremos borrar el fondo
        # Pero si el juego debe ocupar todo el área asignada, limpia el área de destino.
        # glClear afectará a TODO el framebuffer si no usamos Scissor.
        # Si prev_fbo es el widget, queremos limpiar solo el área del juego o todo el widget?
        # Normalmente todo el widget.
        
        glClearColor(0,0,0,1)
        glClear(GL_COLOR_BUFFER_BIT)
        
        dst_x, dst_y, dst_w, dst_h = self.view_rect
        
        # Calcular coordenadas de origen (flip vertical)
        # HW Render: Depende de bottom_left_origin (True = Normal, False = Flipped/Top-Left)
        # SW Render: Datos cargados Bottom-Up o Top-Down?
        # En la version anterior estaba "src_y0=0, src_y1=height" (NO Flip) y salia invertido.
        # Por lo tanto, debemos invertirlo.
        must_flip_y = is_software or (not self.bottom_left_origin)

        src_y0 = 0
        src_y1 = height # Usamos height del frame actual para mapear correctamente la textura
        
        if must_flip_y:
             src_y0 = height
             src_y1 = 0
        
        # Usamos 'width' del frame actual como ancho fuente
        glBlitFramebuffer(0, src_y0, width, src_y1, 
                          dst_x, dst_y, dst_x + dst_w, dst_y + dst_h, 
                          GL_COLOR_BUFFER_BIT, GL_LINEAR)
        
        glBindFramebuffer(GL_READ_FRAMEBUFFER, 0)

    # Callback principal para la comunicación bidireccional entre el núcleo y el frontend (este script).
    # Maneja comandos para configuración, directorios, renderizado, logs y capacidades del sistema.
    def environment(self, cmd, data):
        if cmd == RETRO_ENVIRONMENT_GET_SYSTEM_DIRECTORY:
            sys_dir = os.path.abspath("./system").encode('utf-8')
            if not os.path.exists("./system"):
                os.makedirs("./system")
            p_str = ctypes.cast(data, ctypes.POINTER(ctypes.c_char_p))
            p_str[0] = sys_dir
            print(f"Environment: System Directory -> {sys_dir}")
            return True
        
        elif cmd == RETRO_ENVIRONMENT_SET_PIXEL_FORMAT:
            p_fmt = ctypes.cast(data, ctypes.POINTER(ctypes.c_int))
            self.pixel_format = p_fmt[0]
            print(f"Environment: Set Pixel Format -> {p_fmt[0]}")
            return True

        elif cmd == RETRO_ENVIRONMENT_GET_SAVE_DIRECTORY:
            save_dir = os.path.abspath("./saves").encode('utf-8')
            if not os.path.exists("./saves"):
                os.makedirs("./saves")
            p_str = ctypes.cast(data, ctypes.POINTER(ctypes.c_char_p))
            p_str[0] = save_dir
            return True

        elif cmd == RETRO_ENVIRONMENT_GET_LOG_INTERFACE:
            cb_struct = ctypes.cast(data, ctypes.POINTER(RetroLogCallback))
            cb_struct.contents.log = ctypes.cast(self.log_cb, ctypes.c_void_p)
            print("[ENV] GET_LOG_INTERFACE -> Callback de log asignado")
            return True

        elif cmd == RETRO_ENVIRONMENT_GET_VARIABLE:
            var = ctypes.cast(data, ctypes.POINTER(RetroVariable)).contents
            var.value = None
            return True

        elif cmd == RETRO_ENVIRONMENT_SET_HW_RENDER:
            hw = ctypes.cast(data, ctypes.POINTER(RetroHWRenderCallback)).contents
            hw.get_current_framebuffer = c_hw_get_current_framebuffer_t(get_current_framebuffer_callback)
            hw.get_proc_address = c_hw_get_proc_address_t(get_proc_address_callback)
            
            self.context_reset_cb = hw.context_reset
            self.hw_render_depth = hw.depth
            self.hw_render_stencil = hw.stencil
            self.bottom_left_origin = hw.bottom_left_origin
            
            self._hw_refs.append((hw.get_current_framebuffer, hw.get_proc_address))
            print("Environment: Set HW Render (Aceptado)")
            return True

        elif cmd == RETRO_ENVIRONMENT_SET_GEOMETRY:
            geo = ctypes.cast(data, ctypes.POINTER(RetroGameGeometry)).contents
            self.base_width = geo.base_width
            self.base_height = geo.base_height
            self.aspect_ratio = geo.aspect_ratio
            self.input_manager.update_geometry(geo.base_width, geo.base_height, geo.aspect_ratio)
            # Resize FBO if needed
            if self.fbo_id:
                  self.init_framebuffer(self.base_width, self.base_height)
            return True

        elif cmd == RETRO_ENVIRONMENT_GET_INPUT_DEVICE_CAPABILITIES:
            caps = (1 << RETRO_DEVICE_JOYPAD) | (1 << RETRO_DEVICE_ANALOG) | (1 << RETRO_DEVICE_POINTER) | (1 << RETRO_DEVICE_MOUSE)
            p_caps = ctypes.cast(data, ctypes.POINTER(ctypes.c_uint64))
            p_caps[0] = caps
            print(f"[ENV] GET_INPUT_DEVICE_CAPABILITIES -> Reportando caps: {bin(caps)}")
            return True

        elif cmd == RETRO_ENVIRONMENT_GET_VARIABLE_UPDATE:
            p_bool = ctypes.cast(data, ctypes.POINTER(ctypes.c_bool))
            p_bool[0] = False
            return True

        elif cmd == RETRO_ENVIRONMENT_GET_PREFERRED_HW_RENDER:
            p_uint = ctypes.cast(data, ctypes.POINTER(ctypes.c_uint))
            p_uint[0] = 1 # RETRO_HW_CONTEXT_OPENGL
            return True

        elif cmd in [RETRO_ENVIRONMENT_SET_INPUT_DESCRIPTORS, RETRO_ENVIRONMENT_SET_VARIABLES, RETRO_ENVIRONMENT_SET_CORE_OPTIONS, RETRO_ENVIRONMENT_SET_CORE_OPTIONS_V2]:
            return True

        if cmd != RETRO_ENVIRONMENT_GET_VARIABLE_UPDATE:
            # print(f"[ENV] Comando NO MANEJADO: {cmd}")
            pass
        
        elif cmd == RETRO_ENVIRONMENT_SET_INPUT_DESCRIPTORS:

            print("[ENV] Registrando touchscreen descriptors")

            descriptors = (RetroInputDescriptor * 4)()

            descriptors[0] = RetroInputDescriptor(
                port=0,
                device=RETRO_DEVICE_POINTER,
                index=0,
                id=RETRO_DEVICE_ID_POINTER_X,
                description=b"Touch X"
            )

            descriptors[1] = RetroInputDescriptor(
                port=0,
                device=RETRO_DEVICE_POINTER,
                index=0,
                id=RETRO_DEVICE_ID_POINTER_Y,
                description=b"Touch Y"
            )

            descriptors[2] = RetroInputDescriptor(
                port=0,
                device=RETRO_DEVICE_POINTER,
                index=0,
                id=RETRO_DEVICE_ID_POINTER_PRESSED,
                description=b"Touch Press"
            )

            descriptors[3] = RetroInputDescriptor()  # terminador

            ctypes.memmove(data, descriptors, ctypes.sizeof(descriptors))

            return True
        
        return False

    # Recibe un bloque de muestras de audio desde el núcleo y las envía al gestor de audio para su reproducción.
    def audio_sample_batch(self, data, frames):
        size = frames * 4
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
