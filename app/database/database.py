import aiosqlite
from loguru import logger

DB_PATH = 'data/remind.db'

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            chat_id INTEGER,
            task_text TEXT,
            remind_time TEXT,
            status TEXT)
        ''')
        await db.commit()
    logger.info("База данных инициализирована.")

async def add_reminder(chat_id: int, task_text: str, remind_time: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO reminders (chat_id, task_text, remind_time, status) VALUES (?, ?, ?, 'pending')",
            (chat_id, task_text, remind_time)
        )
        await db.commit()
        return cursor.lastrowid

async def delete_reminder(reminder_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
        await db.commit()

async def get_all_reminders():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id, chat_id, task_text, remind_time FROM reminders") as cursor:
            return await cursor.fetchall()

async def clear_all_reminders():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM reminders")
        await db.commit()
    logger.info("База данных полностью очищена.")