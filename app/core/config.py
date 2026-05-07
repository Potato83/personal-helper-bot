import os
from dotenv import load_dotenv

load_dotenv()

def _get_env_or_raise(key: str, default=None) -> str:
    val = os.getenv(key, default)
    if val is None:
        raise ValueError(f"Критическая ошибка: переменная окружения {key} не задана!")
    return val

BOT_TOKEN = _get_env_or_raise("BOT_TOKEN")
PROXY_URL = os.getenv("PROXY_URL")  # Прокси может быть пустым
MY_ID = int(_get_env_or_raise("MY_ID", "0"))
MY_EMAIL = _get_env_or_raise("MY_EMAIL")
MY_CITY = _get_env_or_raise("MY_CITY", "Moscow")
MY_TIME_ZONE = _get_env_or_raise("MY_TIME_ZONE", "Europe/Moscow")
MY_REGION = _get_env_or_raise("MY_REGION")
RSS_SITE = _get_env_or_raise("RSS_SITE")
OWM_API_KEY = _get_env_or_raise("OWM_API_KEY")
AI_API_KEY = os.getenv("AI_API_KEY")
AI_BASE_URL = os.getenv("AI_BASE_URL", "https://api.openai.com/v1")