import logging
from typing import Optional, Union

from config import ADMIN_ID, BOT_TOKEN, CHANNEL_LOGS
from services.http import get_session

logger = logging.getLogger(__name__)


async def send_alert(message: str) -> None:
    if not BOT_TOKEN:
        logger.warning("BOT_TOKEN missing; cannot send alert")
        return
    chat_id: Optional[Union[str, int]] = CHANNEL_LOGS or ADMIN_ID
    if not chat_id:
        logger.warning("No alert target configured")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
    try:
        session = await get_session()
        async with session.post(url, json=payload, timeout=10) as resp:
            if resp.status != 200:
                logger.warning("Alert send failed: %s", await resp.text())
    except Exception as e:
        logger.warning("Alert send error: %s", e)
