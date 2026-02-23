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
        self.resolutionCombo = None

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

        # ── Sección Gráficos ──
        tituloGraficos = QLabel("Gráficos")
        tituloGraficos.setObjectName("configSectionTitle")
        configLayout.addWidget(tituloGraficos)

        # Fila: etiqueta + combo resolución
        resRow = QHBoxLayout()
        resRow.setSpacing(15)

        resLabel = QLabel("Resolución interna")
        resLabel.setObjectName("configLabel")
        resRow.addWidget(resLabel)

        self.resolutionCombo = QComboBox()
        self.resolutionCombo.setObjectName("configCombo")
        self.resolutionCombo.addItems([
            "1x (Nativa)",
            "2x",
            "3x",
            "4x",
            "5x",
            "6x",
            "7x",
            "8x",
            "9x",
            "10x",
        ])
        resRow.addWidget(self.resolutionCombo, 1)

        configLayout.addLayout(resRow)

        # Nota informativa
        resNote = QLabel("Solo aplica a juegos de 3DS (Citra). Los juegos de DS usan renderizado por software.")
        resNote.setObjectName("configNote")
        resNote.setWordWrap(True)
        configLayout.addWidget(resNote)

        configLayout.addStretch()
