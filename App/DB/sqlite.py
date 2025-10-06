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
            handled INTEGER NOT NULL DEFAULT 0,
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
    def get_user_id(self, username):
        conn = sqlite3.connect('calendai.db')
        cur = conn.cursor()

        cur.execute("SELECT id FROM users WHERE username=?", (username,))
        user = cur.fetchone()

        conn.close()
        return user[0] if user else None
    
    def add_event(self, user_id, title, description, start_date, end_date, start_time, end_time):
        import sqlite3
        conn = sqlite3.connect('calendai.db', timeout=10, isolation_level=None)
        try:
            cur = conn.cursor()
            cur.execute("""
            INSERT INTO events (user_id, title, description, start_date, end_date, start_time, end_time)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, title, start_date, start_time, end_date, end_time)
            DO UPDATE SET description = excluded.description
            """, (user_id, title.strip(), description or "", start_date, end_date, start_time or "", end_time or ""))
        finally:
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
        conn = sqlite3.connect('calendai.db', timeout=10, isolation_level=None)
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA foreign_keys=ON;")
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO messages (conversation_id, user_id, sender, message, metadata)
                VALUES (?, ?, ?, ?, ?)
            """, (conversation_id, user_id, sender, message, json.dumps(metadata) if metadata is not None else None))
            message_id = cur.lastrowid
            conn.commit()
            return message_id
        finally:
            conn.close()
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

    def get_messages_for_chat(self, conversation_id: int):
        """
        Return messages with id + handled so ChatView can filter for tool calls.
        Shape: [{'id': int, 'role': 'user'|'assistant'|'system', 'content': str, 'handled': int, 'timestamp': str}]
        """
        conn = sqlite3.connect("calendai.db")
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT id, sender AS role, message AS content, handled, timestamp
            FROM messages
            WHERE conversation_id=?
            ORDER BY id ASC
        """, (conversation_id,))
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    def mark_message_handled(self, message_id: int):
        conn = sqlite3.connect("calendai.db", timeout=10, isolation_level=None)
        try:
            conn.execute("UPDATE messages SET handled=1 WHERE id=?", (message_id,))
        finally:
            conn.close()

    def mark_last_unhandled_user_message_handled(self, conversation_id: int):
        """
        Mark the most recent *user* message in this conversation as handled.
        Useful when you just created an event based on the latest instruction.
        """
        conn = sqlite3.connect("calendai.db", timeout=10, isolation_level=None)
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT id FROM messages
                WHERE conversation_id=? AND sender='user' AND handled=0
                ORDER BY id DESC LIMIT 1
            """, (conversation_id,))
            row = cur.fetchone()
            if row:
                cur.execute("UPDATE messages SET handled=1 WHERE id=?", (row[0],))
                return row[0]
            return None
        finally:
            conn.close()