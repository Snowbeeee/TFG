# ── Imports ──────────────────────────────────────────────────────
from PyQt6.QtCore import pyqtSignal, QObject
from ui.sidebar.sidebarUI import SidebarUI
from ui.popups.popupAnadir.popupAnadir import PopupAnadir
from lista import Lista


# Controlador de la barra lateral: gestiona listas/carpetas y emite señales.
# Hereda de QObject (no de QWidget) porque la parte visual la gestiona SidebarUI;
# este controlador solo contiene la lógica de negocio.
class Sidebar(QObject):

    # Señales que MainWindow conectará
    juego_clicked = pyqtSignal(str)        # nombre_archivo → abrir detalle
    lista_clicked = pyqtSignal(str)        # nombre_lista → filtrar grid
    todos_clicked = pyqtSignal()           # mostrar todos los juegos
    lista_borrada = pyqtSignal(str)        # nombre_lista → borrar carpeta

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = SidebarUI()
        self._parent_widget = parent  # para el QInputDialog

        # Conectar botones fijos
        self.ui.btnTodos.clicked.connect(self.todos_clicked.emit)
        self.ui.btnNuevaLista.clicked.connect(self._crear_nueva_lista)

    # Devuelve el QFrame visual para insertarlo en un layout
    @property
    def widget(self):
        return self.ui

    # Reconstruye las secciones colapsables y conecta sus señales internas
    def poblar(self, juegos):
        secciones = self.ui.poblar(juegos)
        for seccion in secciones:
            seccion.juego_clicked.connect(self.juego_clicked.emit)
            seccion.lista_clicked.connect(self.lista_clicked.emit)
            seccion.lista_borrada.connect(self.lista_borrada.emit)

    # Muestra el popup para añadir una nueva carpeta.
    # Si el usuario confirma, crea la lista y emite todos_clicked para refrescar.
    def _crear_nueva_lista(self):
        parent_w = self._parent_widget if self._parent_widget else self.ui
        popup = PopupAnadir(parent_w)
        if popup.exec() and popup.nombre:
            Lista.crear_lista(popup.nombre)
            self.todos_clicked.emit()
