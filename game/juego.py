import os
import json
import struct       # Para leer datos binarios de las ROMs (offsets, paletas, etc.)

from lista import Lista

# Intentar importar PIL (Pillow) para la extracción de iconos.
# Si no está instalado, la funcionalidad de iconos se desactiva.
try:
    from PIL import Image
    _PIL_DISPONIBLE = True
except ImportError:
    _PIL_DISPONIBLE = False

# Tamaño final de los iconos extraídos (se upscalean desde el original)
ICON_SIZE = 192


# Mapeo de extensiones de ROM a su core libretro correspondiente
EXTENSION_CORE_MAP = {
    ".3ds": "citra_libretro.dll",
    ".nds": "melondsds_libretro.dll",
    ".iso": "dolphin_libretro.dll",
    ".gcm": "dolphin_libretro.dll",
    ".wbfs": "dolphin_libretro.dll",
}

# Extensiones de ROM reconocidas
EXTENSIONES_VALIDAS = set(EXTENSION_CORE_MAP.keys())

# Ruta al fichero de nombres personalizados (se rellena en escanear_juegos)
_NOMBRES_PATH = None
# Ruta al directorio donde se almacenan los iconos extraídos de las ROMs
_ICONOS_DIR = None


# Carga el diccionario {nombre_archivo: titulo_custom} desde el JSON de nombres
def _cargar_nombres(ruta_games):
    path = os.path.join(ruta_games, "nombres.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


# Guarda el diccionario de nombres personalizados en el JSON
def _guardar_nombres(nombres):
    if _NOMBRES_PATH:
        with open(_NOMBRES_PATH, "w", encoding="utf-8") as f:
            json.dump(nombres, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
#  Extracción de iconos de ROMs
# ---------------------------------------------------------------------------

# Decodifica un índice Morton (Z-order curve) a coordenadas (x, y) dentro de un tile 8x8.
# Las consolas Nintendo usan este orden para almacenar los píxeles de los iconos en memoria.
def _morton_xy(i):
    x = (i & 1) | ((i >> 1) & 2) | ((i >> 2) & 4)
    y = ((i >> 1) & 1) | ((i >> 2) & 2) | ((i >> 3) & 4)
    return x, y


# Extrae el icono 32x32 de una ROM NDS desde su banner.
# El banner contiene un bitmap de 4 bits por píxel (4bpp) organizado en tiles,
# junto con una paleta de 16 colores en formato RGB555.
def _extraer_icono_nds(ruta_rom, ruta_destino):
    try:
        with open(ruta_rom, 'rb') as f:
            # Leer el offset del banner desde la cabecera del NDS (posición 0x68).
            # f.seek() mueve el cursor del archivo a esa posición.
            # struct.unpack('<I', ...) lee 4 bytes y los interpreta como un entero
            # unsigned de 32 bits en little-endian (el orden de bytes que usa la DS).
            f.seek(0x68)
            banner_offset = struct.unpack('<I', f.read(4))[0]
            if banner_offset == 0:
                return None

            # El bitmap del icono está en banner+0x20: 512 bytes (32x32 a 4bpp)
            # La paleta son los 32 bytes siguientes (16 colores × 2 bytes cada uno)
            f.seek(banner_offset + 0x20)
            bitmap = f.read(0x200)       # 0x200 = 512 bytes del bitmap
            palette_data = f.read(0x20)  # 0x20 = 32 bytes de la paleta

        # Decodificar la paleta RGB555: cada color ocupa 2 bytes (unsigned short).
        # Formato de cada color: 0BBBBBGGGGGRRRRR (5 bits por canal R, G, B).
        # Se escalan de 5 bits (0-31) a 8 bits (0-248) multiplicando con << 3.
        palette = []
        for i in range(16):   # 16 colores en la paleta
            # struct.unpack('<H', ...) lee 2 bytes como unsigned short little-endian
            c = struct.unpack('<H', palette_data[i * 2:i * 2 + 2])[0]
            r = (c & 0x1F) << 3              # Bits 0-4 = Rojo
            g = ((c >> 5) & 0x1F) << 3       # Bits 5-9 = Verde
            b = ((c >> 10) & 0x1F) << 3      # Bits 10-14 = Azul
            a = 0 if i == 0 else 255         # Color 0 = transparente (alpha=0)
            palette.append((r, g, b, a))

        # Decodificar el bitmap del icono.
        # El icono 32x32 está dividido en una cuadrícula de 4×4 tiles.
        # Cada tile es un bloque de 8×8 píxeles.
        # Dentro de cada tile, cada byte contiene 2 píxeles (4 bits = índice de paleta).
        img = Image.new('RGBA', (32, 32))    # Crear imagen vacía 32x32 con transparencia
        px = img.load()                       # px = acceso directo a los píxeles (px[x, y] = color)
        for ty in range(4):                   # ty = fila de tiles (0-3, recorre las 4 filas de tiles)
            for tx in range(4):               # tx = columna de tiles (0-3, recorre las 4 columnas)
                # Calcular dónde empiezan los datos de este tile en el bitmap
                tile_base = (ty * 4 + tx) * 32   # Cada tile ocupa 32 bytes (8×8÷2)
                for row in range(8):              # row = fila dentro del tile (0-7)
                    for col in range(0, 8, 2):    # col = columna, de 2 en 2 (cada byte = 2 píxeles)
                        byte = bitmap[tile_base + row * 4 + col // 2]
                        # Los 4 bits bajos del byte = primer píxel (izquierdo)
                        px[tx * 8 + col, ty * 8 + row] = palette[byte & 0xF]
                        # Los 4 bits altos del byte = segundo píxel (derecho)
                        px[tx * 8 + col + 1, ty * 8 + row] = palette[(byte >> 4) & 0xF]

        # Escalar el icono al tamaño final y guardarlo como PNG
        img = img.resize((ICON_SIZE, ICON_SIZE), Image.Resampling.NEAREST)
        img.save(ruta_destino)
        return ruta_destino
    except Exception as e:
        print(f"Error extrayendo icono NDS: {e}")
        return None


# Extrae el icono 48x48 de una ROM 3DS desde su SMDH.
# El icono está almacenado en formato RGB565 organizado en tiles 8x8
# con orden Morton (Z-order curve) para recorrer los píxeles.
def _extraer_icono_3ds(ruta_rom, ruta_destino):
    try:
        with open(ruta_rom, 'rb') as f:
            # Detectar si la ROM es NCSD (dump de cartucho completo) o NCCH (partición directa).
            # f.seek(0x100) mueve al offset donde está el magic number del formato.
            # f.read(4) lee los 4 bytes del identificador.
            f.seek(0x100)
            magic = f.read(4)

            if magic == b'NCSD':
                # NCSD: leer offset de la primera partición (en media units = ×0x200)
                f.seek(0x120)
                p0_off = struct.unpack('<I', f.read(4))[0] * 0x200
            elif magic == b'NCCH':
                # NCCH directo: la partición empieza en el offset 0
                p0_off = 0
            else:
                return None

            # Calcular offset del ExeFS (sistema de archivos ejecutable) dentro del NCCH
            f.seek(p0_off + 0x1A0)
            exefs_off = p0_off + struct.unpack('<I', f.read(4))[0] * 0x200

            # Buscar la entrada "icon" en la tabla de archivos del ExeFS.
            # La tabla tiene hasta 10 entradas, cada una con:
            #   - 8 bytes: nombre del archivo (rellenado con \x00)
            #   - 4 bytes: offset relativo dentro del ExeFS
            #   - 4 bytes: tamaño del archivo
            # f.read(8) lee el nombre, struct.unpack('<II', ...) lee offset y tamaño.
            # rstrip(b'\x00') elimina los bytes nulos del relleno del nombre.
            f.seek(exefs_off)
            icon_off = None
            for _ in range(10):    # Máximo 10 entradas en el ExeFS
                name = f.read(8).rstrip(b'\x00').decode('ascii', errors='ignore')
                off, sz = struct.unpack('<II', f.read(8))   # off = offset, sz = size
                if name == 'icon':
                    # El offset es relativo al inicio de datos del ExeFS (+0x200 por la cabecera)
                    icon_off = exefs_off + 0x200 + off
                    break

            if icon_off is None:
                return None

            # Verificar que el archivo encontrado es realmente un SMDH válido
            f.seek(icon_off)
            if f.read(4) != b'SMDH':
                return None

            # El icono grande (48x48) en formato RGB565 está en el offset 0x24C0 dentro del SMDH.
            # Cada píxel ocupa 2 bytes → 48 × 48 × 2 = 4608 bytes.
            f.seek(icon_off + 0x24C0)
            icon_data = f.read(48 * 48 * 2)

        # Decodificar los píxeles del icono 48x48.
        # El icono está dividido en una cuadrícula de 6×6 tiles (cada tile = 8×8 píxeles).
        # Dentro de cada tile, los 64 píxeles NO se recorren en orden normal (fila por fila),
        # sino en orden Morton/Z-order (un patrón en zigzag que mejora la caché de la GPU).
        # _morton_xy(i) convierte el índice secuencial (0-63) a las coordenadas (x,y) reales.
        img = Image.new('RGB', (48, 48))     # Crear imagen vacía 48x48 (sin transparencia)
        px = img.load()                       # px = acceso directo a los píxeles (px[x, y] = color)
        pos = 0                               # pos = posición actual en el array de bytes del icono
        for ty in range(6):                   # ty = fila de tiles (0-5, recorre las 6 filas)
            for tx in range(6):               # tx = columna de tiles (0-5, recorre las 6 columnas)
                for i in range(64):           # i = índice del píxel dentro del tile (0-63)
                    mx, my = _morton_xy(i)    # (mx, my) = coordenadas dentro del tile 8x8
                    # Leer 2 bytes como unsigned short e interpretar como RGB565:
                    # Bits 15-11 = Rojo (5 bits), Bits 10-5 = Verde (6 bits), Bits 4-0 = Azul (5 bits)
                    c = struct.unpack('<H', icon_data[pos:pos + 2])[0]
                    r = ((c >> 11) & 0x1F) << 3    # Rojo: 5 bits → escalado a 8 bits con << 3
                    g = ((c >> 5) & 0x3F) << 2     # Verde: 6 bits → escalado a 8 bits con << 2
                    b = (c & 0x1F) << 3             # Azul: 5 bits → escalado a 8 bits con << 3
                    # Posición final = (columna_tile × 8 + x_dentro_tile, fila_tile × 8 + y_dentro_tile)
                    px[tx * 8 + mx, ty * 8 + my] = (r, g, b)
                    pos += 2                        # Avanzar 2 bytes al siguiente píxel

        # Escalar el icono de 48x48 al tamaño final (192x192) usando interpolación
        # NEAREST (vecino más cercano) para mantener los píxeles nítidos sin difuminar.
        img = img.resize((ICON_SIZE, ICON_SIZE), Image.Resampling.NEAREST)
        img.save(ruta_destino)
        return ruta_destino
    except Exception as e:
        print(f"Error extrayendo icono 3DS: {e}")
        return None


# Extrae el icono de la ROM y devuelve la ruta al PNG generado.
# Usa caché: si el icono ya fue extraído previamente, reutiliza el archivo existente.
def _extraer_icono(juego):
    if not _PIL_DISPONIBLE or not _ICONOS_DIR:
        return None

    # Nombre del archivo PNG basado en el nombre de la ROM (sin extensión)
    nombre_png = os.path.splitext(juego.nombre_archivo)[0] + ".png"
    ruta_destino = os.path.join(_ICONOS_DIR, nombre_png)

    # Si ya existe el icono en caché, devolverlo directamente
    if os.path.exists(ruta_destino):
        return ruta_destino

    # Llamar al extractor correspondiente según la extensión de la ROM
    if juego.extension == '.nds':
        return _extraer_icono_nds(juego.ruta_juego, ruta_destino)
    elif juego.extension == '.3ds':
        return _extraer_icono_3ds(juego.ruta_juego, ruta_destino)
    return None


# Extrae el título interno completo almacenado dentro del archivo ROM.
# NDS: lee el título en inglés (UTF-16LE) del banner a partir del offset 0x240.
# 3DS: lee el título largo en inglés (UTF-16LE) del SMDH.
def extraer_titulo_rom(ruta_rom, extension):
    try:
        with open(ruta_rom, 'rb') as f:
            if extension == '.nds':
                # El banner NDS tiene títulos en 6 idiomas a partir del offset 0x240:
                # 0x240=JP, 0x340=EN, 0x440=FR, 0x540=DE, 0x640=IT, 0x740=ES
                # Cada título ocupa 256 bytes en UTF-16LE (128 caracteres)
                f.seek(0x68)
                banner_offset = struct.unpack('<I', f.read(4))[0]
                if banner_offset == 0:
                    # Si no hay banner, usar el código corto de 12 bytes de la cabecera como fallback
                    f.seek(0x000)
                    raw = f.read(12)
                    return raw.rstrip(b'\x00').decode('ascii', errors='replace').strip()

                # Leer el título en inglés (índice 1) del banner
                title_off = banner_offset + 0x240 + 1 * 0x100
                f.seek(title_off)
                raw = f.read(0x100)
                # Decodificar UTF-16LE y limpiar caracteres nulos
                titulo = raw.decode('utf-16-le', errors='replace').rstrip('\x00').strip()
                return titulo or None

            elif extension == '.3ds':
                # --- Localizar el SMDH (icono+metadatos) dentro de la ROM 3DS ---
                # El proceso es igual que en _extraer_icono_3ds:
                # 1) Detectar formato NCSD (dump completo) o NCCH (partición directa)
                # 2) Encontrar el ExeFS → buscar la entrada "icon" → leer el SMDH

                # Leer el magic number en offset 0x100 para saber el formato de la ROM
                f.seek(0x100)
                magic = f.read(4)
                if magic == b'NCSD':
                    # NCSD (dump de cartucho): leer el offset de la primera partición NCCH.
                    # El offset está en 0x120 en "media units" (1 media unit = 0x200 bytes).
                    f.seek(0x120)
                    p0_off = struct.unpack('<I', f.read(4))[0] * 0x200
                elif magic == b'NCCH':
                    # NCCH directo: la partición empieza al inicio del archivo
                    p0_off = 0
                else:
                    return None

                # Leer el offset del ExeFS desde la cabecera NCCH (offset relativo + 0x1A0).
                # El valor leído está en media units, así que se multiplica por 0x200.
                f.seek(p0_off + 0x1A0)
                exefs_off = p0_off + struct.unpack('<I', f.read(4))[0] * 0x200

                # Recorrer la tabla de archivos del ExeFS (hasta 10 entradas) buscando "icon".
                # Cada entrada tiene: 8 bytes (nombre) + 4 bytes (offset) + 4 bytes (tamaño).
                f.seek(exefs_off)
                icon_off = None
                for _ in range(10):
                    # Leer nombre del archivo (8 bytes ASCII, rellenado con \x00)
                    name = f.read(8).rstrip(b'\x00').decode('ascii', errors='ignore')
                    # Leer offset relativo y tamaño (ambos unsigned int 32-bit little-endian)
                    off, sz = struct.unpack('<II', f.read(8))
                    if name == 'icon':
                        # El contenido real empieza 0x200 bytes después del inicio del ExeFS
                        # (la tabla de entradas ocupa los primeros 0x200 bytes)
                        icon_off = exefs_off + 0x200 + off
                        break
                if icon_off is None:
                    return None

                # Verificar que el archivo "icon" es realmente un SMDH (magic = "SMDH")
                f.seek(icon_off)
                if f.read(4) != b'SMDH':
                    return None

                # --- Leer el título del juego desde el SMDH ---
                # El SMDH contiene 16 entradas de idioma a partir del offset 0x08:
                #   Índices: 0=JP, 1=EN, 2=FR, 3=DE, 4=IT, 5=ES, 6=CN_S, 7=KR, etc.
                # Cada entrada ocupa 0x200 bytes distribuidos así:
                #   0x000-0x07F: título corto (64 chars UTF-16LE = 0x80 bytes)
                #   0x080-0x17F: título largo (128 chars UTF-16LE = 0x100 bytes)
                #   0x180-0x1FF: publisher (64 chars UTF-16LE = 0x80 bytes)
                # Usamos el índice 1 (inglés) para obtener el título
                entry_off = icon_off + 0x08 + 1 * 0x200
                # Leer el título largo (0x100 bytes = 128 caracteres UTF-16LE) desde offset 0x80
                f.seek(entry_off + 0x80)
                raw = f.read(0x100)
                # Decodificar UTF-16LE y eliminar caracteres nulos sobrantes
                titulo = raw.decode('utf-16-le', errors='replace').rstrip('\x00').strip()
                return titulo or None
    except Exception as e:
        print(f"Error extrayendo título de ROM: {e}")
        return None


# Clase principal que representa un juego (ROM) en el emulador.
# Contiene la información del archivo, la consola detectada, el core asociado y el título.
class Game:
    # Diccionario compartido por todas las instancias para almacenar nombres personalizados
    _nombres_custom = {}

    # Constructor: recibe la ruta al archivo ROM y la carpeta de cores
    def __init__(self, ruta_juego, ruta_cores):
        self.ruta_juego = ruta_juego                                      # Ruta completa al archivo ROM
        self.nombre_archivo = os.path.basename(ruta_juego)                # Nombre del archivo (con extensión)
        self._titulo_default = os.path.splitext(self.nombre_archivo)[0]   # Título por defecto (nombre sin extensión)
        self.extension = os.path.splitext(ruta_juego)[1].lower()          # Extensión en minúsculas (.nds, .3ds, etc.)
        self.consola = self._detectar_consola()                           # Nombre de la consola detectada
        self.ruta_core = self._detectar_core(ruta_cores)                  # Ruta al core libretro correspondiente
        self.imagen = None                                                # Ruta a la carátula (portada del scraper)
        self.imagen_rom = None                                            # Icono extraído directamente de la ROM

    # Devuelve el título personalizado si existe, o el título por defecto
    @property
    def titulo(self):
        return Game._nombres_custom.get(self.nombre_archivo, self._titulo_default)

    # Devuelve el nombre de la lista a la que pertenece el juego, o None
    @property
    def lista(self):
        return Lista.obtener_lista_de_juego(self.nombre_archivo)

    # Asigna el juego a una lista (None o SIN_LISTA para quitar)
    @lista.setter
    def lista(self, nombre_lista):
        Lista.asignar_juego(self.nombre_archivo, nombre_lista)

    # Setter del título: guarda el nombre personalizado o lo elimina si es igual al por defecto
    @titulo.setter
    def titulo(self, nuevo_titulo):
        nuevo_titulo = nuevo_titulo.strip()
        if nuevo_titulo and nuevo_titulo != self._titulo_default:
            Game._nombres_custom[self.nombre_archivo] = nuevo_titulo
        else:
            Game._nombres_custom.pop(self.nombre_archivo, None)
        _guardar_nombres(Game._nombres_custom)

    # Detecta la consola según la extensión del archivo ROM
    def _detectar_consola(self):
        mapa = {
            ".3ds": "Nintendo 3DS",
            ".nds": "Nintendo DS",
            ".iso": "GameCube / Wii",
            ".gcm": "GameCube",
            ".wbfs": "Wii",
        }
        return mapa.get(self.extension, "Desconocida")

    # Detecta la ruta al core libretro según la extensión del archivo ROM
    def _detectar_core(self, ruta_cores):
        core_file = EXTENSION_CORE_MAP.get(self.extension)
        if core_file:
            return os.path.join(ruta_cores, core_file)
        return None

    # Devuelve el conjunto de nombres de archivo ROM presentes en la carpeta de juegos
    @staticmethod
    def obtener_archivos_rom(ruta_games):
        archivos = set()
        if os.path.isdir(ruta_games):
            for archivo in os.listdir(ruta_games):
                ext = os.path.splitext(archivo)[1].lower()
                if ext in EXTENSIONES_VALIDAS:
                    archivos.add(archivo)
        return archivos

    # Detecta archivos renombrados comparando el set de archivos antes y después.
    # Migra los nombres personalizados, iconos y asignaciones de listas al nuevo nombre.
    @staticmethod
    def migrar_renombrados(ruta_games, archivos_antes, archivos_despues):
        eliminados = archivos_antes - archivos_despues
        nuevos = archivos_despues - archivos_antes

        if not eliminados or not nuevos:
            return

        # Agrupar archivos eliminados y nuevos por extensión para emparejar renombrados
        elim_por_ext = {}
        for f in eliminados:
            ext = os.path.splitext(f)[1].lower()
            elim_por_ext.setdefault(ext, []).append(f)

        nuevo_por_ext = {}
        for f in nuevos:
            ext = os.path.splitext(f)[1].lower()
            nuevo_por_ext.setdefault(ext, []).append(f)

        iconos_dir = os.path.join(ruta_games, "icons")
        cambios = False

        for ext, lista_elim in elim_por_ext.items():
            lista_nuevo = nuevo_por_ext.get(ext, [])
            # Solo migrar si hay exactamente un eliminado y un nuevo con la misma extensión
            if len(lista_elim) == 1 and len(lista_nuevo) == 1:
                viejo = lista_elim[0]
                nuevo = lista_nuevo[0]

                # Migrar nombre personalizado del archivo viejo al nuevo
                if viejo in Game._nombres_custom:
                    Game._nombres_custom[nuevo] = Game._nombres_custom.pop(viejo)
                    cambios = True

                # Migrar archivo de icono al nuevo nombre
                viejo_png = os.path.splitext(viejo)[0] + ".png"
                nuevo_png = os.path.splitext(nuevo)[0] + ".png"
                viejo_icon = os.path.join(iconos_dir, viejo_png)
                nuevo_icon = os.path.join(iconos_dir, nuevo_png)
                if os.path.exists(viejo_icon):
                    try:
                        os.rename(viejo_icon, nuevo_icon)
                    except OSError:
                        pass

                # Migrar la asignación de lista al nuevo nombre de archivo
                Lista.migrar_renombrado(viejo, nuevo)

        if cambios:
            _guardar_nombres(Game._nombres_custom)

    # Escanea la carpeta de juegos y devuelve una lista de objetos Game.
    # Inicializa las rutas globales, carga nombres personalizados y listas,
    # y extrae los iconos de cada ROM encontrada.
    @staticmethod
    def escanear_juegos(ruta_games, ruta_cores):
        global _NOMBRES_PATH, _ICONOS_DIR
        _NOMBRES_PATH = os.path.join(ruta_games, "nombres.json")
        _ICONOS_DIR = os.path.join(ruta_games, "icons")
        os.makedirs(_ICONOS_DIR, exist_ok=True)
        # Cargar nombres personalizados y listas desde disco
        Game._nombres_custom = _cargar_nombres(ruta_games)
        Lista.cargar(ruta_games)

        juegos = []
        if not os.path.isdir(ruta_games):
            return juegos
        # Recorrer archivos ordenados alfabéticamente
        for archivo in sorted(os.listdir(ruta_games)):
            ext = os.path.splitext(archivo)[1].lower()
            if ext in EXTENSIONES_VALIDAS:
                ruta_completa = os.path.join(ruta_games, archivo)
                juego = Game(ruta_completa, ruta_cores)
                # Extraer el icono de la ROM (se cachea en disco)
                icono = _extraer_icono(juego)
                juego.imagen = icono          # Imagen mostrada (puede ser reemplazada por portada del scraper)
                juego.imagen_rom = icono      # Icono original de la ROM (se conserva siempre)
                juegos.append(juego)
        return juegos

