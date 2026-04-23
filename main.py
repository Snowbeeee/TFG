import sys
import os
from PyQt6.QtWidgets import QApplication
from ui.mainWindow.mainWindow import MainWindow

# Devuelve la ruta base del proyecto, compatible con PyInstaller.
def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

if __name__ == "__main__":
    # Establecer CWD al directorio del exe/script para que las rutas relativas funcionen
    os.chdir(get_base_path())
    
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
