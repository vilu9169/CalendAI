import PyQt6.QtWidgets as qtw
import PyQt6.QtCore as qtc
import sys
from CalendarView import CalendarView
from ChatView import ChatView
from TaskView import TaskView

class MainWindow(qtw.QMainWindow):
    def __init__(self, userid=None):
        super().__init__()
        main_color = "#352F44"
        second_color = "#5C5470"
        third_color = "#B9B4C7"
        fourth_color = "#FAF0E6"
        palette = [main_color, second_color, third_color, fourth_color]
        self.setWindowTitle("CalendAI")
        self.setFixedSize(qtc.QSize(900, 600))
        self.setStyleSheet(f"background-color: {main_color}; color: {fourth_color};")
        main_widget = qtw.QWidget(self)
        self.setCentralWidget(main_widget)
        self.userID = userid  # Set this when user logs in

        splitter = qtw.QSplitter(qtc.Qt.Orientation.Horizontal)
        nav_panel = qtw.QWidget()
        nav_layout = qtw.QVBoxLayout()
        nav_panel.setLayout(nav_layout)
        nav_panel.setStyleSheet(f"color: {fourth_color}; border-right: 1px solid {second_color};")
        nav_buttons = [
            qtw.QPushButton("Home"),
            qtw.QPushButton("Calendar"),
            qtw.QPushButton("Tasks"),
            qtw.QPushButton("Settings")
        ]
        for button in nav_buttons:
            nav_layout.addWidget(button)

        nav_layout.addStretch()
        main_content = qtw.QStackedWidget()

        self.home_view = ChatView(palette, userid=self.userID)
        self.calendar_view = CalendarView(palette, user_id=self.userID)
        self.tasks_view = TaskView(palette, user_id=self.userID)
        self.settings_view = qtw.QLabel("Settings View")


        views = [
            self.home_view,
            self.calendar_view,
            self.tasks_view,
            self.settings_view
        ]
        for label in [self.settings_view]:
            label.setAlignment(qtc.Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("font-size: 20px; text-align: center;")
        for view in views:
            main_content.addWidget(view)

        for i, button in enumerate(nav_buttons):
            button.clicked.connect(lambda checked, i=i: main_content.setCurrentWidget(views[i]))

        splitter.addWidget(nav_panel)
        splitter.addWidget(main_content)
        splitter.setSizes([200, 700])

        # Add buttons to the layout

        main_layout = qtw.QHBoxLayout()
        main_layout.addWidget(splitter)
        main_widget.setLayout(main_layout)
