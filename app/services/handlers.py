import re
import dateparser
from datetime import datetime, timedelta
from aiogram import Router, types, Bot, F
from aiogram.filters import Command

import re
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import asyncio

from app.services.parsers import get_exchange_rates, get_news, get_weather, get_outages
from app.services.google_cal import get_today_schedule
from app.core.state import bot_state
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from app.services.ai_service import process_user_intent
from app.core.state import bot_state

import app.core.config as config
import app.database.database as database 
import app.services.google_cal as google_cal

router = Router()

# keys for better view
main_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="🌦 Погода"), KeyboardButton(text="🗓 Расписание")],
              [KeyboardButton(text="🌐 Статус сети"), KeyboardButton(text="🧹 Очистить БД")],
              [KeyboardButton(text="🌅 Утренняя сводка")]
    ],
    resize_keyboard=True
)

# --- helpers --- 
async def send_reminder(bot: Bot, chat_id: int, task_text: str, reminder_id: int):
    await bot.send_message(chat_id, f"🔔 НАПОМИНАНИЕ: {task_text}") 
    await database.delete_reminder(reminder_id)

async def morning_briefing(bot: Bot):
    weather_task = get_weather(config.MY_CITY)
    schedule_task = get_today_schedule("сегодня")
    rates_task = get_exchange_rates()
    news_task = get_news()
    outages_task = get_outages(config.MY_REGION)
      
    weather, schedule_text, rates, news, outages = await asyncio.gather(
        weather_task, schedule_task, rates_task, news_task, outages_task
    )
    
    text = (
        f"🌅 <b>Доброе утро! Вот сводка на сегодня:</b>\n\n"
        f"{rates}\n\n"
        f"{weather}\n\n"
        f"{outages}\n\n"
        f"{schedule_text}\n\n"
        f"{news}"
    )
    
    await bot.send_message(chat_id=config.MY_ID, text=text, parse_mode="HTML", disable_web_page_preview=True)

# --- network check ---
async def monitor_network(bot: Bot):
    outages = await get_outages(config.MY_REGION)
    is_down = "⚠️" in outages
    
    # OK -> DOWN
    if is_down and bot_state.last_network_status == "OK":
        await bot.send_message(config.MY_ID, f"🚨 АЛАРМ! Зафиксированы сбои:\n\n{outages}")
        bot_state.last_network_status = "DOWN" 
        
    # DOWN -> OK
    elif not is_down and bot_state.last_network_status == "DOWN":
        await bot.send_message(config.MY_ID, "✅ Ура! Сбои прекратились, интернет и сервисы работают нормально.")
        bot_state.last_network_status = "OK"
        
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

    reminder_id = await database.add_reminder(message.chat.id, task_text, str(time))
    
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
    
    e = await google_cal.add_event(event_body)
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
    await database.clear_all_reminders()
    
    deleted_count = 0
    for job in scheduler.get_jobs():
        if job.name == 'send_reminder':
            job.remove()
            deleted_count += 1
            
    await message.answer(f"🧹 База полностью очищена!\nУдалено зависших таймеров: {deleted_count}")

@router.message(F.text == "🌦 Погода")
async def cmd_weather(message: types.Message):
    msg = await message.answer("🔄 Связываюсь с метеорологами...")
    weather = await get_weather(config.MY_CITY)
    await msg.edit_text(weather)

@router.message(F.text == "🌅 Утренняя сводка")
async def test_morning(message: types.Message, bot: Bot):
    msg = await message.answer("🔄 Собираю данные со всего интернета (турбо-режим)...")
    
    start_time = datetime.now()
    await morning_briefing(bot)
    end_time = datetime.now()
    
    seconds = (end_time - start_time).seconds
    await msg.edit_text(f"✅ Сводка собрана за {seconds} секунд!")
    
# --- AI и Inline Обработчики ---
@router.message(F.text)
async def handle_ai_chat(message: types.Message):
    msg = await message.answer("🤔 Думаю...")
    
    intent = await process_user_intent(message.text)
    action = intent.get("action")
    text = intent.get("text", "")
    time_str = intent.get("time", "")

    if action == "chat":
        await msg.edit_text(text)
        
    elif action == "weather":
        await msg.edit_text("🔄 Смотрю на небо...")
        weather = await get_weather(config.MY_CITY, time_str)
        await msg.edit_text(weather)
            
    elif action == "schedule":
        await msg.edit_text("🔄 Проверяю календарь...")
        target_date = time_str if time_str else "сегодня"
        sched = await get_today_schedule(target_date)
        await msg.edit_text(sched)
        
    elif action in ["remind", "calendar"]:
        bot_state.pending_actions[message.from_user.id] = {
            "action": action,
            "text": text,
            "time": time_str
        }
        
        action_name = "напоминание" if action == "remind" else "событие в календарь"
        
        kb = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="✅ Добавить", callback_data="confirm_action"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")
            ]
        ])
        
        await msg.edit_text(
            f"🤖 Я понял так. Добавляем {action_name}?\n\n"
            f"📝 <b>Что:</b> {text}\n"
            f"🕒 <b>Когда:</b> {time_str}",
            parse_mode="HTML",
            reply_markup=kb
        )
    else:
        await msg.edit_text("❌ Не понял запрос. Попробуй иначе.")

@router.callback_query(F.data.in_(["confirm_action", "cancel_action"]))
async def process_inline_action(callback: CallbackQuery, bot: Bot, scheduler):
    user_id = callback.from_user.id
    
    if callback.data == "cancel_action":
        bot_state.pending_actions.pop(user_id, None)
        await callback.message.edit_text("❌ Действие отменено.")
        await callback.answer()
        return

    # Если подтвердили (confirm_action)
    pending = bot_state.pending_actions.pop(user_id, None)
    if not pending:
        await callback.answer("⏳ Время вышло или действие уже выполнено", show_alert=True)
        return
        
    action, text, time_str = pending["action"], pending["text"], pending["time"]
    
    if action == "remind":
        time_obj = dateparser.parse(
            time_str, 
            settings={'TIMEZONE': config.MY_TIME_ZONE, 'PREFER_DATES_FROM': 'future', 'RETURN_AS_TIMEZONE_AWARE': True}
        )
        if not time_obj:
            await callback.message.edit_text(f"❌ Не смог распознать время: {time_str}")
            return
            
        reminder_id = await database.add_reminder(callback.message.chat.id, text, str(time_obj))
        scheduler.add_job(
            send_reminder,               
            trigger='date',              
            run_date=time_obj,               
            kwargs={'bot': bot, 'chat_id': callback.message.chat.id, 'task_text': text, 'reminder_id': reminder_id}
        )
        nice_time = time_obj.strftime("%d.%m в %H:%M")
        await callback.message.edit_text(f"✅ Напоминание установлено на {nice_time}!")
        
    elif action == "calendar":
        start_time = dateparser.parse(time_str, settings={'TIMEZONE': config.MY_TIME_ZONE, 'PREFER_DATES_FROM': 'future'})
        if not start_time:
            await callback.message.edit_text(f"❌ Не смог распознать время: {time_str}")
            return
            
        end_time = start_time + timedelta(hours=1)
        event_body = {
            'summary': text,
            'start': {'dateTime': start_time.isoformat(), 'timeZone': config.MY_TIME_ZONE},
            'end': {'dateTime': end_time.isoformat(), 'timeZone': config.MY_TIME_ZONE}
        }
        e = await google_cal.add_event(event_body)
        await callback.message.edit_text(
            f"✅ Событие добавлено!\n<a href='{e.get('htmlLink')}'>Открыть календарь</a>", 
            parse_mode="HTML", disable_web_page_preview=True
        )

    await callback.answer()
    
    