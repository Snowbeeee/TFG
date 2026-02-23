import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QGridLayout,
    QLabel, QPushButton, QStackedWidget, QScrollArea,
    QFrame
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap
from ui.editableLabel import EditableLabel


class MainWindowUI:
    """UI principal: contiene un QStackedWidget para navegar entre páginas."""

    def __init__(self):
        # --- Declaración de todas las variables de instancia ---
        self.centralwidget = None
        self.centralLayout = None
        self.stackedWidget = None
        self.menuPage = None
        self.titleLabel = None
        self.scrollArea = None
        self.gridContainer = None
        self.gridLayout = None
        self._cartas = []

    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.setWindowTitle("TFG - Emulador")
        MainWindow.resize(1070, 703)

        # Central widget
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        MainWindow.setCentralWidget(self.centralwidget)

        # Layout principal
        self.centralLayout = QVBoxLayout(self.centralwidget)
        self.centralLayout.setContentsMargins(0, 0, 0, 0)

        # StackedWidget para alternar entre menú y juego
        self.stackedWidget = QStackedWidget()
        self.stackedWidget.setObjectName("stackedWidget")
        self.centralLayout.addWidget(self.stackedWidget)

        # --- Página 0: Menú principal ---
        self.menuPage = QWidget()
        self.menuPage.setObjectName("menuPage")
        menuLayout = QVBoxLayout(self.menuPage)
        menuLayout.setContentsMargins(30, 30, 30, 30)
        menuLayout.setSpacing(20)

        # Título
        self.titleLabel = QLabel("Biblioteca de Juegos")
        self.titleLabel.setObjectName("titleLabel")
        self.titleLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        menuLayout.addWidget(self.titleLabel)

        # Scroll area para las cartas
        self.scrollArea = QScrollArea()
        self.scrollArea.setObjectName("scrollArea")
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setFrameShape(QFrame.Shape.NoFrame)
        menuLayout.addWidget(self.scrollArea)

        # Contenedor con el grid
        self.gridContainer = QWidget()
        self.gridContainer.setObjectName("gridContainer")
        self.gridLayout = QGridLayout(self.gridContainer)
        self.gridLayout.setSpacing(20)
        self.gridLayout.setContentsMargins(10, 10, 10, 10)

        self.scrollArea.setWidget(self.gridContainer)

        self.stackedWidget.addWidget(self.menuPage)  # index 0

        self.retranslateUi(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle("TFG - Emulador")

    def crear_carta(self, juego):
        """Crea un widget 'carta' para un juego y lo devuelve junto a su botón Jugar."""
        carta = QFrame()
        carta.setObjectName("gameCard")
        carta.setFixedSize(220, 300)

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

        # Botón jugar
        btn_jugar = QPushButton("Jugar")
        btn_jugar.setObjectName("gameCardButton")
        layout.addWidget(btn_jugar)

        return carta, btn_jugar, nombre_label

    # Ancho fijo de cada carta + spacing del grid
    CARD_WIDTH = 220
    CARD_SPACING = 20

    def poblar_grid(self, juegos):
        """Llena el grid con cartas generadas dinámicamente.
        Devuelve (botones_dict, labels_dict) donde:
          botones_dict = {QPushButton: Juego}
          labels_dict  = {EditableLabel: Juego}
        """
        # Guardar referencias para poder reposicionar al cambiar tamaño
        self._cartas = []

        # Limpiar grid existente
        while self.gridLayout.count():
            item = self.gridLayout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        botones = {}
        labels = {}
        for juego in juegos:
            carta, btn, lbl = self.crear_carta(juego)
            self._cartas.append(carta)
            botones[btn] = juego
            labels[lbl] = juego

        # Posicionar con las columnas que quepan ahora
        self._reflow_grid()

        return botones, labels

    def _calcular_columnas(self):
        """Calcula cuántas columnas caben según el ancho del scrollArea."""
        ancho = self.scrollArea.viewport().width()
        if ancho <= 0:
            return 1
        # Cada carta necesita CARD_WIDTH + CARD_SPACING, pero la última no
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
            self.gridLayout.addWidget(carta, fila, col, Qt.AlignmentFlag.AlignCenter)
