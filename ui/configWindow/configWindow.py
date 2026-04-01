# ── Imports ──────────────────────────────────────────────────────
import os
import json
from PyQt6.QtWidgets import QWidget
# pyqtSignal: define señales personalizadas de Qt para comunicar eventos entre widgets
from PyQt6.QtCore import pyqtSignal
from ui.configWindow.configWindowUI import ConfigWindowUI

# ── Constantes ───────────────────────────────────────────────────
# Valores que el core Citra acepta para la opción "citra_resolution_factor"
_CITRA_RES_VALUES = [
    "1x (Native)", "2x", "3x", "4x", "5x",
    "6x", "7x", "8x", "9x", "10x",
]

# Valores que el core melonDS acepta para "melonds_render_mode"
_DS_RENDERER_VALUES = ["software", "opengl"]

# Valores que melonDS acepta para "melonds_opengl_resolution" (string numérico)
_DS_RES_VALUES = ["1", "2", "3", "4", "5", "6", "7", "8"]


# Página de configuración: gestiona ajustes de audio y gráficos persistentes.
# Los cambios se guardan automáticamente en config.json cada vez que el usuario
# modifica un slider o combo.
class ConfigWindow(QWidget):

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

    # Establece la ruta del archivo config.json y carga la configuración.
    # blockSignals no se usa aquí porque guardar de vuelta no causa bucle
    # (los valores ya son los mismos que se acaban de cargar).
    def set_config_path(self, path):
        self._config_path = path
        self._cargar_config()
        # Aplicar valores cargados a los widgets
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

    # Devuelve 'software' u 'opengl' según la selección actual
    @property
    def ds_renderer_value(self):
        return _DS_RENDERER_VALUES[self._ds_renderer_index]

    # Devuelve el string numérico que espera melonds_opengl_resolution
    @property
    def ds_resolution_value(self):
        return _DS_RES_VALUES[self._ds_resolution_index]

    # Devuelve el string que espera citra_resolution_factor
    @property
    def citra_resolution_value(self):
        return _CITRA_RES_VALUES[self._citra_resolution_index]

    # ── Slots ──
    # Los slots son métodos que Qt conecta a señales (patrón Observer).
    # Cada vez que el usuario modifica un widget, el slot correspondiente
    # actualiza el estado interno, emite una señal para notificar a otros
    # componentes y guarda la configuración en disco.

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

    # Muestra la resolución DS solo si el renderizador es OpenGL.
    # En modo software, melonDS no soporta resolución superior a 1x.
    def _actualizar_visibilidad_ds_res(self):
        es_opengl = self._ds_renderer_index == 1
        self.ui.dsResolutionRow.setVisible(es_opengl)

    # ── Persistencia ──
    # Lee config.json y aplica los valores guardados.
    # max(0, min(val, max)) asegura que el índice esté en rango válido
    # (por si se editó el JSON manualmente o cambió el número de opciones).
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

    # Guarda la configuración actual en config.json.
    # Lee el archivo primero para preservar claves que otros módulos hayan escrito
    # (por ejemplo, los bindings de controles) y sobreescribe solo los campos propios.
    def _guardar_config(self):
        if self._config_path:
            try:
                cfg = {}
                if os.path.exists(self._config_path):
                    with open(self._config_path, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                cfg["volume"] = self._volume
                cfg["ds_renderer_index"] = self._ds_renderer_index
                cfg["ds_resolution_index"] = self._ds_resolution_index
                cfg["citra_resolution_index"] = self._citra_resolution_index
                with open(self._config_path, "w", encoding="utf-8") as f:
                    json.dump(cfg, f, indent=2)
            except Exception:
                pass
