from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QMenuBar, QStatusBar,
    QHBoxLayout, QVBoxLayout, QPushButton
)
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtCore import QRect


class Ui_MainWindow:

    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1070, 703)

        # Central widget
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        MainWindow.setCentralWidget(self.centralwidget)

        # Layout principal para que el widget ocupe toda la ventana
        self.centralLayout = QVBoxLayout(self.centralwidget)
        self.centralLayout.setContentsMargins(0, 0, 0, 0)

        # Widget contenedor (rojo)
        self.widget = QWidget()
        self.widget.setObjectName("widget")
        self.centralLayout.addWidget(self.widget)

        # Layout horizontal que ocupa todo el widget
        self.horizontalLayout = QHBoxLayout(self.widget)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.horizontalLayout.setSpacing(30)
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)

        # Botón
        self.pushButton = QPushButton()
        self.pushButton.setObjectName("pushButton")
        self.horizontalLayout.addWidget(self.pushButton, 25)

        # OpenGL Widget (placeholder)
        self.openGLWidget = QOpenGLWidget()
        self.openGLWidget.setObjectName("openGLWidget")
        self.horizontalLayout.addWidget(self.openGLWidget, 50)

        # Botón
        self.pushButton = QPushButton()
        self.pushButton.setObjectName("pushButton")
        self.horizontalLayout.addWidget(self.pushButton, 25)

        # Menu bar
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName("menubar")
        self.menubar.setGeometry(QRect(0, 0, 1070, 33))
        MainWindow.setMenuBar(self.menubar)

        # Status bar
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        # Textos
        self.retranslateUi(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle("MainWindow")
        self.pushButton.setText("holaaaa")
