import PyQt6.QtCore as qtc
import PyQt6.QtWidgets as qtw
from ai_call import ai_call, function_call # Assuming you have a module `ai_call` for API integration
from DB.sqlite import CalendarDB

class ChatView(qtw.QWidget):
    def _to_safe_text(self, obj) -> str:
        """
        Convert any value (None, object with .content, dict, etc.) into a non-empty string
        suitable for UI and DB storage.
        """
        # 1) ChatCompletion-like object with .content
        content = getattr(obj, "content", None)
        if isinstance(content, str) and content.strip():
            return content

        # 2) Plain string
        if isinstance(obj, str) and obj.strip():
            return obj

        # 3) Tool-call only or empty/None: give a friendly placeholder
        # (You can customize this text)
        return "[no text content]"
        

    def _sanitized_history(self):
        """
        Return self.messages in a format safe for the OpenAI API:
        - drop entries with None/empty content
        - ensure content is a string
        """
        safe = []
        for m in self.messages:
            role = m.get("role", "user")
            content = m.get("content")
            text = self._to_safe_text(content)
            if text == "[no text content]":
                # skip empty messages for API calls to avoid
                # 'Invalid value for content: expected string, got null'
                continue
            safe.append({"role": role, "content": text})
        return safe


    def __init__(self, palette):
        super().__init__()
        # Set up layout
        self.db = CalendarDB()
        self.messages = self.db.get_messages(conversation_id=1)
        self.second_color = palette[1]
        self.third_color = palette[2]
        self.fourth_color = palette[3]
        print(self.messages)

        self.layout = qtw.QVBoxLayout()
        self.setLayout(self.layout)
        print(palette)
        # Add a label
        label = qtw.QLabel("Chat with AI")
        label.setAlignment(qtc.Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("font-size: 24px; font-weight: bold; margin: 10px;")
        self.layout.addWidget(label)

        # Add a scroll area for messages
        self.messages_widget = qtw.QWidget()
        self.messages_layout = qtw.QVBoxLayout()
        self.messages_layout.setAlignment(qtc.Qt.AlignmentFlag.AlignTop)
        self.messages_widget.setLayout(self.messages_layout)
        self.scroll_area = qtw.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.messages_widget)
        self.scroll_area.verticalScrollBar().rangeChanged.connect(self.scrollToBottom)
        
        self.layout.addWidget(self.scroll_area)
        for message in self.messages:
            if 'content' in message and 'role' in message:
                self.add_message(message['content'], message['role'])
            else:
                print(f"Malformed message data: {message}")
        # Add a text edit widget
        self.text_edit = qtw.QTextEdit()
        self.text_edit.setPlaceholderText("Type your message here...")
        self.text_edit.setFixedHeight(100)
        self.text_edit.setStyleSheet(
            f"border: 1px solid {self.second_color}; border-radius: 5px; padding: 5px;"
        )
        self.layout.addWidget(self.text_edit)

        # Add a send button
        send_button = qtw.QPushButton("Send")
        send_button.setStyleSheet(
            "font-size: 16px; padding: 8px; border-radius: 5px;"
        )
        send_button.clicked.connect(self.handle_send_message)
        self.layout.addWidget(send_button)

    def scrollToBottom (self, minVal=None, maxVal=None):
    # Additional params 'minVal' and 'maxVal' are declared because
    # rangeChanged signal sends them, but we set it to optional
    # because we may need to call it separately (if you need).
        
        self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        )

    def handle_send_message(self):
        text = self.text_edit.toPlainText().strip()
        if not text:
            return


        self.add_message(text, "user")
        self.messages.append({"role": "user", "content": text})
        self.text_edit.clear()
        self.db.save_message(conversation_id=1, sender="user", message=text)

        print("mes: ", self.messages)


        ai_response, event = self.get_ai_response(text)

        ai_text = self._to_safe_text(ai_response)


        self.add_message(ai_text, "ai")
        self.messages.append({"role": "assistant", "content": ai_text})


        metadata = None
        if hasattr(ai_response, "model_dump"):
            try:
                metadata = ai_response.model_dump()
            except Exception:
                metadata = None

        self.db.save_message(
            conversation_id=1,
            sender="assistant",
            message=ai_text,
            metadata=metadata
        )
        if event:
            self.add_event_suggestion_widget(event)

    def add_message(self, text, role):
        """Add a message to the UI and the messages list."""
        text = self._to_safe_text(text)
        message_layout = qtw.QHBoxLayout()
        # Create the message bubble
        message_label = qtw.QLabel(text)
        message_label.setWordWrap(True)
        message_label.setStyleSheet("padding: 10px; margin: 5px; color: white;")
        message_label.setAlignment(qtc.Qt.AlignmentFlag.AlignVCenter)

        # Calculate content width with a maximum of 70% of the current window width
        text_width = message_label.fontMetrics().boundingRect(text).width()
        max_width = int(self.width() * 0.7)
        content_width = min(text_width + 20, max_width)
        message_label.setFixedWidth(content_width+20)
        message_label.setSizePolicy(qtw.QSizePolicy.Policy.Minimum, qtw.QSizePolicy.Policy.Preferred)

        if role == "user":
            # Style user messages
            message_label.setStyleSheet(f" background-color: {self.second_color}; {message_label.styleSheet()}")
            message_label.setAlignment(qtc.Qt.AlignmentFlag.AlignRight)
            message_layout.addStretch(1)  # Push to the right
            message_layout.addWidget(message_label)
        else:  # AI response
            # Style AI messages
            message_label.setStyleSheet(f"background-color: {self.third_color}; {message_label.styleSheet()}")
            message_layout.addWidget(message_label)
            message_layout.addStretch(1)  # Push to the left

        self.messages_layout.addLayout(message_layout)
        self.messages_widget.adjustSize()
        self.scroll_area.verticalScrollBar().setSliderPosition(self.scroll_area.verticalScrollBar().maximum())

    def get_ai_response(self, user_message):
        try:

            res, event = function_call(user_message, self._sanitized_history())
            return res, event
        except Exception as e:
            return f"Error: {e}", None


    def add_event_suggestion_widget(self, event_suggestion):
        """Display an event suggestion UI in the chat."""
        print(event_suggestion)
        suggestion_widget = qtw.QWidget()
        suggestion_layout = qtw.QVBoxLayout()
        title_label = qtw.QTextEdit(f"📅 Event: {event_suggestion['title']}")
        date_label_start = qtw.QDateEdit(qtc.QDate.fromString(event_suggestion['start_date'], "yyyy-MM-dd"), calendarPopup=True)
        date_label_end = qtw.QDateEdit(qtc.QDate.fromString(event_suggestion['end_date'], "yyyy-MM-dd"), calendarPopup=True)
        time_label_start = qtw.QTimeEdit(qtc.QTime.fromString(event_suggestion['start_time'], "HH:mm"))
        time_label_end = qtw.QTimeEdit(qtc.QTime.fromString(event_suggestion['end_time'], "HH:mm"))
        desc_label = qtw.QLabel(f"📝 {event_suggestion['description']}")

        add_button = qtw.QPushButton("✅ Add Event")
        cancel_button = qtw.QPushButton("❌ Cancel")

        add_button.setStyleSheet("background-color: green; color: white; padding: 5px; border-radius: 5px;")
        cancel_button.setStyleSheet("background-color: red; color: white; padding: 5px; border-radius: 5px;")

        add_button.clicked.connect(lambda: self.confirm_add_event(event_suggestion, suggestion_widget))
        cancel_button.clicked.connect(lambda: self.remove_event_suggestion(suggestion_widget))

        suggestion_layout.addWidget(title_label)
        suggestion_layout.addWidget(date_label_start)
        suggestion_layout.addWidget(date_label_end)
        suggestion_layout.addWidget(time_label_start)
        suggestion_layout.addWidget(time_label_end)
        suggestion_layout.addWidget(desc_label)
        suggestion_layout.addWidget(add_button)
        suggestion_layout.addWidget(cancel_button)
        suggestion_widget.setLayout(suggestion_layout)

        self.messages_layout.addWidget(suggestion_widget)
        self.scroll_area.verticalScrollBar().setValue(self.scroll_area.verticalScrollBar().maximum())

    def confirm_add_event(self, event_suggestion, suggestion_widget):
        """Add event to database."""
        self.db.add_event(
            user_id=1,  # Replace with actual user ID
            title=event_suggestion["title"],
            start_date=event_suggestion["start_date"],
            end_date=event_suggestion["end_date"],
            start_time=event_suggestion["start_time"],
            end_time=event_suggestion["end_time"],
            description=event_suggestion["description"]
        )
        self.add_message("✅ Event successfully added!", "ai")
        self.remove_event_suggestion(suggestion_widget)

    def remove_event_suggestion(self, widget):
        """Remove event suggestion widget."""
        widget.setParent(None)

    # def resizeEvent(self, event):
    #     """Override resize event to adjust message widths dynamically."""
    #     for i in range(self.messages_layout.count()):
    #         item = self.messages_layout.itemAt(i)
    #         if isinstance(item, qtw.QHBoxLayout):
    #             for j in range(item.count()):
    #                 widget = item.itemAt(j).widget()
    #                 if isinstance(widget, qtw.QLabel):
    #                     content_width = round(min(self.width() * 0.7, widget.fontMetrics().boundingRect(widget.text()).width() + 20))
    #                     widget.setFixedWidth(content_width)
    #     super().resizeEvent(event)  # Call parent resizeEvent
