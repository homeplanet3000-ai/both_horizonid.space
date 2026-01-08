import datetime
import logging
import time
import uuid
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from database import db
from services.payment import PaymentService
from services.marzban import marzban_api
from services.servers import get_server
from keyboards import inline
from config import PAYMENT_DEFAULT_EMAIL, REFERRAL_BONUS_PERCENT, TARIFFS

pay_router = Router()
logger = logging.getLogger(__name__)

# ==========================================
# 1. ВЫБОР ТАРИФА
# ==========================================

@pay_router.message(F.text == "💎 Купить подписку")
async def show_tariffs(message: Message):
    await message.answer("🌍 <b>Выберите сервер:</b>", reply_markup=inline.servers_menu(), parse_mode="HTML")

@pay_router.callback_query(F.data == "open_tariffs")
async def show_tariffs_cb(callback: CallbackQuery):
    if callback.message.photo:
        await callback.message.delete()
        await callback.message.answer("🌍 <b>Выберите сервер:</b>", reply_markup=inline.servers_menu(), parse_mode="HTML")
    else:
        await callback.message.edit_text("🌍 <b>Выберите сервер:</b>", reply_markup=inline.servers_menu(), parse_mode="HTML")

@pay_router.callback_query(F.data.startswith("select_server_"))
async def select_server(callback: CallbackQuery):
    server_id = callback.data.split("select_server_")[1]
    server = get_server(server_id)
    if not server:
        await callback.answer("Сервер не найден", show_alert=True)
        return
    await callback.message.edit_text(
        f"💎 <b>Выберите период подписки:</b>\n\n"
        f"Сервер: {server.get('flag', '🌍')} {server.get('name', 'Сервер')}",
        reply_markup=inline.tariffs_menu(server_id),
        parse_mode="HTML"
    )

# ==========================================
# 2. СОЗДАНИЕ СЧЕТА
# ==========================================

@pay_router.callback_query(F.data.startswith("buy_sub_"))
async def create_order(callback: CallbackQuery):
    try:
        parts = callback.data.split("_", 3)
        months = int(parts[2])
        server_id = parts[3] if len(parts) > 3 else "default"
    except (ValueError, IndexError):
        await callback.answer("Ошибка тарифа", show_alert=True)
        return

    amount = TARIFFS.get(months)
    if not amount:
        await callback.answer("Тариф не найден", show_alert=True)
        return

    server = get_server(server_id)
    if not server:
        await callback.answer("Сервер не найден", show_alert=True)
        return

    user_id = callback.from_user.id
    order_id = str(uuid.uuid4())

    user_data = await db.get_user(user_id)
    balance = user_data['balance'] if user_data else 0.0

    async with db.get_db() as conn:
        await conn.execute(
            "INSERT INTO payments (order_id, user_id, amount, months, server_id, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (order_id, user_id, amount, months, server_id, int(time.time()))
        )
        await conn.commit()

    pay_url = PaymentService.generate_url(amount, order_id, PAYMENT_DEFAULT_EMAIL)
    if not pay_url:
        await callback.message.edit_text(
            "⚠️ Платежный сервис временно недоступен. Попробуйте позже или обратитесь в поддержку."
        )
        return

    text = (
        f"🧾 <b>Счет на оплату</b>\n"
        f"➖➖➖➖➖➖➖➖➖\n"
        f"🌍 Сервер: <b>{server.get('flag', '🌍')} {server.get('name', 'Сервер')}</b>\n"
        f"📅 Период: <b>{months} мес.</b>\n"
        f"💰 К оплате: <b>{amount} ₽</b>\n"
        f"🆔 Заказ: <code>{order_id}</code>\n\n"
        f"<i>Выберите способ оплаты ниже:</i>"
    )

    await callback.message.edit_text(
        text, 
        reply_markup=inline.payment_menu(pay_url, order_id, amount, balance), 
        parse_mode="HTML"
    )

# ==========================================
# 3. ПРОВЕРКА ОПЛАТЫ (Внешняя)
# ==========================================

@pay_router.callback_query(F.data.startswith("check_pay_"))
async def check_payment(callback: CallbackQuery):
    order_id = callback.data.split("check_pay_")[1]

    async with db.get_db() as conn:
        conn.row_factory = None
        await conn.execute("BEGIN IMMEDIATE")
        cursor = await conn.execute(
            "SELECT status, user_id, months, amount, server_id FROM payments WHERE order_id = ?",
            (order_id,),
        )
        payment = await cursor.fetchone()

        if not payment:
            await conn.rollback()
            await callback.answer("❌ Заказ не найден.", show_alert=True)
            return

        status, user_id, months, amount, server_id = payment

        if status == "paid":
            await conn.rollback()
            await callback.answer("✅ Этот счет уже оплачен!", show_alert=True)
            return

        if status == "processing":
            await conn.rollback()
            await callback.answer("⏳ Платеж уже обрабатывается, попробуйте чуть позже.", show_alert=True)
            return

        if status not in ("pending", "paid_error"):
            await conn.rollback()
            await callback.answer("⚠️ Неверный статус заказа. Обратитесь в поддержку.", show_alert=True)
            return

        cursor = await conn.execute(
            "UPDATE payments SET status = 'processing' WHERE order_id = ? AND status = ?",
            (order_id, status),
        )
        if cursor.rowcount == 0:
            await conn.rollback()
            await callback.answer("⏳ Платеж уже обрабатывается, попробуйте чуть позже.", show_alert=True)
            return

        await conn.commit()

    await callback.answer("🔄 Проверяю статус платежа...")

    already_paid = status == "paid_error"
    is_paid = already_paid or await PaymentService.check_status(order_id)

    if not is_paid:
        async with db.get_db() as conn:
            await conn.execute(
                "UPDATE payments SET status = 'pending' WHERE order_id = ? AND status = 'processing'",
                (order_id,),
            )
            await conn.commit()
        await callback.answer("❌ Оплата пока не поступила. Попробуйте через минуту.", show_alert=True)
        return

    await process_success_payment(callback.message, user_id, months, amount, order_id, "AAIO", server_id)

# ==========================================
# 3.1 ЗАГЛУШКА TELEGRAM STARS
# ==========================================

@pay_router.callback_query(F.data.startswith("pay_stars_"))
async def pay_with_stars(callback: CallbackQuery):
    await callback.answer("⭐ Оплата Telegram Stars скоро появится!", show_alert=True)

# ==========================================
# 4. ОПЛАТА БАЛАНСОМ (ИСПРАВЛЕНО)
# ==========================================

@pay_router.callback_query(F.data.startswith("pay_balance_"))
async def pay_with_balance(callback: CallbackQuery):
    order_id = callback.data.split("pay_balance_")[1]

    async with db.get_db() as conn:
        # Начинаем транзакцию
        await conn.execute("BEGIN IMMEDIATE")
        
        try:
            # 1. Получаем данные заказа
            cursor = await conn.execute("SELECT user_id, amount, months, status, server_id FROM payments WHERE order_id = ?", (order_id,))
            payment = await cursor.fetchone()
            
            if not payment:
                await conn.rollback()
                await callback.answer("Ошибка заказа", show_alert=True)
                return
                
            p_user_id, p_amount, p_months, p_status, p_server_id = payment
            
            if p_status == 'paid':
                await conn.rollback()
                await callback.answer("Уже оплачено", show_alert=True)
                return

            if p_status == "processing":
                await conn.rollback()
                await callback.answer("⏳ Заказ уже обрабатывается, попробуйте позже.", show_alert=True)
                return

            if p_status != "pending":
                await conn.rollback()
                await callback.answer("⚠️ Неверный статус заказа", show_alert=True)
                return

            # 2. Получаем баланс
            cursor = await conn.execute("SELECT balance FROM users WHERE user_id = ?", (p_user_id,))
            user_res = await cursor.fetchone()
            if not user_res:
                await conn.rollback()
                return
            current_balance = user_res[0]

            # 3. Проверка и списание
            if current_balance >= p_amount:
                await conn.execute(
                    "UPDATE payments SET status = 'processing' WHERE order_id = ? AND status = 'pending'",
                    (order_id,),
                )
                await conn.commit()
                # Переходим к успешной выдаче (уже вне транзакции БД)
                await process_success_payment(callback.message, p_user_id, p_months, p_amount, order_id, "Balance", p_server_id)
            else:
                await conn.rollback()
                await callback.answer("❌ Недостаточно средств на балансе!", show_alert=True)
        except Exception as e:
            await conn.rollback()
            logger.error("Ошибка оплаты с баланса (order_id=%s): %s", order_id, e)
            await callback.answer("Ошибка при оплате", show_alert=True)


# ==========================================
# 🛠 ОБРАБОТКА УСПЕШНОЙ ПОКУПКИ
# ==========================================

async def process_success_payment(message: Message, user_id: int, months: int, amount: float, order_id: str, method: str, server_id: str):
    if method == "Balance":
        async with db.get_db() as conn:
            conn.row_factory = None
            cursor = await conn.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
            user_balance = await cursor.fetchone()
            if not user_balance or user_balance[0] < amount:
                await conn.execute(
                    "UPDATE payments SET status = 'pending' WHERE order_id = ? AND status = 'processing'",
                    (order_id,),
                )
                await conn.commit()
                await message.answer("❌ Недостаточно средств на балансе для оплаты.")
                return

    # 1. Активируем в Marzban
    server = get_server(server_id)
    base_url = server.get("marzban_url") if server else None
    key_link = await marzban_api.create_or_update_user(user_id, 0, base_url=base_url)

    if not key_link:
        fail_status = "paid_error" if method == "AAIO" else "pending"
        async with db.get_db() as conn:
            await conn.execute(
                "UPDATE payments SET status = ? WHERE order_id = ? AND status = 'processing'",
                (fail_status, order_id),
            )
            await conn.commit()
        await message.answer(
            "⚠️ Не удалось активировать доступ в VPN. Мы уже получили оплату, "
            "но ключ временно не создан. Нажмите «Проверить оплату» позже или обратитесь в поддержку."
        )
        return

    now = int(time.time())
    async with db.get_db() as conn:
        await conn.execute("BEGIN IMMEDIATE")
        cursor = await conn.execute("SELECT sub_expire, referrer_id FROM users WHERE user_id = ?", (user_id,))
        res = await cursor.fetchone()
        if not res:
            await conn.rollback()
            await message.answer("⚠️ Пользователь не найден. Обратитесь в поддержку.")
            return

        current_expire = res[0] if res[0] else 0
        referrer_id = res[1] if res[1] else 0
        start_date = max(current_expire, now)
        new_expire = start_date + (months * 30 * 86400)

        if method == "Balance":
            cursor = await conn.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
            balance_row = await cursor.fetchone()
            if not balance_row or balance_row[0] < amount:
                await conn.execute(
                    "UPDATE payments SET status = 'pending' WHERE order_id = ? AND status = 'processing'",
                    (order_id,),
                )
                await conn.commit()
                await message.answer("❌ Недостаточно средств на балансе для оплаты.")
                return
            await conn.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, user_id))
            await conn.execute(
                "INSERT INTO transactions (user_id, amount, type, comment, created_at) VALUES (?, ?, ?, ?, ?)",
                (user_id, -amount, "purchase", f"Оплата подписки {months} мес.", int(time.time())),
            )

        if method == "AAIO":
            await conn.execute(
                "INSERT INTO transactions (user_id, amount, type, comment, created_at) VALUES (?, ?, ?, ?, ?)",
                (user_id, amount, "deposit", f"Пополнение AAIO {order_id}", int(time.time())),
            )

        await conn.execute(
            "UPDATE users SET sub_expire = ?, server_id = ?, "
            "alert_sub_3d_sent = 0, alert_sub_1d_sent = 0, alert_traffic_90_sent = 0 "
            "WHERE user_id = ?",
            (new_expire, server_id, user_id),
        )

        await conn.execute(
            """
            INSERT INTO subscriptions (user_id, server_id, link, data_limit_bytes, expire_at, is_trial, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, server_id, key_link, 0, new_expire, 0, int(time.time())),
        )

        await conn.execute(
            "UPDATE payments SET status = 'paid' WHERE order_id = ? AND status = 'processing'",
            (order_id,),
        )
        await conn.commit()

    # 4. Реферальная система (только для AAIO)
    if referrer_id and referrer_id != 0 and method == "AAIO":
        bonus = amount * (REFERRAL_BONUS_PERCENT / 100)
        async with db.get_db() as conn:
            await conn.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (bonus, referrer_id))
            await conn.execute(
                "INSERT INTO transactions (user_id, amount, type, comment, created_at) VALUES (?, ?, ?, ?, ?)",
                (referrer_id, bonus, "bonus", f"Бонус от реферала {user_id}", int(time.time()))
            )
            await conn.commit()
            
        try:
            await message.bot.send_message(referrer_id, f"🎉 <b>Реферальный бонус!</b>\nНачислено: +{bonus} ₽")
        except Exception as e:
            logger.warning("Не удалось отправить уведомление рефереру %s: %s", referrer_id, e)

    try:
        await message.delete()
    except Exception as e:
        logger.debug("Не удалось удалить сообщение после оплаты: %s", e)
    
    expire_dt = datetime.datetime.fromtimestamp(new_expire).strftime('%d.%m.%Y')
    
    await message.answer(
        f"🎉 <b>Оплата прошла успешно!</b>\n\n"
        f"✅ Подписка продлена на <b>{months} мес.</b>\n"
        f"⏳ Действует до: {expire_dt}\n\n"
        f"Нажмите кнопку ниже, чтобы получить ключ.",
        reply_markup=inline.back_btn("close"),
        parse_mode="HTML"
    )
    server = get_server(server_id)
    if not server:
        logger.warning("Сервер не найден после успешной оплаты: %s", server_id)
