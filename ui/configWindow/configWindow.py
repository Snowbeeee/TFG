import os
import json
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import pyqtSignal
from ui.configWindow.configWindowUI import ConfigWindowUI


class ConfigWindow(QWidget):
    """Página de configuración: gestiona ajustes persistentes."""

    volumen_cambiado = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)

        # --- Declaración de todas las variables de instancia ---
        self.ui = None
        self._config_path = None
        self._volume = 100

        # --- Configuración de la UI ---
        self.ui = ConfigWindowUI()
        self.ui.setupUi(self)

        # Conectar slider
        self.ui.volumeSlider.valueChanged.connect(self._on_volume_changed)

    def set_config_path(self, path):
        """Establece la ruta del archivo config.json y carga la configuración."""
        self._config_path = path
        self._cargar_config()
        self.ui.volumeSlider.setValue(self._volume)
        self.ui.volumeValueLabel.setText(f"{self._volume}%")

    @property
    def volume(self):
        return self._volume

    def _on_volume_changed(self, value):
        """Actualiza el volumen y emite la señal."""
        self._volume = value
        self.ui.volumeValueLabel.setText(f"{value}%")
        self.volumen_cambiado.emit(value)
        self._guardar_config()

    def _cargar_config(self):
        """Carga la configuración desde config.json."""
        if self._config_path and os.path.exists(self._config_path):
            try:
                with open(self._config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                self._volume = cfg.get("volume", 100)
            except Exception:
                pass

    def _guardar_config(self):
        """Guarda la configuración en config.json."""
        if self._config_path:
            try:
                cfg = {"volume": self._volume}
                with open(self._config_path, "w", encoding="utf-8") as f:
                    json.dump(cfg, f, indent=2)
            except Exception:
                pass
