import sqlite3
import json

class CalendarDB:
    def __init__(self):
        self.create_tables()


    @staticmethod
    def create_tables():
        conn = sqlite3.connect('calendai.db')
        cur = conn.cursor()

        # Create the tables


        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            start_time TEXT,
            end_time TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            user_id INTEGER,  -- nullable if system/assistant messages
            sender TEXT NOT NULL CHECK(sender IN ('user','assistant','system')),
            message TEXT NOT NULL,
            metadata TEXT, -- JSON
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """)

        conn.commit()
        conn.close()

    def add_user(self, username, password, email):
        conn = sqlite3.connect('calendai.db')
        cur = conn.cursor()

        cur.execute("INSERT INTO users (username, password, email) VALUES (?, ?, ?)", (username, password, email))

        conn.commit()
        conn.close()
    
    def get_user(self, username):
        conn = sqlite3.connect('calendai.db')
        cur = conn.cursor()

        cur.execute("SELECT * FROM users WHERE username=?", (username,))
        user = cur.fetchone()

        conn.close()
        return user
    
    def add_event(self, user_id, title, description, start_date, end_date, start_time, end_time):
        conn = sqlite3.connect('calendai.db')
        cur = conn.cursor()

        cur.execute("INSERT INTO events (user_id, title, description, start_date, end_date, start_time, end_time) VALUES (?, ?, ?, ?, ?, ?, ?)", (user_id, title, description, start_date, end_date, start_time, end_time))

        conn.commit()
        conn.close()

    def get_events(self, user_id):
        conn = sqlite3.connect('calendai.db')
        cur = conn.cursor()

        cur.execute("SELECT * FROM events WHERE user_id=?", (user_id,))
        events = cur.fetchall()

        conn.close()
        return events
    
    def update_event(self, event_id, title, description, start_date, end_date, start_time, end_time):
        conn = sqlite3.connect('calendai.db')
        cur = conn.cursor()

        cur.execute("UPDATE events SET title=?, description=?, start_date=?, end_date=?, start_time=?, end_time=? WHERE id=?", (title, description, start_date, end_date, start_time, end_time, event_id))

        conn.commit()
        conn.close()
    
    def delete_event(self, event_id):
        conn = sqlite3.connect('calendai.db')
        cur = conn.cursor()

        cur.execute("DELETE FROM events WHERE id=?", (event_id,))

        conn.commit()
        conn.close()
    
    def delete_user(self, user_id):
        conn = sqlite3.connect('calendai.db')
        cur = conn.cursor()

        cur.execute("DELETE FROM users WHERE id=?", (user_id,))

        conn.commit()
        conn.close()
    
    def get_user_events(self, username):
        conn = sqlite3.connect('calendai.db')
        cur = conn.cursor()

        cur.execute("SELECT events.* FROM events JOIN users ON events.user_id=users.id WHERE users.username=?", (username,))
        events = cur.fetchall()

        conn.close()
        return events
    
    def save_message(self, conversation_id, sender, message, user_id=None, metadata=None):
        conn = sqlite3.connect('calendai.db')
        cur = conn.cursor()
        msg_text = self._normalize_message_for_storage(message)
        meta_text = json.dumps(metadata) if isinstance(metadata, dict) else None

        cur.execute("INSERT INTO messages (conversation_id, user_id, sender, message, metadata) VALUES (?, ?, ?, ?, ?)", (conversation_id, user_id, sender ,msg_text, meta_text))

    @staticmethod
    def _normalize_message_for_storage(message):
        # Accept None, dicts, objects, etc., return a safe string
        if message is None:
            return "[no text content]"
        if isinstance(message, str):
            text = message.strip()
            return text if text else "[empty message]"
        try:
            # Handle ChatCompletionMessage-like objects
            content = getattr(message, "content", None)
            if content:
                return str(content)
            # Fallback to JSON if possible
            return json.dumps(message, default=str)[:4000]  # avoid huge blobs
        except Exception:
            return str(message)

    def get_messages(self, conversation_id):
        conn = sqlite3.connect('calendai.db')
        
        # Enable named access to columns
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # Execute the query
        cur.execute("SELECT * FROM messages WHERE conversation_id=?", (conversation_id,))
        rows = cur.fetchall()

        # Convert rows to a list of dictionaries
        messages = [dict(row) for row in rows]
        formatted_messages = [{"role": message["sender"], "content": message["message"]} for message in messages]

        conn.close()
        return formatted_messages
    
    def get_user_messages(self, username):
        conn = sqlite3.connect('calendai.db')
        cur = conn.cursor()

        cur.execute("SELECT messages.* FROM messages JOIN users ON messages.user_id=users.id WHERE users.username=?", (username,))
        messages = cur.fetchall()

        conn.close()
        return messages

    def check_user(self, username, password):
        conn = sqlite3.connect('calendai.db')
        cur = conn.cursor()

        cur.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = cur.fetchone()

        conn.close()
        return user is not None
