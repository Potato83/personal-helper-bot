import re
from bs4 import BeautifulSoup
from defusedxml import ElementTree as ET
from loguru import logger
import app.core.config as config
from app.core.http_client import get_session

async def get_exchange_rates():
    try:
        async with get_session().get('https://www.cbr-xml-daily.ru/daily_json.js') as response:
            data = await response.json(content_type=None)
            usd = data['Valute']['USD']['Value']
            eur = data['Valute']['EUR']['Value']
            return f"💵 USD: {usd:.2f} ₽ | 💶 EUR: {eur:.2f} ₽"
    except Exception:
        logger.exception("Ошибка получения курсов валют")
        return "💱 Курсы валют сейчас недоступны."

async def get_news():
    try:
        async with get_session().get(config.RSS_SITE) as response:
            xml_data = await response.text()
            root = ET.fromstring(xml_data)
            items = root.findall('.//item')[:3]
            news_text = "📰 <b>Главные новости:</b>\n"
            for item in items:
                title = item.find('title').text
                link = item.find('link').text
                news_text += f"🔹 <a href='{link}'>{title}</a>\n"
            return news_text
    except Exception:
        logger.exception("Ошибка получения новостей")
        return "📰 Новости сейчас недоступны."

async def get_weather(city=config.MY_CITY):
    if not config.OWM_API_KEY:
        return "☁️ Ошибка: API ключ для погоды не настроен."
    try:
        url = "https://api.openweathermap.org/data/2.5/forecast"
        params = {
            "q": city,
            "appid": config.OWM_API_KEY,
            "units": "metric",
            "lang": "ru"
        }
        async with get_session().get(url, params=params) as response:
            if response.status != 200:
                error_data = await response.text()
                logger.error(f"OWM Error: {error_data}")
                return f"☁️ Ошибка API погоды. Код ответа: {response.status}"
            
            data = await response.json()
            forecasts = data.get('list',[])
            
            result_text = f"🌤 Погода ({city}) на ближайшее время:\n"
            for item in forecasts[:3]:
                time_str = item['dt_txt'][11:16]
                temp = round(item['main']['temp'])
                desc = item['weather'][0]['description'].capitalize()
                result_text += f"🔹 {time_str} | {temp}°C | {desc}\n"
                
            return result_text
    except Exception:
        logger.exception("Внутренняя ошибка парсинга погоды")
        return "☁️ Внутренняя ошибка парсинга погоды."

async def get_outages(region=config.MY_REGION):
    url = f"https://detector404.ru/{region}"
    try:
        async with get_session().get(url) as response:
            if response.status != 200:
                return f"❌ Ошибка доступа к детектору сбоев (Код: {response.status})"
            html = await response.text()
            soup = BeautifulSoup(html, "lxml")
            all_text = soup.get_text(separator=' ', strip=True)
            status_match = re.search(r'(Жалоб\s*[-–—]\s*[А-Яа-я]+|Сбои\s*[-–—]\s*[А-Яа-я]+|Нет сбоев)', all_text, re.IGNORECASE)
            status_text = status_match.group(1).capitalize() if status_match else "Статус неизвестен"
            
            is_bad = any(word in status_text.lower() for word in ['сбой', 'много', 'высокий'])
            if is_bad:
                return f"⚠️ <b>ВНИМАНИЕ! Проблемы с интернетом в регионе!</b>\n📊 Статус: {status_text}"
            return f"✅ Сеть стабильна.\n📊 Статус: {status_text}"
    except Exception:
        logger.exception("Ошибка парсинга Downdetector")
        return "❌ Ошибка парсинга детектора сбоев."