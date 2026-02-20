from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QMenuBar, QStatusBar,
    QVBoxLayout, QPushButton, QStackedWidget
)
from PyQt6.QtCore import QRect


class MainWindowUI:
    """UI principal: contiene un QStackedWidget para navegar entre páginas."""

    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1070, 703)

        # Central widget
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        MainWindow.setCentralWidget(self.centralwidget)

        # Layout principal
        self.centralLayout = QVBoxLayout(self.centralwidget)
        self.centralLayout.setContentsMargins(0, 0, 0, 0)

        # StackedWidget para alternar entre menú y juego
        self.stackedWidget = QStackedWidget()
        self.stackedWidget.setObjectName("stackedWidget")
        self.centralLayout.addWidget(self.stackedWidget)

        # --- Página 0: Menú principal ---
        self.menuPage = QWidget()
        self.menuPage.setObjectName("menuPage")
        self.menuPageLayout = QVBoxLayout(self.menuPage)
        self.menuPageLayout.setContentsMargins(50, 50, 50, 50)

        self.menuPageLayout.addStretch()

        self.pushButtonJugar = QPushButton()
        self.pushButtonJugar.setObjectName("pushButtonJugar")
        self.pushButtonJugar.setText("Jugar")
        self.menuPageLayout.addWidget(self.pushButtonJugar)

        self.menuPageLayout.addStretch()

        self.stackedWidget.addWidget(self.menuPage)  # index 0

        # Menu bar
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName("menubar")
        self.menubar.setGeometry(QRect(0, 0, 1070, 33))
        MainWindow.setMenuBar(self.menubar)

        # Status bar
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle("TFG - Emulador")
