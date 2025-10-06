import sys
import PyQt6.QtWidgets as qtw
import PyQt6.QtCore as qtc
from DB.sqlite import CalendarDB
from MainWindow import MainWindow
import configparser
from LoginToken import generate_token, validate_token, save_token_to_file, load_token_from_file

class LoginView(qtw.QWidget):
    def __init__(self):
        super().__init__()
        self.db = CalendarDB()
        self.hide()
        if not self.auto_login():
            self.show()
        
        # Set up layout
        self.setWindowTitle("CalendAI - Login")
        self.setFixedSize(qtc.QSize(400, 400))
        layout = qtw.QVBoxLayout()
        self.setLayout(layout)

        # Add a label
        label = qtw.QLabel("Welcome to CalendAI")
        label.setAlignment(qtc.Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("font-size: 24px; font-weight: bold; margin: 10px;")
        layout.addWidget(label)

        # Add a username input
        self.username_input = qtw.QLineEdit()
        self.username_input.setPlaceholderText("Username")
        layout.addWidget(self.username_input)

        # Add a password input
        self.password_input = qtw.QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(qtw.QLineEdit.EchoMode.Password)
        layout.addWidget(self.password_input)


        self.remember_me = qtw.QCheckBox("Remember Me")
        layout.addWidget(self.remember_me)
        # Add a login button
        login_button = qtw.QPushButton("Login")
        login_button.setStyleSheet("font-size: 16px; padding: 8px; border-radius: 5px;")
        login_button.clicked.connect(self.handle_login)
        layout.addWidget(login_button)

        self.error_label = qtw.QLabel("")
        self.error_label.setStyleSheet("color: red;")
        layout.addWidget(self.error_label)

        # First, check if the user has a valid session/token
        if not self.auto_login():
            self.show()  # Only show the login window if auto-login fail

        

    def handle_login(self):
        username = self.username_input.text()
        password = self.password_input.text()
        print(username, password)
        if self.db.check_user(username, password):
            if self.remember_me.isChecked():
                self.save_credentials(username)
                token = generate_token(username)
                save_token_to_file(token)
            else:
                self.clear_credentials()
            self.accept_login()
        #placeholder for testing
        if username == "admin" and password == "password":
            if self.remember_me.isChecked():
                self.save_credentials(username)
                token = generate_token(username)
                save_token_to_file(token)
            else:
                self.clear_credentials()
            self.accept_login()
        else:
            self.error_label.setText("Invalid username or password")

    def auto_login(self):
        token = load_token_from_file()
        username = validate_token(token) if token else None
        print(f"Auto-login with token: {token}, username: {username}")
        if username:
            self.accept_login(username=username["username"])
            return True
        return False
    def accept_login(self, username=None):
        self.close()
        self.main_window = MainWindow(userid=self.db.get_user_id(username) if username else None)
        self.main_window.show()

    def save_credentials(self, username):
        config = configparser.ConfigParser()
        config['Credentials'] = {
            'username': username,
        }
        with open('credentials.ini', 'w') as configfile:
            config.write(configfile)


    def load_credentials(self):
        config = configparser.ConfigParser()
        try:
            config.read('credentials.ini')
            if 'Credentials' in config:
                self.username_input.setText(config['Credentials']['username'])
                # Password is hashed, so you can only compare it during login
                self.remember_me.setChecked(False)
        except Exception as e:
            print(f"Error loading credentials: {e}")


    def clear_credentials(self):
        try:
            import os
            if os.path.exists('credentials.ini'):
                os.remove('credentials.ini')
        except Exception as e:
            print(f"Error clearing credentials: {e}")
