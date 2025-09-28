import sys
from PyQt6.QtWidgets import QApplication
from LoginView import LoginView

if __name__ == "__main__":
    app = QApplication(sys.argv)

    login_view = LoginView()

    sys.exit(app.exec())
