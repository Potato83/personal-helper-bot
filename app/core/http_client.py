import aiohttp
from aiohttp_socks import ProxyConnector
from loguru import logger
import app.core.config as config

_session: aiohttp.ClientSession | None = None

async def init_http_client():
    global _session
    connector = ProxyConnector.from_url(config.PROXY_URL) if config.PROXY_URL else None
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    _session = aiohttp.ClientSession(
        connector=connector,
        timeout=aiohttp.ClientTimeout(total=15),
        headers=headers
    )
    logger.info("Глобальная HTTP-сессия инициализирована.")

async def close_http_client():
    global _session
    if _session:
        await _session.close()
        logger.info("Глобальная HTTP-сессия закрыта.")

def get_session() -> aiohttp.ClientSession:
    if _session is None:
        raise RuntimeError("HTTP-клиент не инициализирован!")
    return _session