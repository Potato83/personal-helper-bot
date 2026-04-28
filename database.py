import sqlite3

def init_db():
    conn = sqlite3.connect('data/remind.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reminders (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        chat_id INTEGER,
        task_text TEXT,
        remind_time TEXT,
        status TEXT)
    ''')
    conn.commit()
    conn.close()

def add_reminder(chat_id: int, task_text: str, remind_time: str) -> int:
    conn = sqlite3.connect('data/remind.db')
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO reminders (chat_id, task_text, remind_time, status) VALUES (?, ?, ?, 'pending')",
        (chat_id, task_text, remind_time)
    )
    conn.commit()
    reminder_id = cursor.lastrowid
    conn.close()
    return reminder_id

def delete_reminder(reminder_id: int):
    conn = sqlite3.connect('data/remind.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
    conn.commit()
    conn.close()

def get_all_reminders():
    conn = sqlite3.connect('data/remind.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, chat_id, task_text, remind_time FROM reminders")
    rows = cursor.fetchall()
    conn.close()
    return rows