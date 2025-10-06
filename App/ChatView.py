import PyQt6.QtCore as qtc
import PyQt6.QtWidgets as qtw
from ai_call import function_call # Assuming you have a module `ai_call` for API integration
from DB.sqlite import CalendarDB
from datetime import date, timedelta, datetime


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
        Build a safe history for the model:
        - drop None/empty content
        - EXCLUDE user messages that are already handled
        """
        safe = []
        for m in self.messages:
            # skip handled user messages
            if m.get("role") == "user" and m.get("handled", 0) == 1:
                continue
            text = self._to_safe_text(m.get("content"))
            if text == "[no text content]":
                continue
            safe.append({"role": m.get("role", "user"), "content": text})
        return safe



    def _recent_events_for_prompt(self, days_ahead=30, limit=10) -> list[dict]:
        """
        Returns a short list of upcoming events, shaped for the prompt.
        Keys: title, start_date, start_time, location (optional).
        """
        # Get events from DB
        try:
            if self.user_id is not None and hasattr(self.db, "get_events"):
                rows = self.db.get_events(self.user_id)  # may be tuples
                cols = ["id","user_id","title","description","start_date","end_date","start_time","end_time"]
                if rows and not isinstance(rows[0], dict):
                    rows = [dict(zip(cols, r)) for r in rows]
            elif hasattr(self.db, "get_all_events"):
                rows = self.db.get_all_events()
            else:
                rows = []
        except Exception as e:
            print("recent events load failed:", e)
            rows = []

        # Filter to next N days and shape
        today = date.today()
        until = today + timedelta(days=days_ahead)

        def parse(d):
            try:
                return datetime.strptime(d, "%Y-%m-%d").date()
            except Exception:
                return None

        upcoming = []
        for r in rows:
            sd = parse((r.get("start_date") or "").strip())
            if not sd:
                continue
            if today <= sd <= until:
                upcoming.append({
                    "title": (r.get("title") or "").strip() or "(Untitled)",
                    "start_date": sd.isoformat(),
                    "start_time": (r.get("start_time") or "").strip(),
                    # include if your schema has it; otherwise it will be blank
                    "location": (r.get("location") or "").strip()
                })

        # sort and cap
        upcoming.sort(key=lambda e: (e["start_date"], e.get("start_time","") or "00:00"))
        return upcoming[:limit]

    def __init__(self, palette, userid=None):
        super().__init__()
        # Set up layout
        self.user_id = userid
        self.db = CalendarDB()
        self.messages = self.db.get_messages_for_chat(conversation_id=1)
        self.second_color = palette[1]
        self.third_color = palette[2]
        self.fourth_color = palette[3]
        print(self.messages)

        self.pending_event = None
        self.pending_ui_open = False  # optional but nice to have


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
        msg_id = self.db.save_message(conversation_id=1, sender="user", message=text)
        self.messages[-1]["id"] = msg_id
        self.messages[-1]["handled"] = 0
        print("mes: ", self.messages)


        ai_response, event = self.get_ai_response(text)

        ai_text = self._to_safe_text(ai_response)


        self.add_message(ai_text, "ai")
        aid = self.db.save_message(conversation_id=1, sender="assistant", message=ai_text)
        self.messages.append({"role": "assistant", "content": ai_text, "id": aid})

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
            recent = self._recent_events_for_prompt(days_ahead=30, limit=10)
            res, event = function_call(user_message, self._sanitized_history(), recent_events=recent, has_pending=self.pending_ui_open)

            # ⬇️ NEW: if the model produced a tool call, mark the prompting user msg handled now
            if event:
                try:
                    handled_id = self.db.mark_last_unhandled_user_message_handled(conversation_id=1)
                except Exception:
                    handled_id = None

                # reflect in memory so _sanitized_history drops it immediately
                if handled_id:
                    for m in reversed(self.messages):
                        if m.get("id") == handled_id:
                            m["handled"] = 1
                            break
                else:
                    # fallback: mark latest unhandled user msg
                    for m in reversed(self.messages):
                        if m.get("role") == "user" and m.get("handled", 0) != 1:
                            m["handled"] = 1
                            break

                # Keep a pending event reference for the UI confirm button
                self.pending_event = event

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

        self.pending_event = event_suggestion
        self.pending_ui_open = True

        self.scroll_area.verticalScrollBar().setValue(self.scroll_area.verticalScrollBar().maximum())

    def confirm_add_event(self, event_suggestion, suggestion_widget):
        user_id = self.user_id  # your real user id

        # Skip if exists (nice UX message)
        if hasattr(self.db, "event_exists") and self.db.event_exists(
            user_id=user_id,
            title=event_suggestion["title"],
            start_date=event_suggestion["start_date"],
            end_date=event_suggestion["end_date"],
            start_time=event_suggestion.get("start_time"),
            end_time=event_suggestion.get("end_time"),
        ):
            self.add_message("ℹ️ That event already exists — skipped.", "ai")
            self.remove_event_suggestion(suggestion_widget)
            return

        # Idempotent insert (will update description if same signature)
        self.db.add_event(
            user_id=user_id,
            title=event_suggestion["title"],
            description=event_suggestion.get("description"),
            start_date=event_suggestion["start_date"],
            end_date=event_suggestion["end_date"],
            start_time=event_suggestion.get("start_time"),
            end_time=event_suggestion.get("end_time"),
        )
        

        handled_id = self.db.mark_last_unhandled_user_message_handled(conversation_id=1)

        # Make history consistent in memory
        for m in reversed(self.messages):
            if m.get("role") == "user" and m.get("handled", 0) != 1:
                m["handled"] = 1
                if handled_id and "id" in m and m["id"] == handled_id:
                    # (optional) you matched the exact row
                    pass
                break
        self.pending_event = None
        self.pending_ui_open = False
        self.add_message("✅ Event successfully added!", "ai")
        self.remove_event_suggestion(suggestion_widget)

    # if you have CalendarView/TaskView instances, refresh them here
    # self.calendar_view.refresh_from_db()
    # self.task_view.refresh_from_db()
    def remove_event_suggestion(self, widget):
        """Remove event suggestion widget."""
        widget.setParent(None)
        self.pending_event = None
        self.pending_ui_open = False
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
