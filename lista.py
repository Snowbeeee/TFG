import os
import json


# Nombre especial para juegos sin lista asignada
SIN_LISTA = "Sin Lista"

# Ruta al fichero de listas (se rellena en cargar)
_LISTAS_PATH = None

# Representa una lista/categoría de juegos (ej: 'Favoritos', 'RPG', etc.).
class Lista:

    # Datos compartidos: {nombre_lista: [nombre_archivo, ...]}
    _datos = {}

    def __init__(self, nombre):
        self.nombre = nombre

    # Carga las listas desde listas.json.
    @staticmethod
    def cargar(ruta_games):
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

    # Guarda las listas en listas.json.
    @staticmethod
    def guardar():
        if _LISTAS_PATH:
            try:
                with open(_LISTAS_PATH, "w", encoding="utf-8") as f:
                    json.dump(Lista._datos, f, ensure_ascii=False, indent=2)
            except Exception:
                pass

    # Devuelve la lista ordenada de nombres de listas creadas.
    @staticmethod
    def obtener_nombres():
        return sorted(Lista._datos.keys())

    # Crea una nueva lista vacía si no existe.
    @staticmethod
    def crear_lista(nombre):
        nombre = nombre.strip()
        if nombre and nombre != SIN_LISTA and nombre not in Lista._datos:
            Lista._datos[nombre] = []
            Lista.guardar()

    # Elimina una lista (los juegos pasan a Sin Lista).
    @staticmethod
    def eliminar_lista(nombre):
        if nombre in Lista._datos:
            del Lista._datos[nombre]
            Lista.guardar()

    # Devuelve el nombre de la lista a la que pertenece un juego, o None.
    @staticmethod
    def obtener_lista_de_juego(nombre_archivo):
        for nombre_lista, archivos in Lista._datos.items():
            if nombre_archivo in archivos:
                return nombre_lista
        return None

    # Asigna un juego a una lista. Si nombre_lista es None o SIN_LISTA, lo quita.
    @staticmethod
    def asignar_juego(nombre_archivo, nombre_lista):
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

    # Devuelve los juegos que pertenecen a una lista.
    #    Si nombre_lista es SIN_LISTA, devuelve los que no están en ninguna.
    @staticmethod
    def obtener_juegos_de_lista(nombre_lista, todos_los_juegos):
        if nombre_lista == SIN_LISTA:
            asignados = set()
            for archivos in Lista._datos.values():
                asignados.update(archivos)
            return [j for j in todos_los_juegos if j.nombre_archivo not in asignados]
        elif nombre_lista in Lista._datos:
            archivos_en_lista = set(Lista._datos[nombre_lista])
            return [j for j in todos_los_juegos if j.nombre_archivo in archivos_en_lista]
        return []

    # Devuelve [SIN_LISTA] + listas ordenadas.
    @staticmethod
    def obtener_todas_con_sin_lista():
        return [SIN_LISTA] + sorted(Lista._datos.keys())

    # Migra un archivo renombrado en las listas.
    @staticmethod
    def migrar_renombrado(viejo, nuevo):
        for archivos in Lista._datos.values():
            if viejo in archivos:
                idx = archivos.index(viejo)
                archivos[idx] = nuevo
                Lista.guardar()
                return
