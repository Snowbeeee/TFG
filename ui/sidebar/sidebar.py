from PyQt6.QtWidgets import QInputDialog
from PyQt6.QtCore import pyqtSignal, QObject
from ui.sidebar.sidebarUI import SidebarUI
from lista import Lista


class Sidebar(QObject):
    """Controlador de la barra lateral: gestiona listas y emite señales."""

    # Señales que MainWindow conectará
    juego_clicked = pyqtSignal(str)        # nombre_archivo → lanzar juego
    lista_clicked = pyqtSignal(str)        # nombre_lista → filtrar grid
    todos_clicked = pyqtSignal()           # mostrar todos los juegos

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = SidebarUI()
        self._parent_widget = parent  # para el QInputDialog

        # Conectar botones fijos
        self.ui.btnTodos.clicked.connect(self.todos_clicked.emit)
        self.ui.btnNuevaLista.clicked.connect(self._crear_nueva_lista)

    @property
    def widget(self):
        """Devuelve el QFrame para insertarlo en un layout."""
        return self.ui

    def poblar(self, juegos):
        """Reconstruye las secciones y conecta señales internas."""
        secciones = self.ui.poblar(juegos)
        for seccion in secciones:
            seccion.juego_clicked.connect(self.juego_clicked.emit)
            seccion.lista_clicked.connect(self.lista_clicked.emit)

    def _crear_nueva_lista(self):
        """Pide un nombre al usuario y crea una nueva lista."""
        parent_w = self._parent_widget if self._parent_widget else self.ui
        nombre, ok = QInputDialog.getText(parent_w, "Nueva lista", "Nombre de la lista:")
        if ok and nombre.strip():
            Lista.crear_lista(nombre.strip())
            # Re-poblar se delega a MainWindow a través de la señal;
            # pero como no tenemos los juegos aquí, emitimos todos_clicked
            # para que MainWindow refresque.  Mejor: poblar se llamará
            # externamente por MainWindow cuando necesite.
            # Por ahora simplemente indicamos que la lista cambió.
            self.todos_clicked.emit()
