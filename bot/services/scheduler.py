import asyncio
import logging
import time
from aiogram import Bot
from database import db
from services.marzban import marzban_api
from services.servers import get_server

logger = logging.getLogger(__name__)

async def check_subscriptions(bot: Bot):
    """Проверка истекших подписок и уведомления"""
    now = int(time.time())
    one_day = 86400
    
    # ИСПРАВЛЕНО: убрали await перед db.get_db()
    async with db.get_db() as conn:
        # Получаем всех пользователей, у которых есть подписка (sub_expire > 0)
        async with conn.execute("SELECT user_id, sub_expire, username, server_id FROM users WHERE sub_expire > 0") as cursor:
            users = await cursor.fetchall()

    for user in users:
        user_id, sub_expire, _username, server_id = user
        
        # 1. Если подписка истекла
        if now > sub_expire:
            # Отключаем в Marzban (ставим лимит 1 байт)
            server = get_server(server_id)
            base_url = server.get("marzban_url") if server else None
            await marzban_api.create_or_update_user(user_id, data_limit_bytes=1, base_url=base_url)
            
            # Сбрасываем срок в БД (ИСПРАВЛЕНО: убрали await)
            async with db.get_db() as conn:
                await conn.execute("UPDATE users SET sub_expire = 0 WHERE user_id = ?", (user_id,))
                await conn.commit()
            
            try:
                await bot.send_message(user_id, "⛔️ <b>Ваша подписка истекла!</b>\nДоступ к VPN приостановлен. Пожалуйста, продлите подписку в профиле.", parse_mode="HTML")
            except Exception as e:
                logger.warning("Не удалось отправить уведомление об истечении подписки пользователю %s: %s", user_id, e)

        # 2. Если осталось меньше 24 часов (и мы еще не напоминали - окно 1 час)
        elif (sub_expire - now) < one_day and (sub_expire - now) > (one_day - 3700):
            try:
                await bot.send_message(user_id, "⏳ <b>Остался 1 день!</b>\nНе забудьте продлить подписку, чтобы оставаться на связи.", parse_mode="HTML")
            except Exception as e:
                logger.warning("Не удалось отправить напоминание пользователю %s: %s", user_id, e)

async def scheduler_loop(bot: Bot):
    while True:
        try:
            await check_subscriptions(bot)
        except Exception as e:
            logger.error("Scheduler Error: %s", e)
        
        # Ждем 1 час (3600 секунд)
        await asyncio.sleep(3600)
