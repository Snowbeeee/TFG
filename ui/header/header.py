# ── Imports ──────────────────────────────────────────────────────
from PyQt6.QtWidgets import QFrame
from PyQt6.QtCore import pyqtSignal
from ui.header.headerUI import HeaderUI


# Barra de navegación superior con enlaces: Biblioteca / Configuración / Controles.
# Emite la señal 'navegacion' con el índice de la página seleccionada.
# Usa propiedades CSS dinámicas ("active") para resaltar el enlace activo.
class Header(QFrame):

    # Señal con el índice de página: 0=Biblioteca, 1=Configuración, 2=Controles
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

    # Actualiza el estado visual (propiedad CSS "active") y emite la señal.
    # unpolish/polish: necesario para que Qt reaplique los estilos QSS
    # al cambiar una propiedad dinámica como "active".
    def _navegar(self, index):
        for i, link in enumerate([self.ui.linkBiblioteca, self.ui.linkConfiguracion, self.ui.linkControles]):
            link.setProperty("active", index == i)
            link.style().unpolish(link)
            link.style().polish(link)
        self.navegacion.emit(index)

    # Cambia el enlace activo sin emitir señal (para sincronización externa)
    def set_active(self, index):
        for i, link in enumerate([self.ui.linkBiblioteca, self.ui.linkConfiguracion, self.ui.linkControles]):
            link.setProperty("active", index == i)
            link.style().unpolish(link)
            link.style().polish(link)
