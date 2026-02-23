import os
import json


# Nombre especial para juegos sin lista asignada
SIN_LISTA = "Sin Lista"

# Ruta al fichero de listas (se rellena en cargar)
_LISTAS_PATH = None


class Lista:
    """Representa una lista/categoría de juegos (ej: 'Favoritos', 'RPG', etc.)."""

    # Datos compartidos: {nombre_lista: [nombre_archivo, ...]}
    _datos = {}

    def __init__(self, nombre):
        self.nombre = nombre

    @staticmethod
    def cargar(ruta_games):
        """Carga las listas desde listas.json."""
        global _LISTAS_PATH
        _LISTAS_PATH = os.path.join(ruta_games, "listas.json")
        if os.path.exists(_LISTAS_PATH):
            try:
                with open(_LISTAS_PATH, "r", encoding="utf-8") as f:
                    Lista._datos = json.load(f)
            except Exception:
                Lista._datos = {}
        else:
            Lista._datos = {}

    @staticmethod
    def guardar():
        """Guarda las listas en listas.json."""
        if _LISTAS_PATH:
            try:
                with open(_LISTAS_PATH, "w", encoding="utf-8") as f:
                    json.dump(Lista._datos, f, ensure_ascii=False, indent=2)
            except Exception:
                pass

    @staticmethod
    def obtener_nombres():
        """Devuelve la lista ordenada de nombres de listas creadas."""
        return sorted(Lista._datos.keys())

    @staticmethod
    def crear_lista(nombre):
        """Crea una nueva lista vacía si no existe."""
        nombre = nombre.strip()
        if nombre and nombre != SIN_LISTA and nombre not in Lista._datos:
            Lista._datos[nombre] = []
            Lista.guardar()

    @staticmethod
    def eliminar_lista(nombre):
        """Elimina una lista (los juegos pasan a Sin Lista)."""
        if nombre in Lista._datos:
            del Lista._datos[nombre]
            Lista.guardar()

    @staticmethod
    def obtener_lista_de_juego(nombre_archivo):
        """Devuelve el nombre de la lista a la que pertenece un juego, o None."""
        for nombre_lista, archivos in Lista._datos.items():
            if nombre_archivo in archivos:
                return nombre_lista
        return None

    @staticmethod
    def asignar_juego(nombre_archivo, nombre_lista):
        """Asigna un juego a una lista. Si nombre_lista es None o SIN_LISTA, lo quita."""
        # Quitar de cualquier lista actual
        for archivos in Lista._datos.values():
            if nombre_archivo in archivos:
                archivos.remove(nombre_archivo)

        # Añadir a la nueva lista (si no es Sin Lista)
        if nombre_lista and nombre_lista != SIN_LISTA:
            if nombre_lista not in Lista._datos:
                Lista._datos[nombre_lista] = []
            Lista._datos[nombre_lista].append(nombre_archivo)

        Lista.guardar()

    @staticmethod
    def obtener_juegos_de_lista(nombre_lista, todos_los_juegos):
        """Devuelve los juegos que pertenecen a una lista.
        Si nombre_lista es SIN_LISTA, devuelve los que no están en ninguna."""
        if nombre_lista == SIN_LISTA:
            asignados = set()
            for archivos in Lista._datos.values():
                asignados.update(archivos)
            return [j for j in todos_los_juegos if j.nombre_archivo not in asignados]
        elif nombre_lista in Lista._datos:
            archivos_en_lista = set(Lista._datos[nombre_lista])
            return [j for j in todos_los_juegos if j.nombre_archivo in archivos_en_lista]
        return []

    @staticmethod
    def obtener_todas_con_sin_lista():
        """Devuelve [SIN_LISTA] + listas ordenadas."""
        return [SIN_LISTA] + sorted(Lista._datos.keys())

    @staticmethod
    def migrar_renombrado(viejo, nuevo):
        """Migra un archivo renombrado en las listas."""
        for archivos in Lista._datos.values():
            if viejo in archivos:
                idx = archivos.index(viejo)
                archivos[idx] = nuevo
                Lista.guardar()
                return
