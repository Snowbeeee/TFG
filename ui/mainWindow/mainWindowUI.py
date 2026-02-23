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


class MainWindowUI:
    """UI principal: contiene un QStackedWidget para navegar entre páginas."""

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

        self.scrollArea = QScrollArea()
        self.scrollArea.setObjectName("scrollArea")
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setFrameShape(QFrame.Shape.NoFrame)
        rightLayout.addWidget(self.scrollArea)

        self.gridContainer = QWidget()
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

    def crear_carta(self, juego):
        """Crea un widget 'carta' para un juego y lo devuelve junto a su botón Jugar."""
        carta = QFrame()
        carta.setObjectName("gameCard")
        carta.setFixedSize(220, 300)
        carta.setProperty("nombre_archivo", juego.nombre_archivo)

        layout = QVBoxLayout(carta)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Imagen (placeholder si no hay carátula)
        imagen_label = QLabel()
        imagen_label.setObjectName("gameCardImage")
        imagen_label.setFixedSize(200, 160)
        imagen_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if juego.imagen and os.path.exists(juego.imagen):
            pixmap = QPixmap(juego.imagen).scaled(
                200, 160,
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

        # Consola
        consola_label = QLabel(juego.consola)
        consola_label.setObjectName("gameCardConsole")
        consola_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(consola_label)

        layout.addStretch()

        # Fila inferior: botón jugar + menú "⋯"
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(6)

        btn_jugar = QPushButton("Jugar")
        btn_jugar.setObjectName("gameCardButton")
        bottom_row.addWidget(btn_jugar)

        btn_menu = QPushButton("⋯")
        btn_menu.setObjectName("gameCardMenuBtn")
        btn_menu.setFixedWidth(36)
        btn_menu.setCursor(Qt.CursorShape.PointingHandCursor)
        bottom_row.addWidget(btn_menu)

        layout.addLayout(bottom_row)

        return carta, btn_jugar, nombre_label, btn_menu

    # Ancho fijo de cada carta + spacing del grid
    CARD_WIDTH = 220
    CARD_SPACING = 20

    def poblar_grid(self, juegos, filtro_lista=None):
        """Llena el grid con cartas generadas dinámicamente.
        Si filtro_lista es un nombre de lista, solo muestra esos juegos.
        Devuelve (botones_dict, labels_dict) donde:
          botones_dict = {QPushButton: Juego}
          labels_dict  = {EditableLabel: Juego}
        """
        self._filtro_lista = filtro_lista

        # Filtrar juegos si hay filtro activo
        if filtro_lista is not None:
            juegos_visibles = Lista.obtener_juegos_de_lista(filtro_lista, juegos)
        else:
            juegos_visibles = juegos

        # Guardar referencias para poder reposicionar al cambiar tamaño
        self._cartas = []

        # Limpiar grid existente
        while self.gridLayout.count():
            item = self.gridLayout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        botones = {}
        labels = {}
        menus = {}
        for juego in juegos_visibles:
            carta, btn, lbl, btn_menu = self.crear_carta(juego)
            self._cartas.append(carta)
            botones[btn] = juego
            labels[lbl] = juego
            menus[btn_menu] = juego

        # Posicionar con las columnas que quepan ahora
        self._reflow_grid()

        return botones, labels, menus

    def _calcular_columnas(self):
        """Calcula cuántas columnas caben según el ancho del scrollArea."""
        ancho = self.scrollArea.viewport().width()
        if ancho <= 0:
            return 1
        columnas = max(1, (ancho + self.CARD_SPACING) // (self.CARD_WIDTH + self.CARD_SPACING))
        return columnas

    def _reflow_grid(self):
        """Reposiciona todas las cartas en el grid según las columnas actuales."""
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
