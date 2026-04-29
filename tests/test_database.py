import pytest
import sqlite3
import app.database.database as database

# 1. Запоминаем оригинальную функцию из стандартной библиотеки ДО подмены
original_connect = sqlite3.connect

@pytest.fixture(autouse=True)
def mock_db(monkeypatch, tmpdir):
    # Приводим путь временного файла к строке
    db_path = str(tmpdir.join("test_remind.db"))
    
    # 2. Подменяем функцию.
    monkeypatch.setattr("database.sqlite3.connect", lambda *args, **kwargs: original_connect(db_path))
    
    # Инициализируем пустую структуру таблиц
    database.init_db()
    
    return db_path

def test_add_and_get_reminder():
    chat_id = 12345
    task_text = "Тестовая задача"
    remind_time = "2026-04-28 15:00:00"
    
    reminder_id = database.add_reminder(chat_id, task_text, remind_time)
    
    assert reminder_id == 1  # При чистой БД ID должен быть 1
    
    reminders = database.get_all_reminders()
    assert len(reminders) == 1
    
    saved_id, saved_chat_id, saved_text, saved_time = reminders[0]
    assert saved_chat_id == chat_id
    assert saved_text == task_text
    assert saved_time == remind_time

def test_delete_reminder():
    # Добавляем
    reminder_id = database.add_reminder(111, "To be deleted", "2026-04-28 12:00:00")
    
    # Проверяем, что добавилось
    assert len(database.get_all_reminders()) == 1
    
    # Удаляем
    database.delete_reminder(reminder_id)
    
    # Проверяем, что удалилось
    assert len(database.get_all_reminders()) == 0