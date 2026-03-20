from PyQt6.QtWidgets import QFrame
from PyQt6.QtCore import pyqtSignal
from ui.header.headerUI import HeaderUI


class Header(QFrame):
    """Barra de navegación con enlaces Biblioteca / Configuración."""

    navegacion = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)

        # --- Declaración de todas las variables de instancia ---
        self.ui = None

        # --- Configuración de la UI ---
        self.ui = HeaderUI()
        self.ui.setupUi(self)

        # Conectar botones
        self.ui.linkBiblioteca.clicked.connect(lambda: self._navegar(0))
        self.ui.linkConfiguracion.clicked.connect(lambda: self._navegar(1))
        self.ui.linkControles.clicked.connect(lambda: self._navegar(2))

    def _navegar(self, index):
        """Actualiza el estado visual y emite la señal de navegación."""
        for i, link in enumerate([self.ui.linkBiblioteca, self.ui.linkConfiguracion, self.ui.linkControles]):
            link.setProperty("active", index == i)
            link.style().unpolish(link)
            link.style().polish(link)
        self.navegacion.emit(index)

    def set_active(self, index):
        """Cambia el enlace activo sin emitir señal."""
        for i, link in enumerate([self.ui.linkBiblioteca, self.ui.linkConfiguracion, self.ui.linkControles]):
            link.setProperty("active", index == i)
            link.style().unpolish(link)
            link.style().polish(link)
