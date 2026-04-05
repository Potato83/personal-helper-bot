import re
import aiohttp
import dateparser
from datetime import datetime, timedelta
from aiogram import Router, types, Bot, F
from aiogram.filters import Command
from bs4 import BeautifulSoup
import aiohttp
import sqlite3
import re
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import xml.etree.ElementTree as ET
from aiohttp_socks import ProxyConnector 

import config
import database
import google_cal

router = Router()

LAST_NETWORK_STATUS = "OK"

# keys for better view
main_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="🌦 Погода"), KeyboardButton(text="🗓 Расписание")],
              [KeyboardButton(text="🌐 Статус сети"), KeyboardButton(text="🧹 Очистить БД")],
              [KeyboardButton(text="🌅 Утренняя сводка")]
    ],
    resize_keyboard=True
)

# --- helpers --- 
async def get_exchange_rates():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('https://www.cbr-xml-daily.ru/daily_json.js') as response:
                data = await response.json()
                usd = data['Valute']['USD']['Value']
                eur = data['Valute']['EUR']['Value']
                
                return f"💵 USD: {usd:.2f} ₽ | 💶 EUR: {eur:.2f} ₽"
    except Exception as e:
        return "💱 Курсы валют сейчас недоступны. Ошибка: {e}"

async def get_news():
    try:
        connector = ProxyConnector.from_url(config.PROXY_URL) if config.PROXY_URL else None
        
        async with aiohttp.ClientSession(connector=connector) as session:
            # Requesting an RSS feed 
            async with session.get(config.RSS_SITE) as response:
                xml_data = await response.text()
                root = ET.fromstring(xml_data)
                items = root.findall('.//item')[:3]
                news_text = "📰 **Главные новости:**\n"
                
                for item in items:
                    title = item.find('title').text
                    link = item.find('link').text
                    news_text += f"🔹 <a href='{link}'>{title}</a>\n"
                    
                return news_text
    except Exception as e:
        return "📰 Новости сейчас недоступны. Ошибка: {e}"

async def get_hourly_weather(city=config.MY_CITY):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'https://wttr.in/{city}?format=j1&lang=ru') as response:
                # If the weather site is down, we return a simple string
                if response.status != 200:
                    return "☁️ Сервис погоды сейчас недоступен."
                
                data = await response.json()
                hourly_forecasts = data['weather'][0]['hourly']
                
                current_hour = datetime.now().hour
                result_text = "🌤 Погода на ближайшее время:\n"
                added_count = 0 
                
                for hour_data in hourly_forecasts:
                    time_val = int(hour_data['time']) // 100 
                    if time_val < current_hour - 2:
                        continue
                        
                    time_str = "00:00" if hour_data['time'] == "0" else f"{hour_data['time'][:-2]}:00"
                    temp = hour_data['tempC']
                    desc = hour_data['lang_ru'][0]['value']
                    
                    result_text += f"🔹 {time_str} | {temp}°C | {desc}\n"
                    added_count += 1
                    if added_count >= 3:
                        break 
                        
                return result_text
    except Exception as e:
        # If any error occurred at all (the site did not return JSON, etc.)
        return "☁️ Не удалось загрузить прогноз погоды."

async def get_short_weather(city=config.MY_CITY):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'https://wttr.in/{city}?format=j1&lang=ru') as response:
                data = await response.json()
                
                hourly_forecasts = data['weather'][0]['hourly']
                
                current_hour = datetime.now().hour
                
                result_text = "🌤 Погода на ближайшее время:\n"
                added_count = 0 
                
                for hour_data in hourly_forecasts:
                    # wttr.in returns time in the format "0", "300", "1200" (this is 00:00, 03:00, 12:00)
                    time_val = int(hour_data['time']) // 100 
                    
                    # If the forecast is for a time that HAS ALREADY PASSED, skip (continue)
                    # Take it with a small margin (-2 hours) to capture the current block
                    if time_val < current_hour - 2:
                        continue
                        
                    time_str = "00:00" if hour_data['time'] == "0" else f"{hour_data['time'][:-2]}:00"
                    temp = hour_data['tempC']
                    desc = hour_data['lang_ru'][0]['value']
                    
                    result_text += f"🔹 {time_str} | {temp}°C | {desc}\n"
                    added_count += 1
                    
                    # We only need 3 closest forecasts (approximately 9 hours)
                    if added_count >= 3:
                        break 
                        
                return result_text
    except Exception as e:
        return "☁️ Не удалось загрузить прогноз погоды."

async def get_today_schedule(text='сегодня'):
    if not text: text = 'сегодня'
    target_date = dateparser.parse(text, settings={f'TIMEZONE': config.MY_TIME_ZONE, 'PREFER_DATES_FROM': 'future'})
    
    start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = target_date.replace(hour=23, minute=59, second=59, microsecond=0)
    
    events = google_cal.get_events(start_of_day.isoformat() + "+03:00", end_of_day.isoformat() + "+03:00")
    
    if not events:
        return "На этот день ничего не запланировано! Можно отдыхать 🛋"

    reply_text = f"🗓 Расписание на {target_date.strftime('%d.%m.%Y')}:\n\n"
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        time_formatted = start[11:16] if 'T' in start else "Весь день"
        summary = event.get('summary', 'Без названия')
        reply_text += f"{time_formatted} - {summary}\n"
    return reply_text

async def send_reminder(bot: Bot, chat_id: int, task_text: str, reminder_id: int):
    await bot.send_message(chat_id, f"🔔 НАПОМИНАНИЕ: {task_text}") 
    database.delete_reminder(reminder_id)

async def morning_briefing(bot: Bot):
    # get data
    weather = await get_hourly_weather(config.MY_CITY)
    schedule_text = await get_today_schedule("сегодня")
    rates = await get_exchange_rates()
    news = await get_news()
    outages = await get_outages(config.MY_REGION)
    
    # text
    text = (
        f"🌅 <b>Доброе утро! Вот сводка на сегодня:</b>\n\n"
        f"{rates}\n\n"
        f"{weather}\n\n"
        f"{outages}\n\n"
        f"{schedule_text}\n\n"
        f"{news}"
    )
    
    # send
    await bot.send_message(chat_id=config.MY_ID, text=text, parse_mode="HTML", disable_web_page_preview=True)

# --- downdetector parse ---
async def get_outages(region=config.MY_REGION):
    url = f"https://detector404.ru/{region}"
    
    # user agent
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    
    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url) as response:
                if response.status != 200:
                    # УБРАЛИ error_snippet, чтобы не тянуть HTML-мусор в Телеграм!
                    return f"❌ Ошибка доступа к детектору сбоев (Код: {response.status})"
                    
                    return f"❌ Ошибка доступа!\nКод: {response.status}\nОтвет сайта: {error_snippet}"
                
                html = await response.text()
                
                soup = BeautifulSoup(html, "lxml")
                
                all_text = soup.get_text(separator=' ', strip=True)
                
                status_match = re.search(r'(Жалоб\s*[-–—]\s*[А-Яа-я]+|Сбои\s*[-–—]\s*[А-Яа-я]+|Нет сбоев)', all_text, re.IGNORECASE)
                status_text = status_match.group(1).capitalize() if status_match else "Статус неизвестен"
                
                hour_match = re.search(r'час\s*[:\-]?\s*(\d+[kKкК]?)', all_text, re.IGNORECASE)
                hour_count = hour_match.group(1) if hour_match else "0"
                
                is_bad = any(word in status_text.lower() for word in['сбой', 'много', 'высокий']) or (hour_count.isdigit() and int(hour_count) > 100)
                
                if is_bad:
                    return f"⚠️ **ВНИМАНИЕ! Проблемы с интернетом в регионе!**\n📊 Статус: {status_text}\n📈 Жалоб за час: {hour_count}"
                else:
                    return f"✅ Сеть стабильна.\n📊 Статус: {status_text}\n📈 Жалоб за час: {hour_count}"
                    
    except Exception as e:
        return f"❌ Ошибка парсинга: {e}"

# --- network check ---
async def monitor_network(bot: Bot):
    global LAST_NETWORK_STATUS
    
    outages = await get_outages(config.MY_REGION)
    
    is_down = "⚠️" in outages
    
    # OK -> DOWN
    if is_down and LAST_NETWORK_STATUS == "OK":
        await bot.send_message(config.MY_ID, f"🚨 АЛАРМ! Зафиксированы сбои:\n\n{outages}")
        LAST_NETWORK_STATUS = "DOWN" 
        
    # DOWN -> OK
    elif not is_down and LAST_NETWORK_STATUS == "DOWN":
        await bot.send_message(config.MY_ID, "✅ Ура! Сбои прекратились, интернет и сервисы работают нормально.")
        LAST_NETWORK_STATUS = "OK"
        
    # If OK -> OK or DOWN -> DOWN = nothing :3

# --- handlers ---
@router.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Бот-помощник запущен! Выбирай действие в меню ниже 👇\n\n"
        "(оставшиеся команды:\n/r - напомнить\n/c - в календарь\n/s - расписание)",
        reply_markup=main_kb # add buttons
    )


@router.message(Command("r"))
async def cmd_remind(message: types.Message, bot: Bot, scheduler):  
    
    if "-" not in message.text:
        await message.answer("Используй дефис! Пример: /r через 5 минут - текст")
        return

    text = message.text.replace("/r","").split("-")
    time_str = text[0].strip()
    task_text = text[1].strip()    
    
    time_str = re.sub(r"в (\d{1,2})$", r"в \1:00", time_str)
    if re.match(r"^\d+\s+(минут|час|день|дней|часа|минуты)", time_str):
        time_str = f"через {time_str}"

    time = dateparser.parse(
        time_str, 
        settings={f'TIMEZONE': config.MY_TIME_ZONE, 'PREFER_DATES_FROM': 'future', 'RETURN_AS_TIMEZONE_AWARE': True}
    )
    
    if not time:
        await message.answer(f'Не понял время "{time_str}"! Попробуй иначе.')
        return

    reminder_id = database.add_reminder(message.chat.id, task_text, str(time))
    
    scheduler.add_job(
        send_reminder,               
        trigger='date',              
        run_date=time,               
        kwargs={'bot': bot, 'chat_id': message.chat.id, 'task_text': task_text, 'reminder_id': reminder_id}
    )
    nice_time = time.strftime("%d.%m в %H:%M")
    await message.answer(f"Понял! Напомню {nice_time}.")

@router.message(Command("c"))
async def cmd_calendar(message: types.Message):
    
    if "-" not in message.text:
        await message.answer("Используй дефис! Пример: /c время - ивент - описание")
        return
    
    text = message.text.replace("/c","").split("-", 2)
    time_str = text[0].strip()
    task_text = text[1].strip()
    task_description = text[2].strip() if len(text) > 2 else ""
    
    time_str = re.sub(r"в (\d{1,2})$", r"в \1:00", time_str)
    
    if " до " in time_str:
        start_str, end_str = time_str.split(" до ")
        start_time = dateparser.parse(start_str, settings={'TIMEZONE': config.MY_TIME_ZONE  , 'PREFER_DATES_FROM': 'future'})
        end_time_raw = dateparser.parse(end_str, settings={'TIMEZONE': config.MY_TIME_ZONE, 'PREFER_DATES_FROM': 'future'})
        end_time = end_time_raw.replace(year=start_time.year, month=start_time.month, day=start_time.day)
    elif " на " in time_str:
        start_str, duration_str = time_str.split(" на ")
        start_time = dateparser.parse(start_str, settings={'TIMEZONE': config.MY_TIME_ZONE, 'PREFER_DATES_FROM': 'future'})
        hours = int(''.join(filter(str.isdigit, duration_str))) 
        end_time = start_time + timedelta(hours=hours)
    else:
        start_time = dateparser.parse(time_str, settings={'TIMEZONE': config.MY_TIME_ZONE, 'PREFER_DATES_FROM': 'future'})
        end_time = start_time + timedelta(hours=1)
        
    if not start_time:
        await message.answer("Не понял время!")
        return
    
    event_body = {
        'summary': task_text,
        'description': task_description,
        'start': {'dateTime': start_time.isoformat(), 'timeZone': 'Europe/Moscow'},
        'end': {'dateTime': end_time.isoformat(), 'timeZone': 'Europe/Moscow'}
    }
    
    e = google_cal.add_event(event_body)
    event_link = e.get('htmlLink')
    nice_date = start_time.strftime("%d.%m.%Y в %H:%M")
    await message.answer(f"✅ Событие «{task_text}» добавлено на {nice_date}!\n<a href='{event_link}'>Открыть в календаре</a>", parse_mode="HTML")

@router.message(Command("s"))
@router.message(F.text == "🗓 Расписание")
async def cmd_schedule(message: types.Message):
    if message.text.startswith("/s"):
        text = message.text.replace("/s", "").strip()
        if not text:
            text = "сегодня"
    else:
        text = "сегодня"
        
    reply_text = await get_today_schedule(text)
    await message.answer(reply_text)

@router.message(F.text == "🌐 Статус сети")
async def cmd_status(message: types.Message):
    msg = await message.answer("🔄 Проверяю детекторы сбоев...")
    outages = await get_outages(config.MY_REGION)
    await msg.edit_text(outages)

@router.message(Command("clear"))
async def cmd_clear_reminds(message: types.Message, scheduler):  
    conn = sqlite3.connect('remind.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM reminders")
    conn.commit()
    conn.close()
    deleted_count = 0
    for job in scheduler.get_jobs():
        if job.name == 'send_reminder':
            job.remove()
            deleted_count += 1
            
    await message.answer(f"🧹 База полностью очищена!\nУдалено зависших таймеров: {deleted_count}")

@router.message(F.text == "🌦 Погода")
async def cmd_weather(message: types.Message):
    msg = await message.answer("🔄 Смотрю в окно...")
    weather = await get_short_weather(config.MY_CITY)
    await msg.edit_text(weather)

@router.message(F.text == "🌅 Утренняя сводка")
async def test_morning(message: types.Message, bot: Bot):
    msg = await message.answer("🔄 Собираю данные со всего интернета...")
    await morning_briefing(bot) # Просто вызываем нашу готовую функцию!
    await msg.delete() # Удаляем сообщение "Собираю данные..."