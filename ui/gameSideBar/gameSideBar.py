# ── Imports ──────────────────────────────────────────────────────
from PyQt6.QtWidgets import QFrame, QVBoxLayout
from PyQt6.QtCore import pyqtSignal
from ui.gameSideBar.gameSideBarUI import GameSideBarUI


# Barra lateral que aparece durante la partida con ajustes rápidos.
# Actúa como espejo de ConfigWindow: ambos leen/escriben los mismos valores.
# La sincronización bidireccional se gestiona desde MainWindow conectando
# las señales de ambos lados (patrón Observer de Qt).
# _syncing: flag para evitar bucles infinitos al sincronizar
# (ej: ConfigWindow cambia volumen → sync_from_config → valueChanged → volumen_cambiado → loop)
class GameSideBar(QFrame):

    volumen_cambiado = pyqtSignal(int)
    resolucion_cambiada = pyqtSignal()
    salir_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._syncing = False  # evitar bucles al sincronizar

        # Layout para contener la UI
        wrapper = QVBoxLayout(self)
        wrapper.setContentsMargins(0, 0, 0, 0)

        # UI
        self.ui = GameSideBarUI()
        wrapper.addWidget(self.ui)

        # Conectar señales internas
        self.ui.volumeSlider.valueChanged.connect(self._on_volume_changed)
        self.ui.dsRendererCombo.currentIndexChanged.connect(self._on_ds_renderer_changed)
        self.ui.dsResolutionCombo.currentIndexChanged.connect(self._on_ds_resolution_changed)
        self.ui.citraResolutionCombo.currentIndexChanged.connect(self._on_citra_resolution_changed)
        self.ui.pushButtonSalir.clicked.connect(self.salir_clicked.emit)

        self._actualizar_visibilidad_ds_res()

    # ── Sincronización desde ConfigWindow ──

    # Actualiza todos los widgets para reflejar los valores de ConfigWindow.
    # _syncing = True evita que los valueChanged emitan señales de vuelta.
    def sync_from_config(self, volume, ds_renderer_idx, ds_resolution_idx, citra_resolution_idx):
        self._syncing = True
        self.ui.volumeSlider.setValue(volume)
        self.ui.volumeValueLabel.setText(f"{volume}%")
        self.ui.dsRendererCombo.setCurrentIndex(ds_renderer_idx)
        self.ui.dsResolutionCombo.setCurrentIndex(ds_resolution_idx)
        self.ui.citraResolutionCombo.setCurrentIndex(citra_resolution_idx)
        self._actualizar_visibilidad_ds_res()
        self._syncing = False

    # Muestra solo la sección de gráficos relevante para la consola del juego actual
    def set_consola(self, extension):
        es_ds = extension == ".nds"
        es_3ds = extension == ".3ds"
        self.ui.dsSectionWidget.setVisible(es_ds)
        self.ui.citraSectionWidget.setVisible(es_3ds)

    # ── Lectores (para que MainWindow lea los valores actuales) ──

    @property
    def volume(self):
        return self.ui.volumeSlider.value()

    @property
    def ds_renderer_index(self):
        return self.ui.dsRendererCombo.currentIndex()

    @property
    def ds_resolution_index(self):
        return self.ui.dsResolutionCombo.currentIndex()

    @property
    def citra_resolution_index(self):
        return self.ui.citraResolutionCombo.currentIndex()

    # ── Slots internos ──

    def _on_volume_changed(self, value):
        self.ui.volumeValueLabel.setText(f"{value}%")
        if not self._syncing:
            self.volumen_cambiado.emit(value)

    def _on_ds_renderer_changed(self, index):
        if index < 0:
            return
        self._actualizar_visibilidad_ds_res()
        if not self._syncing:
            self.resolucion_cambiada.emit()

    def _on_ds_resolution_changed(self, index):
        if index < 0:
            return
        if not self._syncing:
            self.resolucion_cambiada.emit()

    def _on_citra_resolution_changed(self, index):
        if index < 0:
            return
        if not self._syncing:
            self.resolucion_cambiada.emit()

    def _actualizar_visibilidad_ds_res(self):
        es_opengl = self.ui.dsRendererCombo.currentIndex() == 1
        self.ui.dsResolutionRow.setVisible(es_opengl)
