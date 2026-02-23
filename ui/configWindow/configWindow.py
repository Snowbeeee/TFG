import os
import json
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import pyqtSignal
from ui.configWindow.configWindowUI import ConfigWindowUI

# Mapeo entre índice del combo y valor que espera citra_resolution_factor
_RESOLUTION_VALUES = [
    "1x (Native)", "2x", "3x", "4x", "5x",
    "6x", "7x", "8x", "9x", "10x",
]


class ConfigWindow(QWidget):
    """Página de configuración: gestiona ajustes persistentes."""

    volumen_cambiado = pyqtSignal(int)
    resolucion_cambiada = pyqtSignal(int)  # índice 0‑9

    def __init__(self, parent=None):
        super().__init__(parent)

        # --- Declaración de todas las variables de instancia ---
        self.ui = None
        self._config_path = None
        self._volume = 100
        self._resolution_index = 0  # 0 = 1x (nativa)

        # --- Configuración de la UI ---
        self.ui = ConfigWindowUI()
        self.ui.setupUi(self)

        # Conectar slider
        self.ui.volumeSlider.valueChanged.connect(self._on_volume_changed)
        # Conectar combo resolución
        self.ui.resolutionCombo.currentIndexChanged.connect(self._on_resolution_changed)

    def set_config_path(self, path):
        """Establece la ruta del archivo config.json y carga la configuración."""
        self._config_path = path
        self._cargar_config()
        self.ui.volumeSlider.setValue(self._volume)
        self.ui.volumeValueLabel.setText(f"{self._volume}%")
        self.ui.resolutionCombo.setCurrentIndex(self._resolution_index)

    # ── Propiedades ──

    @property
    def volume(self):
        return self._volume

    @property
    def resolution_index(self):
        return self._resolution_index

    @property
    def resolution_value(self):
        """Devuelve el string que espera citra_resolution_factor."""
        return _RESOLUTION_VALUES[self._resolution_index]

    # ── Slots ──

    def _on_volume_changed(self, value):
        """Actualiza el volumen y emite la señal."""
        self._volume = value
        self.ui.volumeValueLabel.setText(f"{value}%")
        self.volumen_cambiado.emit(value)
        self._guardar_config()

    def _on_resolution_changed(self, index):
        """Actualiza la resolución interna y emite la señal."""
        if index < 0:
            return
        self._resolution_index = index
        self.resolucion_cambiada.emit(index)
        self._guardar_config()

    # ── Persistencia ──

    def _cargar_config(self):
        """Carga la configuración desde config.json."""
        if self._config_path and os.path.exists(self._config_path):
            try:
                with open(self._config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                self._volume = cfg.get("volume", 100)
                self._resolution_index = cfg.get("resolution_index", 0)
                # Clampar al rango válido
                if self._resolution_index < 0 or self._resolution_index >= len(_RESOLUTION_VALUES):
                    self._resolution_index = 0
            except Exception:
                pass

    def _guardar_config(self):
        """Guarda la configuración en config.json."""
        if self._config_path:
            try:
                cfg = {
                    "volume": self._volume,
                    "resolution_index": self._resolution_index,
                }
                with open(self._config_path, "w", encoding="utf-8") as f:
                    json.dump(cfg, f, indent=2)
            except Exception:
                pass
