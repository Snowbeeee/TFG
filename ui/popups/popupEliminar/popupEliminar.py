# ── Imports ──────────────────────────────────────────────────────
from ui.popups.popupBase import PopupBase
from ui.popups.popupEliminar.popupEliminarUI import PopupEliminarUI


# Popup de confirmación para eliminar una carpeta.
# accept() = confirmar eliminación; reject() = cancelar.
class PopupEliminar(PopupBase):

    def __init__(self, nombre_lista, parent=None):
        super().__init__(parent)

        # --- Declaración de todas las variables de instancia ---
        self.ui = None

        # --- Configuración de la UI ---
        self.ui = PopupEliminarUI()
        self.ui.setupUi(self, nombre_lista)

        # Conectar botones
        self.ui.btnEliminar.clicked.connect(self.accept)
        self.ui.btnCancelar.clicked.connect(self.reject)
