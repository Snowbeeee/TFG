import os
import json
import struct

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
_ICONOS_DIR = None


def _cargar_nombres(ruta_games):
    """Carga el diccionario {nombre_archivo: titulo_custom} desde JSON."""
    path = os.path.join(ruta_games, "nombres.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _guardar_nombres(nombres):
    """Guarda el diccionario de nombres personalizados en JSON."""
    if _NOMBRES_PATH:
        with open(_NOMBRES_PATH, "w", encoding="utf-8") as f:
            json.dump(nombres, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
#  Extracción de iconos de ROMs
# ---------------------------------------------------------------------------

def _morton_xy(i):
    """Decodifica índice Morton/Z-order a (x, y) dentro de un tile 8x8."""
    x = (i & 1) | ((i >> 1) & 2) | ((i >> 2) & 4)
    y = ((i >> 1) & 1) | ((i >> 2) & 2) | ((i >> 3) & 4)
    return x, y


def _extraer_icono_nds(ruta_rom, ruta_destino):
    """Extrae el icono 32x32 de una ROM NDS (banner icon, 4bpp tiled + paleta RGB555)."""
    try:
        with open(ruta_rom, 'rb') as f:
            f.seek(0x68)
            banner_offset = struct.unpack('<I', f.read(4))[0]
            if banner_offset == 0:
                return None

            # Bitmap 32x32 4bpp (512 bytes) + paleta 16 colores (32 bytes)
            f.seek(banner_offset + 0x20)
            bitmap = f.read(0x200)
            palette_data = f.read(0x20)

        # Decodificar paleta RGB555
        palette = []
        for i in range(16):
            c = struct.unpack('<H', palette_data[i * 2:i * 2 + 2])[0]
            r = (c & 0x1F) << 3
            g = ((c >> 5) & 0x1F) << 3
            b = ((c >> 10) & 0x1F) << 3
            a = 0 if i == 0 else 255
            palette.append((r, g, b, a))

        # Decodificar bitmap: 4x4 tiles de 8x8, 2 píxeles por byte
        img = Image.new('RGBA', (32, 32))
        px = img.load()
        for ty in range(4):
            for tx in range(4):
                tile_base = (ty * 4 + tx) * 32
                for row in range(8):
                    for col in range(0, 8, 2):
                        byte = bitmap[tile_base + row * 4 + col // 2]
                        px[tx * 8 + col, ty * 8 + row] = palette[byte & 0xF]
                        px[tx * 8 + col + 1, ty * 8 + row] = palette[(byte >> 4) & 0xF]

        img = img.resize((ICON_SIZE, ICON_SIZE), Image.Resampling.NEAREST)
        img.save(ruta_destino)
        return ruta_destino
    except Exception as e:
        print(f"Error extrayendo icono NDS: {e}")
        return None


def _extraer_icono_3ds(ruta_rom, ruta_destino):
    """Extrae el icono 48x48 de una ROM 3DS (SMDH large icon, RGB565 tiled Morton)."""
    try:
        with open(ruta_rom, 'rb') as f:
            # Detectar NCSD (cart dump) o NCCH directo
            f.seek(0x100)
            magic = f.read(4)

            if magic == b'NCSD':
                f.seek(0x120)
                p0_off = struct.unpack('<I', f.read(4))[0] * 0x200
            elif magic == b'NCCH':
                p0_off = 0
            else:
                return None

            # ExeFS offset (media units relativo al NCCH)
            f.seek(p0_off + 0x1A0)
            exefs_off = p0_off + struct.unpack('<I', f.read(4))[0] * 0x200

            # Buscar entrada "icon" en la cabecera ExeFS
            f.seek(exefs_off)
            icon_off = None
            for _ in range(10):
                name = f.read(8).rstrip(b'\x00').decode('ascii', errors='ignore')
                off, sz = struct.unpack('<II', f.read(8))
                if name == 'icon':
                    icon_off = exefs_off + 0x200 + off
                    break

            if icon_off is None:
                return None

            # Verificar SMDH magic
            f.seek(icon_off)
            if f.read(4) != b'SMDH':
                return None

            # Icono grande 48x48 RGB565 (offset 0x24C0 dentro del SMDH)
            f.seek(icon_off + 0x24C0)
            icon_data = f.read(48 * 48 * 2)

        # Decodificar: 6x6 tiles de 8x8 con orden Morton
        img = Image.new('RGB', (48, 48))
        px = img.load()
        pos = 0
        for ty in range(6):
            for tx in range(6):
                for i in range(64):
                    mx, my = _morton_xy(i)
                    c = struct.unpack('<H', icon_data[pos:pos + 2])[0]
                    r = ((c >> 11) & 0x1F) << 3
                    g = ((c >> 5) & 0x3F) << 2
                    b = (c & 0x1F) << 3
                    px[tx * 8 + mx, ty * 8 + my] = (r, g, b)
                    pos += 2

        img = img.resize((ICON_SIZE, ICON_SIZE), Image.Resampling.NEAREST)
        img.save(ruta_destino)
        return ruta_destino
    except Exception as e:
        print(f"Error extrayendo icono 3DS: {e}")
        return None


def _extraer_icono(juego):
    """Extrae el icono de la ROM y devuelve la ruta al PNG (con caché)."""
    if not _PIL_DISPONIBLE or not _ICONOS_DIR:
        return None

    nombre_png = os.path.splitext(juego.nombre_archivo)[0] + ".png"
    ruta_destino = os.path.join(_ICONOS_DIR, nombre_png)

    # Si ya se extrajo antes, reusar
    if os.path.exists(ruta_destino):
        return ruta_destino

    if juego.extension == '.nds':
        return _extraer_icono_nds(juego.ruta_juego, ruta_destino)
    elif juego.extension == '.3ds':
        return _extraer_icono_3ds(juego.ruta_juego, ruta_destino)
    return None


class Juego:
    # Diccionario compartido por todas las instancias
    _nombres_custom = {}

    def __init__(self, ruta_juego, ruta_cores):
        self.ruta_juego = ruta_juego
        self.nombre_archivo = os.path.basename(ruta_juego)
        self._titulo_default = os.path.splitext(self.nombre_archivo)[0]
        self.extension = os.path.splitext(ruta_juego)[1].lower()
        self.consola = self._detectar_consola()
        self.ruta_core = self._detectar_core(ruta_cores)
        self.imagen = None  # Ruta a la carátula (de momento None)

    @property
    def titulo(self):
        return Juego._nombres_custom.get(self.nombre_archivo, self._titulo_default)

    @titulo.setter
    def titulo(self, nuevo_titulo):
        nuevo_titulo = nuevo_titulo.strip()
        if nuevo_titulo and nuevo_titulo != self._titulo_default:
            Juego._nombres_custom[self.nombre_archivo] = nuevo_titulo
        else:
            Juego._nombres_custom.pop(self.nombre_archivo, None)
        _guardar_nombres(Juego._nombres_custom)

    def _detectar_consola(self):
        mapa = {
            ".3ds": "Nintendo 3DS",
            ".nds": "Nintendo DS",
            ".iso": "GameCube / Wii",
            ".gcm": "GameCube",
            ".wbfs": "Wii",
        }
        return mapa.get(self.extension, "Desconocida")

    def _detectar_core(self, ruta_cores):
        core_file = EXTENSION_CORE_MAP.get(self.extension)
        if core_file:
            return os.path.join(ruta_cores, core_file)
        return None

    @staticmethod
    def escanear_juegos(ruta_games, ruta_cores):
        """Escanea la carpeta games/ y devuelve una lista de objetos Juego."""
        global _NOMBRES_PATH, _ICONOS_DIR
        _NOMBRES_PATH = os.path.join(ruta_games, "nombres.json")
        _ICONOS_DIR = os.path.join(ruta_games, "icons")
        os.makedirs(_ICONOS_DIR, exist_ok=True)
        Juego._nombres_custom = _cargar_nombres(ruta_games)

        juegos = []
        if not os.path.isdir(ruta_games):
            return juegos
        for archivo in sorted(os.listdir(ruta_games)):
            ext = os.path.splitext(archivo)[1].lower()
            if ext in EXTENSIONES_VALIDAS:
                ruta_completa = os.path.join(ruta_games, archivo)
                juego = Juego(ruta_completa, ruta_cores)
                juego.imagen = _extraer_icono(juego)
                juegos.append(juego)
        return juegos

