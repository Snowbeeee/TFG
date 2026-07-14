# ── Imports ──────────────────────────────────────────────────────
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QSlider, QComboBox, QPushButton, QFrame,
    QScrollArea, QLineEdit, QPlainTextEdit, QCheckBox, QSizePolicy
)
from PyQt6.QtCore import Qt


# UI de la barra lateral in-game: configuración rápida + botón salir.
# Es casi idéntica a ConfigWindowUI pero más compacta (280px de ancho)
# y con un botón de salir al final.
class GameSideBarUI(QFrame):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("gameSideBar")
        self.setFixedWidth(280)

        # --- Declaración de variables de instancia ---
        self.volumeSlider = None
        self.volumeValueLabel = None
        self.dsRendererCombo = None
        self.dsResolutionCombo = None
        self.dsResolutionRow = None
        self.citraResolutionCombo = None
        self.pushButtonSalir = None
        self.dsSectionWidget = None    # contenedor de toda la sección DS
        self.citraSectionWidget = None  # contenedor de toda la sección 3DS
        self.cheatSectionWidget = None  # contenedor de la sección de cheats (DS)
        self.cheatListLayout = None     # layout dinámico de la lista de cheats
        self.cheatNameInput = None      # campo de nombre del nuevo cheat
        self.cheatCodeInput = None      # área de código Action Replay
        self.cheatAddButton = None      # botón añadir cheat
        self.fastForwardSectionWidget = None  # contenedor de la sección de fast-forward (DS)
        self.fastForwardButton = None   # botón toggle de fast-forward
        self.fastForwardSpeedCombo = None  # combo de velocidad (x2/x4/x8/x16)

        self._setup_ui()

    # Construye el layout: secciones de audio, gráficos DS, gráficos 3DS y botón salir.
    # dsSectionWidget y citraSectionWidget se muestran/ocultan según la consola.
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(16)

        # ── Sección Audio ──
        tituloAudio = QLabel("Audio")
        tituloAudio.setObjectName("gameSideBarSectionTitle")
        layout.addWidget(tituloAudio)

        volumeRow = QHBoxLayout()
        volumeRow.setSpacing(10)

        volumeLabel = QLabel("Volumen")
        volumeLabel.setObjectName("gameSideBarLabel")
        volumeRow.addWidget(volumeLabel)

        self.volumeSlider = QSlider(Qt.Orientation.Horizontal)
        self.volumeSlider.setObjectName("gameSideBarSlider")
        self.volumeSlider.setMinimum(0)
        self.volumeSlider.setMaximum(100)
        self.volumeSlider.setValue(100)
        self.volumeSlider.setTickPosition(QSlider.TickPosition.NoTicks)
        volumeRow.addWidget(self.volumeSlider, 1)

        self.volumeValueLabel = QLabel("100%")
        self.volumeValueLabel.setObjectName("gameSideBarValue")
        self.volumeValueLabel.setFixedWidth(40)
        self.volumeValueLabel.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        volumeRow.addWidget(self.volumeValueLabel)

        layout.addLayout(volumeRow)

        # ── Sección Gráficos – DS ──
        self.dsSectionWidget = QWidget()
        dsSectionLayout = QVBoxLayout(self.dsSectionWidget)
        dsSectionLayout.setContentsMargins(0, 0, 0, 0)
        dsSectionLayout.setSpacing(8)

        tituloDS = QLabel("Gráficos \u2013 DS")
        tituloDS.setObjectName("gameSideBarSectionTitle")
        dsSectionLayout.addWidget(tituloDS)

        rendererRow = QHBoxLayout()
        rendererRow.setSpacing(10)
        rendererLabel = QLabel("Renderizador")
        rendererLabel.setObjectName("gameSideBarLabel")
        rendererRow.addWidget(rendererLabel)

        self.dsRendererCombo = QComboBox()
        self.dsRendererCombo.setObjectName("gameSideBarCombo")
        self.dsRendererCombo.addItems(["Software", "OpenGL"])
        rendererRow.addWidget(self.dsRendererCombo, 1)
        dsSectionLayout.addLayout(rendererRow)

        self.dsResolutionRow = QWidget()
        dsResLayout = QHBoxLayout(self.dsResolutionRow)
        dsResLayout.setContentsMargins(0, 0, 0, 0)
        dsResLayout.setSpacing(10)
        dsResLabel = QLabel("Resoluci\u00f3n")
        dsResLabel.setObjectName("gameSideBarLabel")
        dsResLayout.addWidget(dsResLabel)

        self.dsResolutionCombo = QComboBox()
        self.dsResolutionCombo.setObjectName("gameSideBarCombo")
        self.dsResolutionCombo.addItems([
            "1x (256\u00d7192)", "2x (512\u00d7384)", "3x (768\u00d7576)", "4x (1024\u00d7768)",
            "5x (1280\u00d7960)", "6x (1536\u00d71152)", "7x (1792\u00d71344)", "8x (2048\u00d71536)",
        ])
        dsResLayout.addWidget(self.dsResolutionCombo, 1)
        dsSectionLayout.addWidget(self.dsResolutionRow)

        layout.addWidget(self.dsSectionWidget)

        # ── Sección Gráficos – 3DS ──
        self.citraSectionWidget = QWidget()
        citraSectionLayout = QVBoxLayout(self.citraSectionWidget)
        citraSectionLayout.setContentsMargins(0, 0, 0, 0)
        citraSectionLayout.setSpacing(8)

        titulo3DS = QLabel("Gr\u00e1ficos \u2013 3DS")
        titulo3DS.setObjectName("gameSideBarSectionTitle")
        citraSectionLayout.addWidget(titulo3DS)

        citraResRow = QHBoxLayout()
        citraResRow.setSpacing(10)
        citraResLabel = QLabel("Resoluci\u00f3n")
        citraResLabel.setObjectName("gameSideBarLabel")
        citraResRow.addWidget(citraResLabel)

        self.citraResolutionCombo = QComboBox()
        self.citraResolutionCombo.setObjectName("gameSideBarCombo")
        self.citraResolutionCombo.addItems([
            "1x (Nativa)", "2x", "3x", "4x", "5x",
            "6x", "7x", "8x", "9x", "10x",
        ])
        citraResRow.addWidget(self.citraResolutionCombo, 1)
        citraSectionLayout.addLayout(citraResRow)

        layout.addWidget(self.citraSectionWidget)

        # ── Sección Cheats – DS ──
        self.cheatSectionWidget = QWidget()
        # Fixed vertical: la sección NO crece cuando la ventana se maximiza.
        # Sin esto, el QVBoxLayout reparte el espacio sobrante entre la sección
        # y la lista (QScrollArea expandible) dejando un hueco entre el título
        # y los items. Con Fixed la sección se ciñe a su sizeHint.
        self.cheatSectionWidget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        cheatSectionLayout = QVBoxLayout(self.cheatSectionWidget)
        cheatSectionLayout.setContentsMargins(0, 0, 0, 0)
        cheatSectionLayout.setSpacing(8)
        cheatSectionLayout.setAlignment(Qt.AlignmentFlag.AlignTop)

        tituloCheat = QLabel("Cheats – DS")
        tituloCheat.setObjectName("gameSideBarSectionTitle")
        cheatSectionLayout.addWidget(tituloCheat)

        # Lista de cheats existentes (scroll)
        scrollArea = QScrollArea()
        scrollArea.setObjectName("cheatScrollArea")
        scrollArea.setWidgetResizable(True)
        scrollArea.setFixedHeight(110)
        scrollArea.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        cheatListContainer = QWidget()
        cheatListContainer.setObjectName("cheatListContainer")
        self.cheatListLayout = QVBoxLayout(cheatListContainer)
        self.cheatListLayout.setContentsMargins(4, 4, 4, 4)
        self.cheatListLayout.setSpacing(4)
        self.cheatListLayout.addStretch()
        scrollArea.setWidget(cheatListContainer)
        cheatSectionLayout.addWidget(scrollArea)

        # Formulario para añadir cheat
        self.cheatNameInput = QLineEdit()
        self.cheatNameInput.setObjectName("cheatInput")
        self.cheatNameInput.setPlaceholderText("Nombre del cheat")
        cheatSectionLayout.addWidget(self.cheatNameInput)

        self.cheatCodeInput = QPlainTextEdit()
        self.cheatCodeInput.setObjectName("cheatCodeInput")
        self.cheatCodeInput.setPlaceholderText("XXXXXXXX YYYYYYYY\nXXXXXXXX YYYYYYYY")
        self.cheatCodeInput.setFixedHeight(58)
        cheatSectionLayout.addWidget(self.cheatCodeInput)

        self.cheatAddButton = QPushButton("Añadir Cheat")
        self.cheatAddButton.setObjectName("cheatAddButton")
        self.cheatAddButton.setCursor(Qt.CursorShape.PointingHandCursor)
        cheatSectionLayout.addWidget(self.cheatAddButton)

        layout.addWidget(self.cheatSectionWidget)

        # ── Sección Fast-Forward – DS ──
        # Toggle que acelera la emulación de melonDS: muta el audio (libera
        # el throttle bloqueante de PyAudio) y GameWindow ejecuta N frames
        # extra por tick del timer. Solo tiene sentido para .nds; para
        # 3DS/Wii/GC la sección se oculta desde set_consola.
        self.fastForwardSectionWidget = QWidget()
        self.fastForwardSectionWidget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        ffSectionLayout = QVBoxLayout(self.fastForwardSectionWidget)
        ffSectionLayout.setContentsMargins(0, 0, 0, 0)
        ffSectionLayout.setSpacing(8)

        tituloFF = QLabel("Fast-Forward – DS")
        tituloFF.setObjectName("gameSideBarSectionTitle")
        ffSectionLayout.addWidget(tituloFF)

        self.fastForwardButton = QPushButton("Acelerar ▶▶")
        self.fastForwardButton.setObjectName("fastForwardButton")
        self.fastForwardButton.setCheckable(True)
        self.fastForwardButton.setCursor(Qt.CursorShape.PointingHandCursor)
        ffSectionLayout.addWidget(self.fastForwardButton)

        ffSpeedRow = QHBoxLayout()
        ffSpeedRow.setSpacing(10)
        ffSpeedLabel = QLabel("Velocidad")
        ffSpeedLabel.setObjectName("gameSideBarLabel")
        ffSpeedRow.addWidget(ffSpeedLabel)

        self.fastForwardSpeedCombo = QComboBox()
        self.fastForwardSpeedCombo.setObjectName("gameSideBarCombo")
        # (texto visible, frames extra por tick). El multiplicador real es
        # extra_frames + 1 (el frame que ya dispara paintGL normalmente).
        for texto, extra in (("x2", 1), ("x4", 3), ("x8", 7), ("x16", 15)):
            self.fastForwardSpeedCombo.addItem(texto, extra)
        # Default: x4 (3 frames extra)
        self.fastForwardSpeedCombo.setCurrentIndex(1)
        ffSpeedRow.addWidget(self.fastForwardSpeedCombo, 1)
        ffSectionLayout.addLayout(ffSpeedRow)

        layout.addWidget(self.fastForwardSectionWidget)

        # ── Espacio flexible ──
        layout.addStretch()

        # ── Botón Salir (abajo del todo) ──
        self.pushButtonSalir = QPushButton("Salir del Juego")
        self.pushButtonSalir.setObjectName("gameSideBarSalir")
        self.pushButtonSalir.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self.pushButtonSalir)
