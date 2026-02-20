import os
from PyQt6.QtWidgets import QMainWindow
from PyQt6.QtCore import QTimer
from ui.principal_ui import Ui_MainWindow
from ui.retro_gl_widget import RetroOpenGLWidget


def _get_resource_path(relative_path):
    """Devuelve la ruta a un recurso empaquetado (ej: ui/)."""
    import sys
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, relative_path)
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base, relative_path)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # Cargar UI desde Python (reemplaza al .ui)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        
        # Cargar hoja de estilos
        qss_path = _get_resource_path(os.path.join("ui", "styles.qss"))
        if os.path.exists(qss_path):
            with open(qss_path, "r") as f:
                self.setStyleSheet(f.read())
        
        # Cargar UI desde .ui (comentado)
        # from PyQt6 import uic
        # ui_path = _get_resource_path(os.path.join("ui", "principal.ui"))
        # uic.loadUi(ui_path, self)
        
        # Reemplazar el openGLWidget placeholder por el nuestro
        old_widget = self.ui.openGLWidget
        if old_widget:
            parent = old_widget.parent()
            layout = parent.layout() if parent else None
            
            # Crear nueva instancia
            self.game_widget = RetroOpenGLWidget(parent)
            
            if layout:
                # El widget está en un layout: reemplazarlo en su posición con su stretch
                index = layout.indexOf(old_widget)
                stretch = layout.stretch(index) if hasattr(layout, 'stretch') else 0
                layout.removeWidget(old_widget)
                old_widget.setParent(None)
                old_widget.deleteLater()
                layout.insertWidget(index, self.game_widget, stretch)
            else:
                # Sin layout: heredar geometría absoluta del placeholder
                geometry = old_widget.geometry()
                old_widget.setParent(None)
                old_widget.deleteLater()
                self.game_widget.setGeometry(geometry)
            
            self.game_widget.show()
            self.game_widget.setFocus()
            
            # Timer para actualizar renderizado (60 FPS approx)
            self.timer = QTimer()
            self.timer.timeout.connect(self.game_widget.update)
            self.timer.start(16)
        else:
            print("Error: No se encontró 'openGLWidget' en la UI.")

    def closeEvent(self, event):
        if hasattr(self, 'game_widget'):
            self.game_widget.closeEvent(event)
        super().closeEvent(event)
