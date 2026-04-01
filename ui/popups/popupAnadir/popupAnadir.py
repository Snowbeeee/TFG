# ── Imports ──────────────────────────────────────────────────────
from ui.popups.popupBase import PopupBase
from ui.popups.popupAnadir.popupAnadirUI import PopupAnadirUI


# Popup para introducir el nombre de una nueva carpeta/lista.
# accept(): cierra el dialogo con código QDialog.Accepted.
# reject(): cierra con código QDialog.Rejected.
class PopupAnadir(PopupBase):

    def __init__(self, parent=None):
        super().__init__(parent)

        # --- Declaración de todas las variables de instancia ---
        self.ui = None
        self._nombre = ""

        # --- Configuración de la UI ---
        self.ui = PopupAnadirUI()
        self.ui.setupUi(self)

        # Conectar botones
        self.ui.btnAceptar.clicked.connect(self._aceptar)
        self.ui.btnCancelar.clicked.connect(self.reject)
        self.ui.inputField.returnPressed.connect(self._aceptar)

    # Devuelve el nombre introducido por el usuario
    @property
    def nombre(self):
        return self._nombre

    def _aceptar(self):
        texto = self.ui.inputField.text().strip()
        if texto:
            self._nombre = texto
            self.accept()
