# ── Imports ──────────────────────────────────────────────────────
import json
import os
import re
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QCheckBox, QLabel, QPushButton, QWidget
from PyQt6.QtCore import pyqtSignal, Qt
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
    cheats_cambiados = pyqtSignal(list)  # emite la lista completa de cheats al cambiar
    fast_forward_cambiado = pyqtSignal(bool)  # emite True/False al activar fast-forward
    fast_forward_speed_cambiada = pyqtSignal(int)  # emite frames extra por tick al cambiar velocidad

    def __init__(self, parent=None):
        super().__init__(parent)
        self._syncing = False  # evitar bucles al sincronizar
        self._cheats = []      # lista de {name, code, enabled}
        self._rom_name = None  # nombre del archivo ROM actual (para persistencia)
        self._editing_index = -1  # índice del cheat que se está editando (-1 = ninguno)

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
        self.ui.cheatAddButton.clicked.connect(self._on_add_cheat)
        self.ui.fastForwardButton.toggled.connect(self.fast_forward_cambiado.emit)
        self.ui.fastForwardSpeedCombo.currentIndexChanged.connect(self._on_ff_speed_changed)

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
        self.ui.cheatSectionWidget.setVisible(es_ds)
        self.ui.fastForwardSectionWidget.setVisible(es_ds)
        # Al cambiar de juego reseteamos el toggle para no arrastrar estado.
        # blockSignals evita emitir fast_forward_cambiado(False) durante el reset.
        self.ui.fastForwardButton.blockSignals(True)
        self.ui.fastForwardButton.setChecked(False)
        self.ui.fastForwardButton.blockSignals(False)

    # Carga los cheats del archivo JSON asociado a la ROM y actualiza la lista.
    def cargar_cheats(self, rom_name):
        self._rom_name = rom_name
        self._cheats = []
        path = self._cheats_path()
        if path and os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    self._cheats = json.load(f)
            except Exception as e:
                print(f"[Cheats] Error cargando cheats: {e}")
        self._rebuild_cheat_list()
        self.cheats_cambiados.emit(list(self._cheats))

    # ── Cheats internos ──

    def _cheats_path(self):
        if not self._rom_name:
            return None
        base = os.path.splitext(self._rom_name)[0]
        return os.path.abspath(os.path.join("saves", base + "_cheats.json"))

    def _guardar_cheats(self):
        path = self._cheats_path()
        if not path:
            return
        os.makedirs(os.path.dirname(path), exist_ok=True)
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self._cheats, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[Cheats] Error guardando cheats: {e}")

    # Normaliza un código Action Replay al formato esperado por DeSmuME libretro:
    # bloques de 8 dígitos hex separados por '+', sin espacios ni saltos de línea.
    # Acepta entrada con espacios, saltos de línea o '+' como separadores.
    @staticmethod
    def _normalizar_codigo(raw):
        # Extraer solo caracteres hex
        hex_chars = re.sub(r'[^0-9A-Fa-f]', '', raw).upper()
        # Cada bloque AR es de 8 dígitos. Debe haber un número par de bloques.
        if len(hex_chars) == 0 or len(hex_chars) % 8 != 0:
            return None
        blocks = [hex_chars[i:i+8] for i in range(0, len(hex_chars), 8)]
        # AR codes vienen en pares (dirección, valor). Si no es par, formato inválido.
        if len(blocks) % 2 != 0:
            return None
        # Juntar pares como "AAAAAAAA BBBBBBBB" y unir con '+'
        pares = [f"{blocks[i]} {blocks[i+1]}" for i in range(0, len(blocks), 2)]
        return '+'.join(pares)

    def _rebuild_cheat_list(self):
        layout = self.ui.cheatListLayout
        # Eliminar todos los widgets del layout excepto el stretch final
        while layout.count() > 1:
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for i, cheat in enumerate(self._cheats):
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(4)

            cb = QCheckBox()
            cb.setObjectName("cheatCheckBox")
            cb.setChecked(cheat.get('enabled', False))
            cb.toggled.connect(lambda checked, idx=i: self._on_toggle_cheat(idx, checked))

            name_label = QLabel(cheat.get('name', ''))
            name_label.setObjectName("cheatNameLabel")
            name_label.setToolTip(cheat.get('code', ''))

            edit_btn = QPushButton("✎")
            edit_btn.setObjectName("cheatEditButton")
            edit_btn.setFixedSize(20, 20)
            edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            edit_btn.clicked.connect(lambda _, idx=i: self._on_edit_cheat(idx))

            del_btn = QPushButton("×")
            del_btn.setObjectName("cheatDeleteButton")
            del_btn.setFixedSize(20, 20)
            del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            del_btn.clicked.connect(lambda _, idx=i: self._on_delete_cheat(idx))

            row.addWidget(cb)
            row.addWidget(name_label, 1)
            row.addWidget(edit_btn)
            row.addWidget(del_btn)

            row_widget = QWidget()
            row_widget.setObjectName("cheatRow")
            row_widget.setLayout(row)
            layout.insertWidget(layout.count() - 1, row_widget)

    def _on_add_cheat(self):
        name = self.ui.cheatNameInput.text().strip()
        code_raw = self.ui.cheatCodeInput.toPlainText().strip()
        if not name or not code_raw:
            return
        code = self._normalizar_codigo(code_raw)
        if code is None:
            self.ui.cheatCodeInput.setPlaceholderText("Código inválido (deben ser pares hex de 8 dígitos)")
            return

        if self._editing_index >= 0 and self._editing_index < len(self._cheats):
            # Modo edición: actualizar el cheat existente conservando enabled
            prev_enabled = self._cheats[self._editing_index].get('enabled', True)
            self._cheats[self._editing_index] = {'name': name, 'code': code, 'enabled': prev_enabled}
        else:
            self._cheats.append({'name': name, 'code': code, 'enabled': True})

        self._cancel_edit_mode()
        self._guardar_cheats()
        self._rebuild_cheat_list()
        self.cheats_cambiados.emit(list(self._cheats))

    def _on_edit_cheat(self, index):
        if not (0 <= index < len(self._cheats)):
            return
        c = self._cheats[index]
        self.ui.cheatNameInput.setText(c.get('name', ''))
        # Mostrar el código en formato legible (un par por línea)
        code = c.get('code', '')
        pares = code.split('+')
        self.ui.cheatCodeInput.setPlainText('\n'.join(p.strip() for p in pares))
        self._editing_index = index
        self.ui.cheatAddButton.setText("Guardar Cambios")

    def _cancel_edit_mode(self):
        self._editing_index = -1
        self.ui.cheatNameInput.clear()
        self.ui.cheatCodeInput.clear()
        self.ui.cheatCodeInput.setPlaceholderText("XXXXXXXX YYYYYYYY\nXXXXXXXX YYYYYYYY")
        self.ui.cheatAddButton.setText("Añadir Cheat")

    def _on_toggle_cheat(self, index, enabled):
        if 0 <= index < len(self._cheats):
            self._cheats[index]['enabled'] = enabled
            self._guardar_cheats()
            self.cheats_cambiados.emit(list(self._cheats))

    def _on_delete_cheat(self, index):
        if 0 <= index < len(self._cheats):
            self._cheats.pop(index)
            # Si estábamos editando este o uno posterior, ajustar
            if self._editing_index == index:
                self._cancel_edit_mode()
            elif self._editing_index > index:
                self._editing_index -= 1
            self._guardar_cheats()
            self._rebuild_cheat_list()
            self.cheats_cambiados.emit(list(self._cheats))

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

    # Devuelve los frames extra por tick seleccionados en el combo de velocidad.
    # El multiplicador real de velocidad es este valor + 1.
    @property
    def fast_forward_extra_frames(self):
        data = self.ui.fastForwardSpeedCombo.currentData()
        return int(data) if data is not None else 3

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

    def _on_ff_speed_changed(self, index):
        if index < 0:
            return
        self.fast_forward_speed_cambiada.emit(self.fast_forward_extra_frames)

    def _actualizar_visibilidad_ds_res(self):
        es_opengl = self.ui.dsRendererCombo.currentIndex() == 1
        self.ui.dsResolutionRow.setVisible(es_opengl)
