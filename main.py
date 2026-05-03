import asyncio
import aiohttp
from loguru import logger
from datetime import datetime
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.core.middlewares import PrivateBotMiddleware

import app.core.config as config
import app.database.database as database
from app.services.handlers import router, send_reminder, morning_briefing, monitor_network

from app.core.http_client import init_http_client, close_http_client

# --- patch SSL ---
old_init = aiohttp.TCPConnector.__init__
def new_init(self, *args, **kwargs):
   kwargs['ssl'] = False
   old_init(self, *args, **kwargs)
aiohttp.TCPConnector.__init__ = new_init

async def restore_reminders(scheduler: AsyncIOScheduler, bot: Bot):
    rows = await database.get_all_reminders()
    for row in rows:
        reminder_id, chat_id, task_text, time_str = row
        try:
            time_obj = datetime.fromisoformat(time_str)
        except ValueError:
            continue 
        scheduler.add_job(
            send_reminder,               
            trigger='date',              
            run_date=time_obj,            
            kwargs={'bot': bot, 'chat_id': chat_id, 'task_text': task_text, 'reminder_id': reminder_id}
        )
    logger.info(f"Восстановлено напоминаний: {len(rows)}")

async def main():
    await database.init_db()

    if config.PROXY_URL:
        session = AiohttpSession(proxy=config.PROXY_URL)
        bot = Bot(token=config.BOT_TOKEN, session=session)
    else:
        bot = Bot(token=config.BOT_TOKEN)

    scheduler = AsyncIOScheduler(timezone=config.MY_TIME_ZONE)
    await restore_reminders(scheduler, bot)
    
    scheduler.add_job(morning_briefing, trigger='cron', hour=6, minute=0, kwargs={'bot': bot})
    scheduler.start()
    
    scheduler.add_job(monitor_network, trigger='interval', minutes=15, kwargs={'bot': bot})

    dp = Dispatcher()
    dp.include_router(router)
    dp.message.middleware(PrivateBotMiddleware(config.MY_ID))
    dp['scheduler'] = scheduler

    dp.startup.register(init_http_client)
    dp.shutdown.register(close_http_client)
    
    logger.info("--- БОТ НАПОМИНАЛКА ЗАПУЩЕН ---") 
    await dp.start_polling(bot)
    


if __name__ == "__main__":
    asyncio.run(main())