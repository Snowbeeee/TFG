# ── Imports ──────────────────────────────────────────────────────
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QScrollArea, QFrame, QTabWidget
)
from PyQt6.QtCore import Qt

# ── Constantes ───────────────────────────────────────────────────
# Tuplas (nombre_display, clave_config) para los botones de cada consola.
# nombre_display se muestra en la UI; clave_config se usa como key en el dict de bindings.

# Botones DS:  (nombre_display, clave_config)
_DS_BUTTONS = [
    ("A",       "a"),
    ("B",       "b"),
    ("X",       "x"),
    ("Y",       "y"),
    ("L",       "l"),
    ("R",       "r"),
    ("START",   "start"),
    ("SELECT",  "select"),
    ("↑ D-Pad", "up"),
    ("↓ D-Pad", "down"),
    ("← D-Pad", "left"),
    ("→ D-Pad", "right"),
]

# Botones 3DS (incluye todos los de DS + ZL, ZR y Circle Pad)
_3DS_EXTRA_BUTTONS = [
    ("A",       "a"),
    ("B",       "b"),
    ("X",       "x"),
    ("Y",       "y"),
    ("L",       "l"),
    ("R",       "r"),
    ("ZL",      "zl"),
    ("ZR",      "zr"),
    ("START",   "start"),
    ("SELECT",  "select"),
    ("↑ D-Pad", "up"),
    ("↓ D-Pad", "down"),
    ("← D-Pad", "left"),
    ("→ D-Pad", "right"),
    ("Circle Pad ↑", "circle_up"),
    ("Circle Pad ↓", "circle_down"),
    ("Circle Pad ←", "circle_left"),
    ("Circle Pad →", "circle_right"),
]


# Define el layout de la página de controles.
# Tiene dos pestañas (QTabWidget): una para DS y otra para 3DS.
# Cada pestaña tiene una rejilla (QGridLayout) con etiqueta + botón por cada control.
class ControlsWindowUI:

    def __init__(self):
        self.tabWidget = None
        # dict de clave_config → QPushButton para cada pestaña
        self.ds_bind_buttons = {}
        self.n3ds_bind_buttons = {}
        self.ds_reset_btn = None
        self.n3ds_reset_btn = None

    # Construye el layout completo de controles.
    # QScrollArea: contenedor con scroll para cuando hay muchos botones.
    # QGridLayout: rejilla de 2 columnas (etiqueta | botón de binding).
    def setupUi(self, parent):
        parent.setObjectName("controlsPage")

        mainLayout = QVBoxLayout(parent)
        mainLayout.setContentsMargins(40, 30, 40, 30)
        mainLayout.setSpacing(20)

        titulo = QLabel("Controles")
        titulo.setObjectName("controlsSectionTitle")
        mainLayout.addWidget(titulo)

        instrucciones = QLabel(
            "Haz clic en un campo y pulsa la tecla o botón del mando que quieras asignar."
        )
        instrucciones.setObjectName("controlsHelpLabel")
        instrucciones.setWordWrap(True)
        mainLayout.addWidget(instrucciones)

        # Pestañas DS / 3DS
        self.tabWidget = QTabWidget()
        self.tabWidget.setObjectName("controlsTabs")
        mainLayout.addWidget(self.tabWidget)

        # --- Pestaña DS ---
        ds_page = QWidget()
        ds_layout = QVBoxLayout(ds_page)
        ds_layout.setContentsMargins(10, 15, 10, 10)
        ds_layout.setSpacing(0)

        ds_scroll = QScrollArea()
        ds_scroll.setObjectName("controlsScroll")
        ds_scroll.setWidgetResizable(True)
        ds_scroll.setFrameShape(QFrame.Shape.NoFrame)

        ds_grid_widget = QWidget()
        ds_grid = QGridLayout(ds_grid_widget)
        ds_grid.setSpacing(8)
        ds_grid.setContentsMargins(0, 0, 0, 0)

        for row, (display, key) in enumerate(_DS_BUTTONS):
            lbl = QLabel(display)
            lbl.setObjectName("controlsButtonLabel")
            lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            lbl.setFixedWidth(140)
            ds_grid.addWidget(lbl, row, 0)

            btn = QPushButton("Sin asignar")
            btn.setObjectName("controlsBindButton")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(36)
            ds_grid.addWidget(btn, row, 1)

            self.ds_bind_buttons[key] = btn

        ds_grid.setRowStretch(len(_DS_BUTTONS), 1)
        ds_scroll.setWidget(ds_grid_widget)
        ds_layout.addWidget(ds_scroll)

        self.ds_reset_btn = QPushButton("Restablecer valores por defecto")
        self.ds_reset_btn.setObjectName("controlsResetButton")
        self.ds_reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        ds_layout.addWidget(self.ds_reset_btn, alignment=Qt.AlignmentFlag.AlignRight)

        self.tabWidget.addTab(ds_page, "Nintendo DS")

        # --- Pestaña 3DS ---
        n3ds_page = QWidget()
        n3ds_layout = QVBoxLayout(n3ds_page)
        n3ds_layout.setContentsMargins(10, 15, 10, 10)
        n3ds_layout.setSpacing(0)

        n3ds_scroll = QScrollArea()
        n3ds_scroll.setObjectName("controlsScroll")
        n3ds_scroll.setWidgetResizable(True)
        n3ds_scroll.setFrameShape(QFrame.Shape.NoFrame)

        n3ds_grid_widget = QWidget()
        n3ds_grid = QGridLayout(n3ds_grid_widget)
        n3ds_grid.setSpacing(8)
        n3ds_grid.setContentsMargins(0, 0, 0, 0)

        for row, (display, key) in enumerate(_3DS_EXTRA_BUTTONS):
            lbl = QLabel(display)
            lbl.setObjectName("controlsButtonLabel")
            lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            lbl.setFixedWidth(140)
            n3ds_grid.addWidget(lbl, row, 0)

            btn = QPushButton("Sin asignar")
            btn.setObjectName("controlsBindButton")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(36)
            n3ds_grid.addWidget(btn, row, 1)

            self.n3ds_bind_buttons[key] = btn

        n3ds_grid.setRowStretch(len(_3DS_EXTRA_BUTTONS), 1)
        n3ds_scroll.setWidget(n3ds_grid_widget)
        n3ds_layout.addWidget(n3ds_scroll)

        self.n3ds_reset_btn = QPushButton("Restablecer valores por defecto")
        self.n3ds_reset_btn.setObjectName("controlsResetButton")
        self.n3ds_reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        n3ds_layout.addWidget(self.n3ds_reset_btn, alignment=Qt.AlignmentFlag.AlignRight)

        self.tabWidget.addTab(n3ds_page, "Nintendo 3DS")
