import logging

import aiohttp

from config import BOT_TOKEN, CHANNEL_LOGS, ADMIN_ID

logger = logging.getLogger(__name__)


async def send_alert(message: str):
    if not BOT_TOKEN:
        logger.warning("BOT_TOKEN missing; cannot send alert")
        return
    chat_id = CHANNEL_LOGS or ADMIN_ID
    if not chat_id:
        logger.warning("No alert target configured")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=10) as resp:
                if resp.status != 200:
                    logger.warning("Alert send failed: %s", await resp.text())
    except Exception as e:
        logger.warning("Alert send error: %s", e)
