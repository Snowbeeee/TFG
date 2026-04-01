# ── Imports ──────────────────────────────────────────────────────
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap


# Define el layout de la página de detalle de un juego.
# Layout: barra superior (volver/menú) + área scrollable con portada,
# metadatos, descripción, botón de jugar y galería de imágenes.
class GameDetailPageUI:

    def __init__(self):
        self.btn_volver = None
        self.btn_jugar = None
        self.btn_menu = None
        self.cover_label = None
        self.titulo_label = None
        self.consola_label = None
        self.fecha_label = None
        self.generos_label = None
        self.editeur_label = None
        self.developpeur_label = None
        self.jugadores_label = None
        self.descripcion_label = None
        self.gallery_scroll = None
        self.gallery_container = None
        self.gallery_layout = None
        self.loading_label = None

    def setupUi(self, widget):
        widget.setObjectName("gameDetailPage")

        main_layout = QVBoxLayout(widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Barra superior ──
        top_bar = QWidget()
        top_bar.setObjectName("detailTopBar")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(20, 10, 20, 10)

        self.btn_volver = QPushButton("← Volver")
        self.btn_volver.setObjectName("detailBackBtn")
        self.btn_volver.setCursor(Qt.CursorShape.PointingHandCursor)
        top_layout.addWidget(self.btn_volver)

        top_layout.addStretch()

        self.btn_menu = QPushButton("⋯")
        self.btn_menu.setObjectName("detailMenuBtn")
        self.btn_menu.setFixedWidth(40)
        self.btn_menu.setCursor(Qt.CursorShape.PointingHandCursor)
        top_layout.addWidget(self.btn_menu)

        main_layout.addWidget(top_bar)

        # ── Área scrollable con el contenido ──
        scroll = QScrollArea()
        scroll.setObjectName("detailScrollArea")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        main_layout.addWidget(scroll)

        content = QWidget()
        content.setObjectName("detailContent")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(40, 20, 40, 30)
        content_layout.setSpacing(24)
        scroll.setWidget(content)

        # ── Layout principal: Portada (izq) + todo el contenido (der) ──
        main_row = QHBoxLayout()
        main_row.setSpacing(30)

        self.cover_label = QLabel()
        self.cover_label.setObjectName("detailCover")
        self.cover_label.setFixedSize(280, 380)
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover_label.setText("Sin carátula")
        main_row.addWidget(self.cover_label,
                           alignment=Qt.AlignmentFlag.AlignTop)

        # Panel derecho: título + dos columnas + botón
        right_panel = QVBoxLayout()
        right_panel.setSpacing(16)

        self.titulo_label = QLabel()
        self.titulo_label.setObjectName("detailTitle")
        self.titulo_label.setWordWrap(True)
        right_panel.addWidget(self.titulo_label)

        # Dos columnas: descripción (izq) + metadatos (der)
        columns = QHBoxLayout()
        columns.setSpacing(24)

        # Columna izquierda – descripción
        self.descripcion_label = QLabel()
        self.descripcion_label.setObjectName("detailDescription")
        self.descripcion_label.setWordWrap(True)
        self.descripcion_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        columns.addWidget(self.descripcion_label, 3,
                          Qt.AlignmentFlag.AlignTop)

        # Columna derecha – metadatos
        details = QVBoxLayout()
        details.setSpacing(10)

        self.consola_label = QLabel()
        self.consola_label.setObjectName("detailConsole")
        details.addWidget(self.consola_label)

        self.fecha_label = QLabel()
        self.fecha_label.setObjectName("detailDate")
        details.addWidget(self.fecha_label)

        self.generos_label = QLabel()
        self.generos_label.setObjectName("detailGenres")
        self.generos_label.setWordWrap(True)
        details.addWidget(self.generos_label)

        self.editeur_label = QLabel()
        self.editeur_label.setObjectName("detailPublisher")
        details.addWidget(self.editeur_label)

        self.developpeur_label = QLabel()
        self.developpeur_label.setObjectName("detailDeveloper")
        details.addWidget(self.developpeur_label)

        self.jugadores_label = QLabel()
        self.jugadores_label.setObjectName("detailPlayers")
        details.addWidget(self.jugadores_label)

        details.addStretch()

        details_wrapper = QWidget()
        details_wrapper.setLayout(details)
        columns.addWidget(details_wrapper, 2,
                          Qt.AlignmentFlag.AlignTop)

        right_panel.addLayout(columns)

        # Botón Jugar (sencillo)
        btn_row = QHBoxLayout()
        self.btn_jugar = QPushButton("▶  Jugar")
        self.btn_jugar.setObjectName("detailPlayBtn")
        self.btn_jugar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_row.addWidget(self.btn_jugar)
        btn_row.addStretch()
        right_panel.addLayout(btn_row)

        main_row.addLayout(right_panel, 1)
        content_layout.addLayout(main_row)

        # ── Galería ──
        gallery_header = QLabel("Galería")
        gallery_header.setObjectName("detailSectionHeader")
        content_layout.addWidget(gallery_header)

        self.gallery_scroll = QScrollArea()
        self.gallery_scroll.setObjectName("detailGalleryScroll")
        self.gallery_scroll.setWidgetResizable(True)
        self.gallery_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.gallery_scroll.setFixedHeight(260)
        self.gallery_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.gallery_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.gallery_container = QWidget()
        self.gallery_container.setObjectName("detailGalleryContainer")
        self.gallery_layout = QHBoxLayout(self.gallery_container)
        self.gallery_layout.setSpacing(12)
        self.gallery_layout.setContentsMargins(0, 0, 0, 0)
        self.gallery_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.gallery_scroll.setWidget(self.gallery_container)

        content_layout.addWidget(self.gallery_scroll)

        # ── Loading ──
        self.loading_label = QLabel("Buscando información del juego…")
        self.loading_label.setObjectName("detailLoading")
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_label.hide()
        content_layout.addWidget(self.loading_label)

        content_layout.addStretch()

    # ── Métodos auxiliares de presentación ──

    # Establece la imagen de portada, escalada proporcionalmente
    def set_cover(self, ruta):
        if ruta and os.path.exists(ruta):
            pixmap = QPixmap(ruta).scaled(
                280, 380,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.cover_label.setPixmap(pixmap)
        else:
            self.cover_label.setPixmap(QPixmap())
            self.cover_label.setText("Sin carátula")

    # Rellena los labels con la información del juego (sin tocar el título).
    # setVisible(bool): oculta los campos vacíos para no dejar huecos en la UI.
    def set_info(self, info):
        consola = info.get("consola", "")
        self.consola_label.setText(f"🎮  {consola}" if consola else "")
        self.consola_label.setVisible(bool(consola))

        fecha = info.get("fecha_lanzamiento", "")
        self.fecha_label.setText(f"📅  {fecha}" if fecha else "")
        self.fecha_label.setVisible(bool(fecha))

        generos = info.get("generos", [])
        self.generos_label.setText(
            f"🏷️  {', '.join(generos)}" if generos else "")
        self.generos_label.setVisible(bool(generos))

        editeur = info.get("editeur", "")
        self.editeur_label.setText(
            f"📦  Editor: {editeur}" if editeur else "")
        self.editeur_label.setVisible(bool(editeur))

        dev = info.get("developpeur", "")
        self.developpeur_label.setText(
            f"💻  Desarrollador: {dev}" if dev else "")
        self.developpeur_label.setVisible(bool(dev))

        jugadores = info.get("jugadores", "")
        self.jugadores_label.setText(
            f"👥  Jugadores: {jugadores}" if jugadores else "")
        self.jugadores_label.setVisible(bool(jugadores))

        desc = info.get("descripcion", "")
        self.descripcion_label.setText(
            desc if desc else "Sin descripción disponible.")

    # Carga las miniaturas de la galería horizontal.
    # Primero limpia las imágenes anteriores con deleteLater() (liberación segura en Qt).
    def set_galeria(self, rutas_imagenes):
        # Eliminar widgets previos del layout
        while self.gallery_layout.count():
            item = self.gallery_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not rutas_imagenes:
            lbl = QLabel("No hay imágenes disponibles")
            lbl.setObjectName("detailNoImages")
            self.gallery_layout.addWidget(lbl)
            return

        for ruta in rutas_imagenes:
            if not os.path.exists(ruta):
                continue
            lbl = QLabel()
            lbl.setObjectName("detailGalleryImage")
            pixmap = QPixmap(ruta).scaled(
                300, 230,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            lbl.setPixmap(pixmap)
            lbl.setFixedSize(pixmap.size())
            self.gallery_layout.addWidget(lbl)

    def mostrar_cargando(self, visible):
        self.loading_label.setVisible(visible)
