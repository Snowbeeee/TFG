# ── Imports ──────────────────────────────────────────────────────
# QDialog: ventana modal de Qt (bloquea la interacción con la ventana padre)
from PyQt6.QtWidgets import QDialog, QWidget
from PyQt6.QtCore import Qt
# QPainter/QColor: necesarios para pintar el overlay semitransparente
from PyQt6.QtGui import QPainter, QColor


# Widget semitransparente que oscurece la ventana padre.
# WA_TranslucentBackground: permite que el fondo del widget sea transparente
# para que el fillRect con alpha sea visible (sin esto sería opaco).
class _Overlay(QWidget):

    def __init__(self, parent, on_click):
        super().__init__(parent)
        self._on_click = on_click
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 150))

    def mousePressEvent(self, event):
        self._on_click()


# Base para todos los popups: añade overlay oscuro sobre la ventana padre.
# FramelessWindowHint: elimina la barra de título del sistema para un look personalizado.
# setModal(True): bloquea la interacción con otras ventanas mientras está abierto.
class PopupBase(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setModal(True)

        # --- Declaración de todas las variables de instancia ---
        self._overlay = None

    # Sube por la jerarquía de widgets hasta encontrar la ventana raíz
    def _top_level_parent(self):
        widget = self.parent()
        while widget and widget.parent():
            widget = widget.parent()
        return widget

    def showEvent(self, event):
        super().showEvent(event)
        top = self._top_level_parent()
        if top:
            self._overlay = _Overlay(top, on_click=self.reject)
            self._overlay.setGeometry(top.rect())
            self._overlay.show()
            self._overlay.raise_()
            self.raise_()
            # Centrar el popup sobre la ventana padre
            geom = self.frameGeometry()
            geom.moveCenter(top.rect().center())
            self.move(top.mapToGlobal(geom.topLeft()))

    def closeEvent(self, event):
        self._remove_overlay()
        super().closeEvent(event)

    def hideEvent(self, event):
        self._remove_overlay()
        super().hideEvent(event)

    def _remove_overlay(self):
        if self._overlay is not None:
            self._overlay.deleteLater()
            self._overlay = None
