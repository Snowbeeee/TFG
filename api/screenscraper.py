import os
import json
import hashlib
import zlib
import urllib.request
import urllib.parse
import urllib.error

# Mapeo de extensiones a system IDs de ScreenScraper
# Verificar en: api2/systemesListe.php
SYSTEM_IDS = {
    ".nds": 15,   # Nintendo DS
    ".3ds": 17,   # Nintendo 3DS
}

CACHE_DIR_NAME = "scraper_cache" 
CACHE_INFO_FILE = "info.json"

# Clase principal para interactuar con la API de ScreenScraper, 
# incluyendo métodos para buscar juegos por hash o nombre, descargar imágenes 
# y manejar la caché local.
class ScreenScraperAPI:

    BASE_URL = "https://api.screenscraper.fr/api2"

    def __init__(self, devid, devpassword, softname="TFG-Emulador"):
        self.devid = devid
        self.devpassword = devpassword
        self.softname = softname

    # Parametros base que se requiere poner en la url para las llamadas a la API
    def _parametros_base(self, extra=None):
        params = {
            "devid": self.devid,
            "devpassword": self.devpassword,
            "softname": self.softname,
            "output": "json",
        }
        if extra:
            params.update(extra)
        return params

    # LLamada a la API (concretamente a jeuInfos.php), busqueda por hash del 
    # contenodo del fichero ROM 
    def buscar_por_hash(self, ruta_rom, extension):
        if not os.path.isfile(ruta_rom):
            return None

        nombre_rom = os.path.basename(ruta_rom)
        taille = os.path.getsize(ruta_rom)

        # Calcular hashes en una sola pasada
        crc_val = 0
        md5 = hashlib.md5()
        sha1 = hashlib.sha1()
        
        # Con el with se asegura de cerrar la conexión automáticamente
        with open(ruta_rom, 'rb') as archivo_rom:
            # Se lee el archivo en bloques de 1 MB para no cargarlo todo en memoria
            while True:
                bloque = archivo_rom.read(1 << 20)  # 1 MB
                if not bloque:
                    break
                crc_val = zlib.crc32(bloque, crc_val)
                
                # El update funciona de la misma forma que un += pero para hashes
                md5.update(bloque)
                sha1.update(bloque)
        
        # Formatear hashes como hexadecimales ya que la API asi lo espera       
        crc_hex = format(crc_val & 0xFFFFFFFF, '08X')
        md5_hex = md5.hexdigest().upper()
        sha1_hex = sha1.hexdigest().upper()

        print(f"[ScreenScraper] Hashes de '{nombre_rom}': CRC={crc_hex}, MD5={md5_hex[:16]}…, SHA1={sha1_hex[:16]}…")

        # Parametros extra para la llamada a la API de la busqueda por hash
        extra = {
            "crc": crc_hex,
            "md5": md5_hex,
            "sha1": sha1_hex,
            "romnom": nombre_rom,
            "romtaille": str(taille),
            "romtype": "rom",
        }
        
        # Se comprueba que le extension se encuentre en SYSTEM_IDS para poder diferenciar
        # las distintas extensiones de juegos
        if extension and extension in SYSTEM_IDS:
            extra["systemeid"] = str(SYSTEM_IDS[extension])

        params = self._parametros_base(extra)
    
        # Construir la URL
        # urlencode se encarga de formatear los parametros para que internet lo entienda
        url = f"{self.BASE_URL}/jeuInfos.php?{urllib.parse.urlencode(params)}"

        # Realizar la solicitud HTTP
        try:
            # Se añade un User-Agent personalizado para evitar bloqueos por parte del servidor
            request = urllib.request.Request(url, headers={"User-Agent": self.softname})
            
            with urllib.request.urlopen(request, timeout=30) as respuesta:
                status = respuesta.getcode()
                print(f"[ScreenScraper] jeuInfos HTTP {status} para '{nombre_rom}'")
                
                contenido_crudo = respuesta.read().decode("utf-8")
                datos_respuesta = json.loads(contenido_crudo)
        
        # Control de errores HTTP para obtener información útil en caso de fallo
        except urllib.error.HTTPError as error_http:
            cuerpo_error = ""
            try:
                cuerpo_error = error_http.read().decode("utf-8", errors="ignore")[:300]
            except Exception:
                pass
            print(f"[ScreenScraper] jeuInfos HTTP {error_http.code}: {error_http.reason} | rom: '{nombre_rom}' | body: {cuerpo_error}")
            return None
        except Exception as error:
            print(f"[ScreenScraper] jeuInfos Error: {error}")
            return None

        return self._parsear_respuesta_hash_un_juego(datos_respuesta)

    # El endpoint de búsqueda por hash (jeuInfos.php) devuelve un solo juego, esta función parsea ese juego.
    def _parsear_respuesta_hash_un_juego(self, datos_respuesta):
        """Parsea la respuesta de jeuInfos.php (un solo juego, no una lista)."""
        try:
            juego = datos_respuesta.get("response", {}).get("jeu", {})
            if not juego:
                return None
            
            info = {
                "id": str(juego.get("id", "")),
                "titulo": _texto_regional(juego.get("noms"), "region",
                                          ["wor", "eu", "us", "ss"]),
                "descripcion": _texto_regional(juego.get("synopsis"), "langue",
                                               ["es", "en", "fr"]),
                "generos": _generos(juego.get("genres", [])),
                "fecha_lanzamiento": _texto_regional(juego.get("dates"), "region",
                                                     ["wor", "eu", "us", "jp"]),
                "consola": (juego.get("systeme", {}).get("text", "")
                            if isinstance(juego.get("systeme"), dict) else ""),
                "editeur": _safe(juego.get("editeur")),
                "developpeur": _safe(juego.get("developpeur")),
                "jugadores": _safe(juego.get("joueurs")),
                "medias": _medias(juego.get("medias", {})),
            }
            
            # Comprueba que la API fallo la llamada devolviendo un resultado vacío (sin id ni título)
            if not info["id"] and not info["titulo"]:
                print(f"[ScreenScraper] jeuInfos resultado vacío")
                return None
            
            return info
        except Exception as error:
            print(f"[ScreenScraper] Error parseando jeuInfos: {error}")
            return None

    # Llamada a la API, busqueda por nombre del juego
    def buscar_por_nombre(self, nombre, extension=None):
        # Parametros extra para la llamada a la API de la busqueda por nombre
        extra = {"recherche": nombre}
        
        # Se comprueba que la extension se encuentre en SYSTEM_IDS para poder diferenciar
        # las distintas extensiones de juegos
        if extension and extension in SYSTEM_IDS:
            extra["systemeid"] = str(SYSTEM_IDS[extension])

        params = self._params_base(extra)
        
        # Construir la URL
        # urlencode se encarga de formatear los parametros para que internet lo entienda
        url = f"{self.BASE_URL}/jeuRecherche.php?{urllib.parse.urlencode(params)}"

        # Realizar la solicitud HTTP
        try:
            # Se añade un User-Agent personalizado para evitar bloqueos por parte del servidor
            request = urllib.request.Request(url, headers={"User-Agent": self.softname})
            
            with urllib.request.urlopen(request, timeout=20) as respuesta:
                status = respuesta.getcode()
                contenido_crudo = respuesta.read().decode("utf-8")
                print(f"[ScreenScraper] HTTP {status} para búsqueda: '{extra.get('recherche', '')}'") 
                datos_respuesta = json.loads(contenido_crudo)
        
        # Control de errores HTTP para obtener información útil en caso de fallo
        except urllib.error.HTTPError as error_http:
            cuerpo_error = ""
            try:
                cuerpo_error = error_http.read().decode("utf-8", errors="ignore")[:300]
            except Exception:
                pass
            print(f"[ScreenScraper] HTTP {error_http.code}: {error_http.reason} | búsqueda: '{extra.get('recherche', '')}' | body: {cuerpo_error}")
            return None
        except Exception as error:
            print(f"[ScreenScraper] Error: {error}")
            return None

        return self._parsear_respuesta_nombre_varios_juegos(datos_respuesta)

    # El endpoint de búsqueda por nombre (en este caso jeuRecherche.php) devuelve una lista de juegos, 
    # esta función parsea esa lista y devuelve la info del primer juego (si hay resultados)
    def _parsear_respuesta_nombre_varios_juegos(self, datos_respuesta):
        try:
            jeux = datos_respuesta.get("response", {}).get("jeux", [])
            if not jeux:
                return None
            jeu = jeux[0]
            info = {
                "id": str(jeu.get("id", "")),
                "titulo": _texto_regional(jeu.get("noms"), "region",
                                          ["wor", "eu", "us", "ss"]),
                "descripcion": _texto_regional(jeu.get("synopsis"), "langue",
                                               ["es", "en", "fr"]),
                "generos": _generos(jeu.get("genres", [])),
                "fecha_lanzamiento": _texto_regional(jeu.get("dates"), "region",
                                                     ["wor", "eu", "us", "jp"]),
                "consola": (jeu.get("systeme", {}).get("text", "")
                            if isinstance(jeu.get("systeme"), dict) else ""),
                "editeur": _safe(jeu.get("editeur")),
                "developpeur": _safe(jeu.get("developpeur")),
                "jugadores": _safe(jeu.get("joueurs")),
                "medias": _medias(jeu.get("medias", {})),
            }
            # Comprueba que la API fallo la llamada devolviendo un resultado vacío (sin id ni título)
            if not info["id"] and not info["titulo"]:
                print(f"[ScreenScraper] Resultado vacío descartado")
                return None
            return info
        except Exception as error:
            print(f"[ScreenScraper] Error parseando: {error}")
            return None

    # Descarga imagenes de la API, dada la URL y la ruta destino local donde guardarla
    @staticmethod
    def descargar_imagen(url, ruta_destino):
        try:
            os.makedirs(os.path.dirname(ruta_destino), exist_ok=True)
            
            request = urllib.request.Request(url, headers={"User-Agent": "TFG-Emulador"})
            
            with urllib.request.urlopen(request, timeout=30) as respuesta:

                contenido = respuesta.read()

                # La API devuelve texto si no hay media
                if len(contenido) < 100:
                    texto = contenido.decode("utf-8", errors="ignore").strip()

                    if texto in ("CRCOK", "MD5OK", "SHA1OK", "NOMEDIA"):
                        return False
                    
                with open(ruta_destino, 'wb') as archivo:
                    archivo.write(contenido)
            
            return True
        except Exception as error:
            print(f"[ScreenScraper] Error descargando: {error}")
            return False


# ── Helpers de parseo ──

# Devuelve un texto de forma segura, manejando casos donde 
# el valor puede ser un dict con "text" o un string directo, o incluso None.
def _safe(valor):
    if isinstance(valor, dict):
        return valor.get("text", "")
    
    return str(valor) if valor else ""

# Esta funcion maneja la extracción de textos segun la región o idioma preferido, 
# tanto si los datos vienen como una lista de dicts o un dict con claves regionales
def _texto_regional(datos, clave, preferencias):
    if not datos:
        return ""
    
    if isinstance(datos, list):
        for preferencia in preferencias:
            for item in datos:
                if isinstance(item, dict) and item.get(clave) == preferencia:
                    return item.get("text", "")
                
        if datos and isinstance(datos[0], dict):
            return datos[0].get("text", "")
        
    elif isinstance(datos, dict):
        for preferencia in preferencias:
            for nombre_campo, valor_campo in datos.items():
                if nombre_campo.endswith(f"_{preferencia}"):
                    return valor_campo if isinstance(valor_campo, str) else ""
                
    return ""

# Extrae una lista de géneros a partir de la sección "genres" de la API, 
# manejando distintos formatos posibles
def _generos(datos_generos):
    resultado = []
    if isinstance(datos_generos, list):
        for genero in datos_generos:
            if not isinstance(genero, dict):
                continue
            nombres = genero.get("noms", [])
            nombre = _texto_regional(nombres, "langue", ["es", "en", "fr"])
            if nombre:
                resultado.append(nombre)
    return resultado


# Esta función maneja la extracción de URLs de medios, clasificando portadas y galerías,
def _medias(datos_medias):
    resultado = {"portada_url": None, "imagenes": []}
    if isinstance(datos_medias, list):
        for media in datos_medias:
            if not isinstance(media, dict):
                continue
            _clasificar(resultado, media.get("type", ""), media.get("url", ""), media.get("region", ""))
    elif isinstance(datos_medias, dict):
        _recorrer(datos_medias, resultado)
    return resultado

# Clasifica una URL de media como portada o imagen de galería según su tipo y región,
def _clasificar(resultado_medias, tipo, url, region):
    if not url:
        return
    tipo_normalizado = tipo.lower().replace("-", "").replace("_", "")
    es_portada = (tipo_normalizado in ("box2d", "boitier2d")
                  and "back" not in tipo_normalizado and "side" not in tipo_normalizado
                  and "texture" not in tipo_normalizado and "3d" not in tipo_normalizado
                  and "vierge" not in tipo_normalizado)
    tipos_excluidos = ("video", "manuel", "bezel", "theme", "p2k", "map", "box")
    if es_portada:
        if region in ("wor", "eu", "us", "ss") or resultado_medias["portada_url"] is None:
            resultado_medias["portada_url"] = url
    elif not any(excluido in tipo_normalizado for excluido in tipos_excluidos):
        resultado_medias["imagenes"].append({"url": url, "type": tipo, "region": region})


# Recorre recursivamente un dict de medias extrayendo URLs, 
# ignorando secciones de boitiers (fotos de caratulas de la caja fisica de juegos) (texture, 2d, 3d)
def _recorrer(diccionario_medias, resultado_medias):
    for clave, valor in diccionario_medias.items():
        # Ignorar secciones de boitiers (texture, 2d, 3d)
        if "boitier" in clave.lower():
            continue
        if isinstance(valor, str) and valor.startswith("http"):
            tipo = clave.replace("media_", "")
            region = ""
            for codigo_region in ("wor", "eu", "us", "jp", "fr", "de", "es", "it", "ss"):
                if clave.endswith(f"_{codigo_region}") or clave.endswith(f"({codigo_region})"):
                    region = codigo_region
                    break
            _clasificar(resultado_medias, tipo, valor, region)
        elif isinstance(valor, dict):
            _recorrer(valor, resultado_medias)


# ── Cache ──

# Esta funcion devuelve el directorio de caché para un juego concreto, 
# basado en la ruta de los juegos y el nombre del archivo ROM,
def obtener_cache_dir(ruta_games, nombre_archivo):
    base = os.path.splitext(nombre_archivo)[0]
    return os.path.join(ruta_games, CACHE_DIR_NAME, base)

# Carga la info cacheada de un juego, o None si no existe o está vacía.
def cargar_info_cache(ruta_games, nombre_archivo):
    ruta_cache = os.path.join(obtener_cache_dir(ruta_games, nombre_archivo), CACHE_INFO_FILE)
    if os.path.exists(ruta_cache):
        try:
            with open(ruta_cache, "r", encoding="utf-8") as archivo:
                datos = json.load(archivo)

            # Descartar cachés vacías (sin id ni título)
            # Esto significa que la API no devolvió nada
            if not datos.get("id") and not datos.get("titulo"):
                os.remove(ruta_cache)
                return None
            
            return datos
        except Exception:
            pass
    return None


 # Guarda la info de un juego en la caché, incluyendo la descarga de 
 # imágenes a partir de las URLs obtenidas de la API.
def guardar_info_cache(ruta_games, nombre_archivo, info):
    directorio = obtener_cache_dir(ruta_games, nombre_archivo)
    os.makedirs(directorio, exist_ok=True)
    with open(os.path.join(directorio, CACHE_INFO_FILE), "w", encoding="utf-8") as archivo:
        json.dump(info, archivo, ensure_ascii=False, indent=2)


# Esta funcion obtiene la ruta de la portada 
# (que siempre se guarda con el nombre "cover" seguido de su extensión) 
# dada la ruta de los juegos y el nombre del archivo ROM
def obtener_ruta_portada(ruta_games, nombre_archivo):
    directorio = obtener_cache_dir(ruta_games, nombre_archivo)
    for extension in (".png", ".jpg", ".jpeg"):
        ruta = os.path.join(directorio, f"cover{extension}")
        if os.path.exists(ruta):
            return ruta
    return None


# Esta función devuelve una lista de rutas a las imágenes de galería cacheadas,
# excluyendo la portada, dada la ruta de los juegos y el nombre del archivo ROM
# dada la ruta de los juegos y el nombre del archivo ROM. 
def obtener_rutas_galeria(ruta_games, nombre_archivo):
    directorio = obtener_cache_dir(ruta_games, nombre_archivo)
    rutas = []
    if os.path.isdir(directorio):
        for nombre_fichero in sorted(os.listdir(directorio)):
            if nombre_fichero.startswith("cover") or nombre_fichero == CACHE_INFO_FILE:
                continue
            if nombre_fichero.lower().endswith(('.png', '.jpg', '.jpeg')):
                rutas.append(os.path.join(directorio, nombre_fichero))
    return rutas
