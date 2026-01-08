import asyncio
import logging
import time
from aiogram import Bot
from config import SUB_ALERT_DAYS_1, SUB_ALERT_DAYS_3, SUB_ALERT_WINDOW_SECONDS, TRAFFIC_ALERT_PERCENT
from database import db
from services.marzban import marzban_api
from services.servers import get_server

logger = logging.getLogger(__name__)

async def check_subscriptions(bot: Bot):
    """Проверка истекших подписок и уведомления"""
    now = int(time.time())
    one_day = 86400

    expired_subs = await db.get_expired_subscriptions()
    for sub in expired_subs:
        user_id = sub["user_id"]
        server_id = sub["server_id"] or "default"

        server = get_server(server_id)
        base_url = server.get("marzban_url") if server else None
        await marzban_api.create_or_update_user(user_id, data_limit_bytes=1, base_url=base_url)

        async with db.get_db() as conn:
            await conn.execute("UPDATE subscriptions SET expire_at = 0 WHERE id = ?", (sub["id"],))
            await conn.commit()

        try:
            await bot.send_message(
                user_id,
                "⛔️ <b>Ваша подписка истекла!</b>\nДоступ к VPN приостановлен. Пожалуйста, продлите подписку в профиле.",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.warning("Не удалось отправить уведомление об истечении подписки пользователю %s: %s", user_id, e)

    async with db.get_db() as conn:
        async with conn.execute(
            "SELECT user_id, sub_expire, server_id, alert_sub_3d_sent, alert_sub_1d_sent, alert_traffic_90_sent "
            "FROM users WHERE sub_expire > 0"
        ) as cursor:
            users = await cursor.fetchall()

    for user_id, sub_expire, server_id, alert_sub_3d_sent, alert_sub_1d_sent, alert_traffic_90_sent in users:
        time_left = sub_expire - now
        if (SUB_ALERT_DAYS_3 * one_day - SUB_ALERT_WINDOW_SECONDS) < time_left <= (SUB_ALERT_DAYS_3 * one_day):
            if not alert_sub_3d_sent:
                try:
                    await bot.send_message(
                        user_id,
                        "📅 <b>До конца подписки осталось 3 дня!</b>\nПродлите подписку заранее, чтобы не потерять доступ.",
                        parse_mode="HTML"
                    )
                    async with db.get_db() as conn:
                        await conn.execute(
                            "UPDATE users SET alert_sub_3d_sent = 1 WHERE user_id = ?",
                            (user_id,),
                        )
                        await conn.commit()
                except Exception as e:
                    logger.warning("Не удалось отправить 3-дневное напоминание пользователю %s: %s", user_id, e)

        if (SUB_ALERT_DAYS_1 * one_day - SUB_ALERT_WINDOW_SECONDS) < time_left <= (SUB_ALERT_DAYS_1 * one_day):
            if not alert_sub_1d_sent:
                try:
                    await bot.send_message(
                        user_id,
                        "⏳ <b>Остался 1 день!</b>\nНе забудьте продлить подписку, чтобы оставаться на связи.",
                        parse_mode="HTML"
                    )
                    async with db.get_db() as conn:
                        await conn.execute(
                            "UPDATE users SET alert_sub_1d_sent = 1 WHERE user_id = ?",
                            (user_id,),
                        )
                        await conn.commit()
                except Exception as e:
                    logger.warning("Не удалось отправить 1-дневное напоминание пользователю %s: %s", user_id, e)

        if not alert_traffic_90_sent:
            server = get_server(server_id or "default")
            base_url = server.get("marzban_url") if server else None
            user_info = await marzban_api.get_user_info(f"user_{user_id}", base_url=base_url)
            if user_info:
                used_bytes = user_info.get("used_traffic") or 0
                limit_bytes = user_info.get("data_limit") or 0
                if limit_bytes > 0:
                    percent = int((used_bytes / limit_bytes) * 100)
                    if percent >= TRAFFIC_ALERT_PERCENT:
                        try:
                            await bot.send_message(
                                user_id,
                                f"💾 <b>Вы использовали {percent}% трафика!</b>\n"
                                "Проверьте остаток, чтобы избежать отключения.",
                                parse_mode="HTML"
                            )
                            async with db.get_db() as conn:
                                await conn.execute(
                                    "UPDATE users SET alert_traffic_90_sent = 1 WHERE user_id = ?",
                                    (user_id,),
                                )
                                await conn.commit()
                        except Exception as e:
                            logger.warning("Не удалось отправить алерт по трафику пользователю %s: %s", user_id, e)
async def scheduler_loop(bot: Bot):
    while True:
        try:
            await check_subscriptions(bot)
        except Exception as e:
            logger.error("Scheduler Error: %s", e)
        
        # Ждем 1 час (3600 секунд)
        await asyncio.sleep(3600)
