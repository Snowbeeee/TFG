import os
import json
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import pyqtSignal
from ui.configWindow.configWindowUI import ConfigWindowUI

# Valores que espera citra_resolution_factor
_CITRA_RES_VALUES = [
    "1x (Native)", "2x", "3x", "4x", "5x",
    "6x", "7x", "8x", "9x", "10x",
]

# Valores que espera melonds_render_mode
_DS_RENDERER_VALUES = ["software", "opengl"]

# Valores que espera melonds_opengl_resolution (string numérico)
_DS_RES_VALUES = ["1", "2", "3", "4", "5", "6", "7", "8"]


class ConfigWindow(QWidget):
    """Página de configuración: gestiona ajustes persistentes."""

    volumen_cambiado = pyqtSignal(int)
    resolucion_cambiada = pyqtSignal()  # cualquier cambio gráfico

    def __init__(self, parent=None):
        super().__init__(parent)

        # --- Declaración de todas las variables de instancia ---
        self.ui = None
        self._config_path = None
        self._volume = 100
        self._ds_renderer_index = 0    # 0=software, 1=opengl
        self._ds_resolution_index = 0  # 0..7 → 1x..8x
        self._citra_resolution_index = 0  # 0..9 → 1x..10x

        # --- Configuración de la UI ---
        self.ui = ConfigWindowUI()
        self.ui.setupUi(self)

        # Conectar señales
        self.ui.volumeSlider.valueChanged.connect(self._on_volume_changed)
        self.ui.dsRendererCombo.currentIndexChanged.connect(self._on_ds_renderer_changed)
        self.ui.dsResolutionCombo.currentIndexChanged.connect(self._on_ds_resolution_changed)
        self.ui.citraResolutionCombo.currentIndexChanged.connect(self._on_citra_resolution_changed)

        # Mostrar/ocultar resolución DS según renderizador
        self._actualizar_visibilidad_ds_res()

    def set_config_path(self, path):
        """Establece la ruta del archivo config.json y carga la configuración."""
        self._config_path = path
        self._cargar_config()
        # Aplicar valores cargados a los widgets (bloquear señales para no guardar de vuelta)
        self.ui.volumeSlider.setValue(self._volume)
        self.ui.volumeValueLabel.setText(f"{self._volume}%")
        self.ui.dsRendererCombo.setCurrentIndex(self._ds_renderer_index)
        self.ui.dsResolutionCombo.setCurrentIndex(self._ds_resolution_index)
        self.ui.citraResolutionCombo.setCurrentIndex(self._citra_resolution_index)
        self._actualizar_visibilidad_ds_res()

    # ── Propiedades ──

    @property
    def volume(self):
        return self._volume

    @property
    def ds_renderer_value(self):
        """Devuelve 'software' u 'opengl'."""
        return _DS_RENDERER_VALUES[self._ds_renderer_index]

    @property
    def ds_resolution_value(self):
        """Devuelve el string numérico que espera melonds_opengl_resolution."""
        return _DS_RES_VALUES[self._ds_resolution_index]

    @property
    def citra_resolution_value(self):
        """Devuelve el string que espera citra_resolution_factor."""
        return _CITRA_RES_VALUES[self._citra_resolution_index]

    # ── Slots ──

    def _on_volume_changed(self, value):
        self._volume = value
        self.ui.volumeValueLabel.setText(f"{value}%")
        self.volumen_cambiado.emit(value)
        self._guardar_config()

    def _on_ds_renderer_changed(self, index):
        if index < 0:
            return
        self._ds_renderer_index = index
        self._actualizar_visibilidad_ds_res()
        self.resolucion_cambiada.emit()
        self._guardar_config()

    def _on_ds_resolution_changed(self, index):
        if index < 0:
            return
        self._ds_resolution_index = index
        self.resolucion_cambiada.emit()
        self._guardar_config()

    def _on_citra_resolution_changed(self, index):
        if index < 0:
            return
        self._citra_resolution_index = index
        self.resolucion_cambiada.emit()
        self._guardar_config()

    def _actualizar_visibilidad_ds_res(self):
        """Muestra la resolución DS solo si el renderizador es OpenGL."""
        es_opengl = self._ds_renderer_index == 1
        self.ui.dsResolutionRow.setVisible(es_opengl)

    # ── Persistencia ──

    def _cargar_config(self):
        if self._config_path and os.path.exists(self._config_path):
            try:
                with open(self._config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                self._volume = cfg.get("volume", 100)
                self._ds_renderer_index = max(0, min(
                    cfg.get("ds_renderer_index", 0), len(_DS_RENDERER_VALUES) - 1))
                self._ds_resolution_index = max(0, min(
                    cfg.get("ds_resolution_index", 0), len(_DS_RES_VALUES) - 1))
                self._citra_resolution_index = max(0, min(
                    cfg.get("citra_resolution_index", 0), len(_CITRA_RES_VALUES) - 1))
            except Exception:
                pass

    def _guardar_config(self):
        if self._config_path:
            try:
                cfg = {
                    "volume": self._volume,
                    "ds_renderer_index": self._ds_renderer_index,
                    "ds_resolution_index": self._ds_resolution_index,
                    "citra_resolution_index": self._citra_resolution_index,
                }
                with open(self._config_path, "w", encoding="utf-8") as f:
                    json.dump(cfg, f, indent=2)
            except Exception:
                pass
