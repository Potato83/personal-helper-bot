import asyncio
import dateparser
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import app.core.config as config

SCOPES =['https://www.googleapis.com/auth/calendar']
SERVICE_ACCOUNT_FILE = 'credentials.json'

creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
calendar_service = build('calendar', 'v3', credentials=creds)

async def add_event(event_body):
    return await asyncio.to_thread(
        calendar_service.events().insert(calendarId=config.MY_EMAIL, body=event_body).execute
    )

async def get_events(time_min, time_max):
    def _fetch():
        return calendar_service.events().list(
            calendarId=config.MY_EMAIL, timeMin=time_min, timeMax=time_max,   
            singleEvents=True, orderBy='startTime'               
        ).execute()
    events_result = await asyncio.to_thread(_fetch)
    return events_result.get('items',[])

async def get_today_schedule(text='сегодня'):
    if not text: text = 'сегодня'
    target_date = dateparser.parse(text, settings={'TIMEZONE': config.MY_TIME_ZONE, 'PREFER_DATES_FROM': 'future'})
    
    start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = target_date.replace(hour=23, minute=59, second=59, microsecond=0)
    
    events = await get_events(start_of_day.isoformat() + "+03:00", end_of_day.isoformat() + "+03:00")
    
    if not events:
        return "На этот день ничего не запланировано! Можно отдыхать 🛋"

    reply_text = f"🗓 Расписание на {target_date.strftime('%d.%m.%Y')}:\n\n"
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        time_formatted = start[11:16] if 'T' in start else "Весь день"
        summary = event.get('summary', 'Без названия')
        reply_text += f"{time_formatted} - {summary}\n"
    return reply_text