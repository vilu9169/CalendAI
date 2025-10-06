import sqlite3

conn = sqlite3.connect("calendai.db")
cur = conn.cursor()
cur.execute("DELETE FROM messages")  # or add WHERE conversation_id = 1
conn.commit()
conn.close()