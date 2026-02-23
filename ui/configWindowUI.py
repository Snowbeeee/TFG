from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QSlider
)
from PyQt6.QtCore import Qt


class ConfigWindowUI:
    """UI de la página de configuración."""

    def __init__(self):
        # --- Declaración de todas las variables de instancia ---
        self.volumeSlider = None
        self.volumeValueLabel = None

    def setupUi(self, parent):
        parent.setObjectName("configPage")
        configLayout = QVBoxLayout(parent)
        configLayout.setContentsMargins(40, 30, 40, 30)
        configLayout.setSpacing(20)

        # Título de sección
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
        configLayout.addStretch()
