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

    def _navegar(self, index):
        """Actualiza el estado visual y emite la señal de navegación."""
        self.ui.linkBiblioteca.setProperty("active", index == 0)
        self.ui.linkConfiguracion.setProperty("active", index == 1)
        # Refrescar estilos para aplicar el estado active
        self.ui.linkBiblioteca.style().unpolish(self.ui.linkBiblioteca)
        self.ui.linkBiblioteca.style().polish(self.ui.linkBiblioteca)
        self.ui.linkConfiguracion.style().unpolish(self.ui.linkConfiguracion)
        self.ui.linkConfiguracion.style().polish(self.ui.linkConfiguracion)
        self.navegacion.emit(index)

    def set_active(self, index):
        """Cambia el enlace activo sin emitir señal."""
        self.ui.linkBiblioteca.setProperty("active", index == 0)
        self.ui.linkConfiguracion.setProperty("active", index == 1)
        self.ui.linkBiblioteca.style().unpolish(self.ui.linkBiblioteca)
        self.ui.linkBiblioteca.style().polish(self.ui.linkBiblioteca)
        self.ui.linkConfiguracion.style().unpolish(self.ui.linkConfiguracion)
        self.ui.linkConfiguracion.style().polish(self.ui.linkConfiguracion)
