from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QSlider, QComboBox
)
from PyQt6.QtCore import Qt


class ConfigWindowUI:
    """UI de la página de configuración."""

    def __init__(self):
        # --- Declaración de todas las variables de instancia ---
        self.volumeSlider = None
        self.volumeValueLabel = None
        self.dsRendererCombo = None
        self.dsResolutionCombo = None
        self.dsResolutionRow = None
        self.citraResolutionCombo = None

    def setupUi(self, parent):
        parent.setObjectName("configPage")
        configLayout = QVBoxLayout(parent)
        configLayout.setContentsMargins(40, 30, 40, 30)
        configLayout.setSpacing(20)

        # ── Sección Audio ──
        tituloAudio = QLabel("Audio")
        tituloAudio.setObjectName("configSectionTitle")
        configLayout.addWidget(tituloAudio)

        # Fila: etiqueta + slider + valor
        volumeRow = QHBoxLayout()
        volumeRow.setSpacing(15)

        volumeLabel = QLabel("Volumen")
        volumeLabel.setObjectName("configLabel")
        volumeRow.addWidget(volumeLabel)

        self.volumeSlider = QSlider(Qt.Orientation.Horizontal)
        self.volumeSlider.setObjectName("volumeSlider")
        self.volumeSlider.setMinimum(0)
        self.volumeSlider.setMaximum(100)
        self.volumeSlider.setValue(100)
        self.volumeSlider.setTickPosition(QSlider.TickPosition.NoTicks)
        volumeRow.addWidget(self.volumeSlider, 1)

        self.volumeValueLabel = QLabel("100%")
        self.volumeValueLabel.setObjectName("configValueLabel")
        self.volumeValueLabel.setFixedWidth(50)
        self.volumeValueLabel.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        volumeRow.addWidget(self.volumeValueLabel)

        configLayout.addLayout(volumeRow)

        # ── Sección Gráficos – DS (melonDS DS) ──
        tituloDS = QLabel("Gráficos – DS")
        tituloDS.setObjectName("configSectionTitle")
        configLayout.addWidget(tituloDS)

        # Renderizador DS
        rendererRow = QHBoxLayout()
        rendererRow.setSpacing(15)
        rendererLabel = QLabel("Renderizador")
        rendererLabel.setObjectName("configLabel")
        rendererRow.addWidget(rendererLabel)

        self.dsRendererCombo = QComboBox()
        self.dsRendererCombo.setObjectName("configCombo")
        self.dsRendererCombo.addItems(["Software", "OpenGL"])
        rendererRow.addWidget(self.dsRendererCombo, 1)
        configLayout.addLayout(rendererRow)

        # Resolución interna DS (solo visible con OpenGL)
        self.dsResolutionRow = QWidget()
        dsResLayout = QHBoxLayout(self.dsResolutionRow)
        dsResLayout.setContentsMargins(0, 0, 0, 0)
        dsResLayout.setSpacing(15)
        dsResLabel = QLabel("Resolución interna")
        dsResLabel.setObjectName("configLabel")
        dsResLayout.addWidget(dsResLabel)

        self.dsResolutionCombo = QComboBox()
        self.dsResolutionCombo.setObjectName("configCombo")
        self.dsResolutionCombo.addItems([
            "1x (256×192)", "2x (512×384)", "3x (768×576)", "4x (1024×768)",
            "5x (1280×960)", "6x (1536×1152)", "7x (1792×1344)", "8x (2048×1536)",
        ])
        dsResLayout.addWidget(self.dsResolutionCombo, 1)
        configLayout.addWidget(self.dsResolutionRow)

        dsNote = QLabel("OpenGL permite aumentar la resolución interna de los juegos de DS.")
        dsNote.setObjectName("configNote")
        dsNote.setWordWrap(True)
        configLayout.addWidget(dsNote)

        # ── Sección Gráficos – 3DS (Citra) ──
        titulo3DS = QLabel("Gráficos – 3DS")
        titulo3DS.setObjectName("configSectionTitle")
        configLayout.addWidget(titulo3DS)

        citraResRow = QHBoxLayout()
        citraResRow.setSpacing(15)
        citraResLabel = QLabel("Resolución interna")
        citraResLabel.setObjectName("configLabel")
        citraResRow.addWidget(citraResLabel)

        self.citraResolutionCombo = QComboBox()
        self.citraResolutionCombo.setObjectName("configCombo")
        self.citraResolutionCombo.addItems([
            "1x (Nativa)", "2x", "3x", "4x", "5x",
            "6x", "7x", "8x", "9x", "10x",
        ])
        citraResRow.addWidget(self.citraResolutionCombo, 1)
        configLayout.addLayout(citraResRow)

        configLayout.addStretch()
