from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QSlider, QComboBox, QPushButton, QFrame
)
from PyQt6.QtCore import Qt


class GameSideBarUI(QFrame):
    """UI de la barra lateral del juego: configuración + botón salir."""

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

        self._setup_ui()

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
        tituloDS = QLabel("Gráficos – DS")
        tituloDS.setObjectName("gameSideBarSectionTitle")
        layout.addWidget(tituloDS)

        rendererRow = QHBoxLayout()
        rendererRow.setSpacing(10)
        rendererLabel = QLabel("Renderizador")
        rendererLabel.setObjectName("gameSideBarLabel")
        rendererRow.addWidget(rendererLabel)

        self.dsRendererCombo = QComboBox()
        self.dsRendererCombo.setObjectName("gameSideBarCombo")
        self.dsRendererCombo.addItems(["Software", "OpenGL"])
        rendererRow.addWidget(self.dsRendererCombo, 1)
        layout.addLayout(rendererRow)

        self.dsResolutionRow = QWidget()
        dsResLayout = QHBoxLayout(self.dsResolutionRow)
        dsResLayout.setContentsMargins(0, 0, 0, 0)
        dsResLayout.setSpacing(10)
        dsResLabel = QLabel("Resolución")
        dsResLabel.setObjectName("gameSideBarLabel")
        dsResLayout.addWidget(dsResLabel)

        self.dsResolutionCombo = QComboBox()
        self.dsResolutionCombo.setObjectName("gameSideBarCombo")
        self.dsResolutionCombo.addItems([
            "1x (256×192)", "2x (512×384)", "3x (768×576)", "4x (1024×768)",
            "5x (1280×960)", "6x (1536×1152)", "7x (1792×1344)", "8x (2048×1536)",
        ])
        dsResLayout.addWidget(self.dsResolutionCombo, 1)
        layout.addWidget(self.dsResolutionRow)

        # ── Sección Gráficos – 3DS ──
        titulo3DS = QLabel("Gráficos – 3DS")
        titulo3DS.setObjectName("gameSideBarSectionTitle")
        layout.addWidget(titulo3DS)

        citraResRow = QHBoxLayout()
        citraResRow.setSpacing(10)
        citraResLabel = QLabel("Resolución")
        citraResLabel.setObjectName("gameSideBarLabel")
        citraResRow.addWidget(citraResLabel)

        self.citraResolutionCombo = QComboBox()
        self.citraResolutionCombo.setObjectName("gameSideBarCombo")
        self.citraResolutionCombo.addItems([
            "1x (Nativa)", "2x", "3x", "4x", "5x",
            "6x", "7x", "8x", "9x", "10x",
        ])
        citraResRow.addWidget(self.citraResolutionCombo, 1)
        layout.addLayout(citraResRow)

        # ── Espacio flexible ──
        layout.addStretch()

        # ── Botón Salir (abajo del todo) ──
        self.pushButtonSalir = QPushButton("Salir del Juego")
        self.pushButtonSalir.setObjectName("gameSideBarSalir")
        self.pushButtonSalir.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self.pushButtonSalir)
