import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
PROXY_URL = os.getenv("PROXY_URL")
MY_ID = int(os.getenv("MY_ID", 0))
MY_EMAIL = os.getenv("MY_EMAIL")
MY_CITY = os.getenv("MY_CITY", "Moscow")
MY_TIME_ZONE = os.getenv("MY_TIME_ZONE", "Europe/Moscow")
MY_REGION=os.getenv("MY_REGION")
RSS_SITE=os.getenv("RSS_SITE")
OWM_API_KEY = os.getenv("OWM_API_KEY")