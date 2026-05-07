import pytest
import json
from unittest.mock import patch, AsyncMock
from app.services import ai_service

# Подменяем реальный запрос к Groq на "заглушку" (Mock)
@pytest.fixture
def mock_groq():
    with patch("app.services.ai_service.client.chat.completions.create", new_callable=AsyncMock) as mock:
        yield mock

@pytest.mark.asyncio
async def test_ai_remind_intent(mock_groq):
    # 1. Настраиваем фейковый ответ от ИИ
    fake_response_content = '{"action": "remind", "text": "купить хлеб", "time": "2026-05-10 18:00"}'
    
    mock_message = AsyncMock()
    mock_message.content = fake_response_content
    mock_response = AsyncMock()
    mock_response.choices = [AsyncMock(message=mock_message)]
    mock_groq.return_value = mock_response

    # 2. Вызываем нашу функцию
    result = await ai_service.process_user_intent("напомни купить хлеб завтра в 18:00")
    
    # 3. Проверяем результат
    assert result["action"] == "remind"
    assert result["text"] == "купить хлеб"
    assert result["time"] == "2026-05-10 18:00"
    mock_groq.assert_called_once() # Проверяем, что ИИ действительно был вызван

@pytest.mark.asyncio
async def test_ai_schedule_intent(mock_groq):
    fake_response_content = '{"action": "schedule", "text": "", "time": "2026-05-07 00:00"}'
    
    mock_message = AsyncMock()
    mock_message.content = fake_response_content
    mock_response = AsyncMock()
    mock_response.choices = [AsyncMock(message=mock_message)]
    mock_groq.return_value = mock_response

    result = await ai_service.process_user_intent("что запланировано на 7 мая?")
    
    assert result["action"] == "schedule"
    assert result["text"] == ""
    assert result["time"] == "2026-05-07 00:00"

@pytest.mark.asyncio
async def test_ai_no_key():
    # Тест: что будет, если ключ ИИ не задан
    with patch("app.core.config.AI_API_KEY", None):
        result = await ai_service.process_user_intent("привет")
        assert result["action"] == "error"
        assert "не настроен" in result["text"]