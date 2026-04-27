# ── Imports ──────────────────────────────────────────────────────
import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QStackedWidget, QScrollArea,
    QFrame, QSizePolicy, QMenu
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QPixmap
from ui.editableLabel.editableLabel import EditableLabel
from ui.header.header import Header
from ui.sidebar.sidebarUI import SidebarUI
from lista import Lista, SIN_LISTA


# QFrame que emite una señal clicked al hacer clic.
# Se usa como contenedor clickeable para las cartas de juego.
class ClickableFrame(QFrame):
    clicked = pyqtSignal()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


# Tarjeta de juego con soporte para menú contextual (click derecho)
class GameCard(ClickableFrame):
    # Señales para las acciones del menú contextual
    asignar_lista = pyqtSignal(str)  # nombre_lista
    eliminar_lista = pyqtSignal()
    mover_lista = pyqtSignal(str)  # nombre_lista
    
    def __init__(self, juego, filtro_lista_actual=None):
        super().__init__()
        self.juego = juego
        self.filtro_lista_actual = filtro_lista_actual
    
    # Muestra menú contextual con opciones según la lista del juego.
    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setObjectName("cardContextMenu")
        
        lista_actual = self.juego.lista
        
        if lista_actual == SIN_LISTA:
            # Juego sin lista: opción de añadir
            submenu_anadir = menu.addMenu("Añadir a lista")
            submenu_anadir.setObjectName("cardContextMenu")
            for nombre_lista in Lista.obtener_nombres():
                submenu_anadir.addAction(nombre_lista, 
                    lambda nl=nombre_lista: self.asignar_lista.emit(nl))
        elif self.filtro_lista_actual is None or self.filtro_lista_actual == SIN_LISTA:
            # Estamos en "Todos los juegos" o en "Sin lista": solo mostrar "Mover a lista"
            submenu_mover = menu.addMenu("Mover a lista")
            submenu_mover.setObjectName("cardContextMenu")
            for nombre_lista in Lista.obtener_nombres():
                if nombre_lista != lista_actual:
                    submenu_mover.addAction(nombre_lista,
                        lambda nl=nombre_lista: self.mover_lista.emit(nl))
        else:
            # Estamos en una lista específica: opciones de eliminar y mover
            menu.addAction("Eliminar de lista", self.eliminar_lista.emit)
            
            submenu_mover = menu.addMenu("Mover a lista")
            submenu_mover.setObjectName("cardContextMenu")
            for nombre_lista in Lista.obtener_nombres():
                if nombre_lista != lista_actual:
                    submenu_mover.addAction(nombre_lista,
                        lambda nl=nombre_lista: self.mover_lista.emit(nl))
        
        menu.exec(event.globalPos())


# Tarjeta de lista/carpeta con soporte para menú contextual (click derecho)
class ListCard(ClickableFrame):
    # Señal para eliminar la lista
    eliminar_lista = pyqtSignal(str)  # nombre_lista
    
    def __init__(self, nombre_lista):
        super().__init__()
        self.nombre_lista = nombre_lista
    
    # Muestra menú contextual con opción de eliminar lista.
    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setObjectName("cardContextMenu")
        menu.addAction("Eliminar lista",
            lambda: self.eliminar_lista.emit(self.nombre_lista))
        menu.exec(event.globalPos())


# Widget custom para el grid container que captura clicks derechos
class GridContainerWidget(QWidget):
    crear_lista = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.filtro_lista_actual = None
    
    # Muestra menú contextual al hacer click derecho en el fondo del grid.
    def contextMenuEvent(self, event):
        # Solo mostrar el menú si estamos en "Todos los juegos"
        if self.filtro_lista_actual is None:
            menu = QMenu(self)
            menu.setObjectName("cardContextMenu")
            menu.addAction("Crear lista", self.crear_lista.emit)
            menu.exec(event.globalPos())


# UI principal: contiene un QStackedWidget para navegar entre páginas.
# QStackedWidget apila múltiples widgets y muestra uno a la vez (como pestañas invisibles).
# Índices: 0=Biblioteca, 1=Configuración, 2=Controles, 3=Juego, 4=Detalle.
class MainWindowUI:

    def __init__(self):
        # --- Declaración de todas las variables de instancia ---
        self.centralwidget = None
        self.centralLayout = None
        self.header = None
        self.stackedWidget = None
        self.menuPage = None
        # Sidebar (widget externo)
        self.sidebar = None
        # Grid de cartas (panel derecho)
        self.scrollArea = None
        self.gridContainer = None
        self.gridLayout = None
        self._cartas = []
        self._filtro_lista = None  # None = mostrar todos
        # Label de ruta de games
        self.games_path_label = None
        self.btn_anadir_juego = None

    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.setWindowTitle("TFG - Emulador")
        MainWindow.resize(1070, 703)

        # Central widget
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        MainWindow.setCentralWidget(self.centralwidget)

        # Layout principal vertical
        self.centralLayout = QVBoxLayout(self.centralwidget)
        self.centralLayout.setContentsMargins(0, 0, 0, 0)
        self.centralLayout.setSpacing(0)

        # --- Barra de navegación (cabecera) ---
        self.header = Header()
        self.centralLayout.addWidget(self.header)

        # StackedWidget para alternar entre páginas
        self.stackedWidget = QStackedWidget()
        self.stackedWidget.setObjectName("stackedWidget")
        self.centralLayout.addWidget(self.stackedWidget)

        # --- Página 0: Biblioteca (sidebar + grid) ---
        self.menuPage = QWidget()
        self.menuPage.setObjectName("menuPage")
        menuLayout = QHBoxLayout(self.menuPage)
        menuLayout.setContentsMargins(0, 0, 0, 0)
        menuLayout.setSpacing(0)

        # == Barra lateral izquierda ==
        self.sidebar = SidebarUI()
        menuLayout.addWidget(self.sidebar)

        # == Panel derecho: grid de cartas ==
        rightPanel = QWidget()
        rightPanel.setObjectName("rightPanel")
        rightLayout = QVBoxLayout(rightPanel)
        rightLayout.setContentsMargins(30, 20, 30, 30)
        rightLayout.setSpacing(20)

        # Layout superior con botón volver y ruta de games
        topLayout = QHBoxLayout()
        topLayout.setContentsMargins(0, 0, 0, 0)
        topLayout.setSpacing(20)

        # Botón de volver (solo visible cuando hay un filtro activo)
        self.btn_volver = QPushButton("← Volver")
        self.btn_volver.setObjectName("backButton")
        self.btn_volver.setMaximumWidth(100)
        self.btn_volver.hide()
        _sp = self.btn_volver.sizePolicy()
        _sp.setRetainSizeWhenHidden(True)
        self.btn_volver.setSizePolicy(_sp)
        topLayout.addWidget(self.btn_volver, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        # Stretch para separar el botón del label
        topLayout.addStretch()

        # Botón para añadir un juego desde el explorador de archivos
        self.btn_anadir_juego = QPushButton("+ Añadir juego")
        self.btn_anadir_juego.setObjectName("addGameButton")
        topLayout.addWidget(self.btn_anadir_juego, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        # Label con la ruta de la carpeta de games
        self.games_path_label = QLabel("")
        self.games_path_label.setObjectName("gamesPathLabel")
        self.games_path_label.setStyleSheet("color: #FB923C; font-size: 12px;")
        topLayout.addWidget(self.games_path_label, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        rightLayout.addLayout(topLayout)

        self.scrollArea = QScrollArea()
        self.scrollArea.setObjectName("scrollArea")
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setFrameShape(QFrame.Shape.NoFrame)
        rightLayout.addWidget(self.scrollArea)

        self.gridContainer = GridContainerWidget()
        self.gridContainer.setObjectName("gridContainer")
        self.gridLayout = QGridLayout(self.gridContainer)
        self.gridLayout.setSpacing(20)
        self.gridLayout.setContentsMargins(10, 10, 10, 10)
        self.gridLayout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.scrollArea.setWidget(self.gridContainer)

        menuLayout.addWidget(rightPanel)

        self.stackedWidget.addWidget(self.menuPage)  # index 0

        self.retranslateUi(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle("TFG - Emulador")

    # ------------------------------------------------------------------
    #  Cartas (panel derecho)
    # ------------------------------------------------------------------

    # Crea un widget 'carta' con imagen y nombre editable para un juego
    def crear_carta(self, juego, filtro_lista_actual=None):
        carta = GameCard(juego, filtro_lista_actual)
        carta.setObjectName("gameCard")
        carta.setFixedSize(220, 300)
        carta.setCursor(Qt.CursorShape.PointingHandCursor)
        carta.setProperty("nombre_archivo", juego.nombre_archivo)

        layout = QVBoxLayout(carta)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Imagen (placeholder si no hay carátula)
        imagen_label = QLabel()
        imagen_label.setObjectName("gameCardImage")
        imagen_label.setFixedSize(200, 200)
        imagen_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if juego.imagen and os.path.exists(juego.imagen):
            pixmap = QPixmap(juego.imagen).scaled(
                200, 200,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            imagen_label.setPixmap(pixmap)
        else:
            imagen_label.setText(juego.consola)

        layout.addWidget(imagen_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # Nombre del juego (editable con doble clic)
        nombre_label = EditableLabel(juego.titulo)
        layout.addWidget(nombre_label)

        layout.addStretch()

        return carta, nombre_label

    # Ancho fijo de cada carta + spacing del grid
    CARD_WIDTH = 220
    CARD_SPACING = 20

    # Crea una carta visual para una carpeta/lista del grid
    def crear_carta_carpeta(self, nombre_lista, count):
        carta = ListCard(nombre_lista)
        carta.setObjectName("folderCard")
        carta.setFixedSize(self.CARD_WIDTH, 300)
        carta.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(carta)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        # Icono de carpeta
        icono_label = QLabel("📁")
        icono_label.setObjectName("folderCardIcon")
        icono_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icono_label, stretch=1)

        # Nombre de la lista
        nombre_label = QLabel(nombre_lista)
        nombre_label.setObjectName("folderCardName")
        nombre_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nombre_label.setWordWrap(True)
        layout.addWidget(nombre_label)

        # Contador de juegos
        texto_count = f"{count} juego{'s' if count != 1 else ''}"
        count_label = QLabel(texto_count)
        count_label.setObjectName("folderCardCount")
        count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(count_label)

        layout.addStretch()

        return carta

    # Llena el grid con cartas generadas dinámicamente.
    # Si filtro_lista es None (vista 'Todos'), muestra una carta por cada carpeta
    # con juegos y las cartas de los juegos sin carpeta asignada.
    # Si filtro_lista es un nombre de lista, solo muestra los juegos de esa lista.
    # Devuelve 4 dicts para que MainWindow pueda conectar señales a cada carta.
    def poblar_grid(self, juegos, filtro_lista=None):
        self._filtro_lista = filtro_lista

        # Guardar referencias para poder reposicionar al cambiar tamaño
        self._cartas = []

        # Limpiar grid existente
        while self.gridLayout.count():
            item = self.gridLayout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        cartas_juego = {}
        labels = {}
        carpetas = {}
        borrar_carpetas = {}

        if filtro_lista is not None:
            # Filtro activo: mostrar solo los juegos de esa lista
            juegos_visibles = Lista.obtener_juegos_de_lista(filtro_lista, juegos)
            for juego in juegos_visibles:
                carta, lbl = self.crear_carta(juego, filtro_lista)
                self._cartas.append(carta)
                cartas_juego[carta] = juego
                labels[lbl] = juego
        else:
            # Sin filtro: una carta por cada carpeta + juegos sin carpeta
            for nombre_lista in Lista.obtener_nombres():
                juegos_en_lista = Lista.obtener_juegos_de_lista(nombre_lista, juegos)
                carta = self.crear_carta_carpeta(nombre_lista, len(juegos_en_lista))
                self._cartas.append(carta)
                carpetas[carta] = nombre_lista

            # Juegos sin carpeta asignada
            juegos_sin_lista = Lista.obtener_juegos_de_lista(SIN_LISTA, juegos)
            for juego in juegos_sin_lista:
                carta, lbl = self.crear_carta(juego, None)
                self._cartas.append(carta)
                cartas_juego[carta] = juego
                labels[lbl] = juego

        # Posicionar con las columnas que quepan ahora
        self._reflow_grid()

        return cartas_juego, labels, carpetas

    # Calcula cuántas columnas caben según el ancho del scrollArea
    def _calcular_columnas(self):
        ancho = self.scrollArea.viewport().width()
        if ancho <= 0:
            return 1
        columnas = max(1, (ancho + self.CARD_SPACING) // (self.CARD_WIDTH + self.CARD_SPACING))
        return columnas

    # Reposiciona todas las cartas en el grid según las columnas actuales.
    # Se llama en cada resizeEvent para hacer el grid responsivo.
    def _reflow_grid(self):
        if not self._cartas:
            return

        columnas = self._calcular_columnas()

        # Quitar widgets del layout sin destruirlos
        while self.gridLayout.count():
            self.gridLayout.takeAt(0)

        # Reposicionar
        for i, carta in enumerate(self._cartas):
            fila = i // columnas
            col = i % columnas
            self.gridLayout.addWidget(carta, fila, col, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
