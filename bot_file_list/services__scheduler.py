import asyncio
import logging
import time
from aiogram import Bot

from config import (
    SCHEDULER_INTERVAL_SECONDS,
    PAYMENT_PENDING_REMINDER_SECONDS,
    SUB_ALERT_DAYS_1,
    SUB_ALERT_DAYS_3,
    SUB_ALERT_WINDOW_SECONDS,
    TRAFFIC_ALERT_PERCENT,
)
from database import db
from services import content
from services.marzban import marzban_api
from services.servers import get_server
from services.alerts import send_alert

logger = logging.getLogger(__name__)

async def check_subscriptions(bot: Bot) -> None:
    """Проверка истекших подписок и уведомления"""
    now = int(time.time())
    one_day = 86400

    try:
        expired_subs = await db.get_expired_subscriptions()
    except Exception:
        logger.exception("Не удалось получить список истекших подписок")
        expired_subs = []
    for sub in expired_subs:
        try:
            user_id = sub["user_id"]
            server_id = sub["server_id"] or "default"

            server = get_server(server_id)
            base_url = server.get("marzban_url") if server else None
            result = await marzban_api.create_or_update_user(user_id, data_limit_bytes=1, base_url=base_url)
            if not result:
                await send_alert(
                    f"⚠️ Не удалось ограничить доступ для пользователя <b>{user_id}</b> "
                    f"на сервере <b>{server_id}</b>. Попробуем позже."
                )
                continue

            try:
                await db.expire_user_subscription(user_id, sub["id"])
            except Exception:
                logger.exception("Не удалось обновить статус подписки пользователя %s", user_id)

            try:
                await bot.send_message(
                    user_id,
                    "⛔️ <b>Ваша подписка истекла!</b>\nДоступ к VPN приостановлен. Пожалуйста, продлите подписку в профиле.",
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.warning("Не удалось отправить уведомление об истечении подписки пользователю %s: %s", user_id, e)
        except Exception:
            logger.exception("Ошибка при обработке истекшей подписки: %s", sub)

    async with db.get_db() as conn:
        async with conn.execute(
            "SELECT user_id, sub_expire, server_id, alert_sub_3d_sent, alert_sub_1d_sent, alert_traffic_90_sent "
            "FROM users WHERE sub_expire > 0"
        ) as cursor:
            users = await cursor.fetchall()

    for user_id, sub_expire, server_id, alert_sub_3d_sent, alert_sub_1d_sent, alert_traffic_90_sent in users:
        try:
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
        except Exception:
            logger.exception("Ошибка при обработке уведомлений пользователя %s", user_id)

async def check_pending_payments(bot: Bot) -> None:
    now = int(time.time())
    cutoff = now - PAYMENT_PENDING_REMINDER_SECONDS
    async with db.get_db() as conn:
        cursor = await conn.execute(
            """
            SELECT order_id, user_id
            FROM payments
            WHERE status = 'pending'
              AND created_at <= ?
              AND pending_reminder_sent = 0
            """,
            (cutoff,),
        )
        payments = await cursor.fetchall()

    if not payments:
        return

    reminder_text = content.get_message("payment_pending_reminder")

    for order_id, user_id in payments:
        try:
            await bot.send_message(user_id, reminder_text, parse_mode="HTML")
            async with db.get_db() as conn:
                await conn.execute(
                    "UPDATE payments SET pending_reminder_sent = 1 WHERE order_id = ?",
                    (order_id,),
                )
                await conn.commit()
        except Exception as exc:
            logger.warning("Не удалось отправить напоминание об оплате %s пользователю %s: %s", order_id, user_id, exc)

async def scheduler_loop(bot: Bot) -> None:
    while True:
        try:
            await check_subscriptions(bot)
            await check_pending_payments(bot)
        except Exception:
            logger.exception("Scheduler Error")
        
        await asyncio.sleep(SCHEDULER_INTERVAL_SECONDS)
