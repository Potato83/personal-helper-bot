import pytest
import aiosqlite
import app.database.database as database

original_connect = aiosqlite.connect

@pytest.fixture(autouse=True)
async def mock_db(monkeypatch, tmpdir):
    db_path = str(tmpdir.join("test_remind.db"))
    monkeypatch.setattr("app.database.database.DB_PATH", db_path)
    await database.init_db()
    return db_path

@pytest.mark.asyncio
async def test_add_and_get_reminder():
    chat_id = 12345
    task_text = "Тестовая задача"
    remind_time = "2026-04-28 15:00:00"
    
    reminder_id = await database.add_reminder(chat_id, task_text, remind_time)
    assert reminder_id == 1  
    
    reminders = await database.get_all_reminders()
    assert len(reminders) == 1
    
    saved_id, saved_chat_id, saved_text, saved_time = reminders[0]
    assert saved_chat_id == chat_id
    assert saved_text == task_text
    assert saved_time == remind_time

@pytest.mark.asyncio
async def test_delete_reminder():
    reminder_id = await database.add_reminder(111, "To be deleted", "2026-04-28 12:00:00")
    assert len(await database.get_all_reminders()) == 1
    
    await database.delete_reminder(reminder_id)
    assert len(await database.get_all_reminders()) == 0