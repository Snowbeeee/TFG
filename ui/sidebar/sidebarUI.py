from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QScrollArea, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from lista import Lista, SIN_LISTA


class _ListaSeccion(QWidget):
    """Sección colapsable en la barra lateral: cabecera + lista de nombres de juego."""
    juego_clicked = pyqtSignal(str)   # nombre_archivo del juego
    lista_clicked = pyqtSignal(str)   # nombre_lista (para filtrar)

    def __init__(self, nombre_lista, parent=None):
        super().__init__(parent)
        self.nombre_lista = nombre_lista
        self._colapsado = False
        self._items = []  # QPushButton por cada juego

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Fila de cabecera: flecha + nombre
        header_row = QWidget()
        header_row.setObjectName("sidebarSectionHeaderRow")
        row_layout = QHBoxLayout(header_row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(0)

        # Botón flecha (solo colapsa/expande)
        self.arrow_btn = QPushButton("▼")
        self.arrow_btn.setObjectName("sidebarArrowBtn")
        self.arrow_btn.setFixedWidth(36)
        self.arrow_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.arrow_btn.clicked.connect(self._toggle)
        row_layout.addWidget(self.arrow_btn)

        # Botón nombre (filtra las cartas por esta lista)
        self.name_btn = QPushButton(nombre_lista)
        self.name_btn.setObjectName("sidebarSectionName")
        self.name_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.name_btn.clicked.connect(lambda: self.lista_clicked.emit(self.nombre_lista))
        row_layout.addWidget(self.name_btn)

        layout.addWidget(header_row)

        # Contenedor de items
        self.items_container = QWidget()
        self.items_container.setObjectName("sidebarSectionItems")
        self.items_layout = QVBoxLayout(self.items_container)
        self.items_layout.setContentsMargins(0, 0, 0, 0)
        self.items_layout.setSpacing(0)
        layout.addWidget(self.items_container)

    def _toggle(self):
        self._colapsado = not self._colapsado
        self.items_container.setVisible(not self._colapsado)
        self.arrow_btn.setText("▶" if self._colapsado else "▼")

    def set_juegos(self, juegos):
        """Llena la sección con los nombres de los juegos dados."""
        for btn in self._items:
            btn.deleteLater()
        self._items.clear()

        for juego in juegos:
            btn = QPushButton(juego.titulo)
            btn.setObjectName("sidebarGameItem")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setProperty("nombre_archivo", juego.nombre_archivo)
            btn.clicked.connect(lambda checked, na=juego.nombre_archivo: self.juego_clicked.emit(na))
            self.items_layout.addWidget(btn)
            self._items.append(btn)


class SidebarUI(QFrame):
    """Widget visual de la barra lateral (sin lógica de negocio)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebarPanel")
        self.setFixedWidth(280)

        # --- Variables de instancia ---
        self.btnTodos = None
        self.btnNuevaLista = None
        self.sidebarScroll = None
        self.sidebarContainer = None
        self.sidebarLayout = None
        self._secciones = []

        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Fila superior: "Todos los juegos" + botón "+"
        topRow = QWidget()
        topRow.setObjectName("sidebarTopRow")
        topRowLayout = QHBoxLayout(topRow)
        topRowLayout.setContentsMargins(0, 0, 0, 0)
        topRowLayout.setSpacing(0)

        self.btnTodos = QPushButton("Todos los juegos")
        self.btnTodos.setObjectName("sidebarTodosBtn")
        self.btnTodos.setCursor(Qt.CursorShape.PointingHandCursor)
        topRowLayout.addWidget(self.btnTodos)

        self.btnNuevaLista = QPushButton("+")
        self.btnNuevaLista.setObjectName("sidebarAddBtn")
        self.btnNuevaLista.setFixedWidth(40)
        self.btnNuevaLista.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btnNuevaLista.setToolTip("Crear nueva lista")
        topRowLayout.addWidget(self.btnNuevaLista)

        main_layout.addWidget(topRow)

        # Scroll con las secciones de listas
        self.sidebarScroll = QScrollArea()
        self.sidebarScroll.setObjectName("sidebarScroll")
        self.sidebarScroll.setWidgetResizable(True)
        self.sidebarScroll.setFrameShape(QFrame.Shape.NoFrame)
        self.sidebarScroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        main_layout.addWidget(self.sidebarScroll)

        self.sidebarContainer = QWidget()
        self.sidebarContainer.setObjectName("sidebarContainer")
        self.sidebarLayout = QVBoxLayout(self.sidebarContainer)
        self.sidebarLayout.setContentsMargins(0, 0, 0, 0)
        self.sidebarLayout.setSpacing(0)
        self.sidebarLayout.addStretch()
        self.sidebarScroll.setWidget(self.sidebarContainer)

    def poblar(self, juegos):
        """Construye las secciones colapsables. Devuelve la lista de _ListaSeccion."""
        for sec in self._secciones:
            sec.setParent(None)
            sec.deleteLater()
        self._secciones.clear()

        nombres_listas = Lista.obtener_todas_con_sin_lista()

        for nombre_lista in nombres_listas:
            juegos_en_lista = Lista.obtener_juegos_de_lista(nombre_lista, juegos)
            seccion = _ListaSeccion(nombre_lista)
            seccion.set_juegos(juegos_en_lista)
            self.sidebarLayout.insertWidget(self.sidebarLayout.count() - 1, seccion)
            self._secciones.append(seccion)

        return self._secciones
