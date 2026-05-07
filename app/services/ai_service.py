import json
import httpx
from datetime import datetime
from datetime import timedelta
from openai import AsyncOpenAI
from loguru import logger
import app.core.config as config



if config.PROXY_URL:
    http_client = httpx.AsyncClient(
        proxy=config.PROXY_URL,
        verify=False  # nosec B501
    )
else:
    http_client = httpx.AsyncClient()

client = AsyncOpenAI(
    api_key=config.AI_API_KEY, 
    base_url=config.AI_BASE_URL,
    http_client=http_client
)

async def process_user_intent(text: str) -> dict:
    if not config.AI_API_KEY:
        return {"action": "error", "text": "AI ключ не настроен"}

    now = datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M")
    
    # Генерируем таблицу-подсказку на 7 дней вперед
    days_map = {
        0: "понедельник", 1: "вторник", 2: "среда", 3: "четверг", 
        4: "пятница", 5: "суббота", 6: "воскресенье"
    }
    
    calendar_context = ""
    for i in range(8):
        d = now + timedelta(days=i)
        day_name = days_map[d.weekday()]
        prefix = "СЕГОДНЯ" if i == 0 else ("ЗАВТРА" if i == 1 else day_name)
        calendar_context += f"{prefix}: {d.strftime('%Y-%m-%d')}\n"

    system_prompt = f"""
    Ты — строгий анализатор намерений. Ты не ведешь диалог, ты только выдаешь JSON.
    
    ТЕКУЩАЯ ДАТА: {now_str}
    
    СПРАВОЧНИК ДАТ (используй его, чтобы не ошибиться!):
    {calendar_context}
    
    "action" может быть:
    - "remind": напоминание/таймер (через X минут, напомни в 15:00)
    - "calendar": СОЗДАТЬ/ЗАПИСАТЬ новое событие (добавь встречу, запиши игру)
    - "schedule": ПОСМОТРЕТЬ существующее расписание (что у меня на..., какие планы)
    - "weather": узнать погоду
    - "chat": просто общение

    ПРАВИЛА:
    1. Поле "time" ВСЕГДА должно быть "YYYY-MM-DD HH:MM". 
    2. Если просят "на четверг" — посмотри в СПРАВОЧНИКЕ выше дату для четверга.
    3. Если время в часах не указано, ставь 00:00.
    4. "text": только суть (купить хлеб, матан, игры). Для chat — твой ответ.

    ПРИМЕР:
    Запрос: "расписание на четверг"
    Ответ: {{"action": "schedule", "text": "", "time": "2026-05-07 00:00"}}
    """

    try:
        response = await client.chat.completions.create(
            model="llama-3.1-8b-instant", 
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        logger.debug(f"AI Response: {content}")
        return json.loads(content)
    except Exception as e:
        logger.exception("Ошибка AI")
        return {"action": "error", "text": f"Ошибка: {str(e)}"}