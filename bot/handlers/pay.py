import uuid
import time
import datetime
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from database import db
from services.payment import PaymentService
from services.marzban import marzban_api
from keyboards import inline
from config import TARIFFS, REFERRAL_BONUS_PERCENT

pay_router = Router()

# ==========================================
# 1. ВЫБОР ТАРИФА
# ==========================================

@pay_router.message(F.text == "💎 Купить подписку")
async def show_tariffs(message: Message):
    await message.answer("💎 <b>Выберите период подписки:</b>", reply_markup=inline.tariffs_menu(), parse_mode="HTML")

@pay_router.callback_query(F.data == "open_tariffs")
async def show_tariffs_cb(callback: CallbackQuery):
    if callback.message.photo:
        await callback.message.delete()
        await callback.message.answer("💎 <b>Выберите период подписки:</b>", reply_markup=inline.tariffs_menu(), parse_mode="HTML")
    else:
        await callback.message.edit_text("💎 <b>Выберите период подписки:</b>", reply_markup=inline.tariffs_menu(), parse_mode="HTML")

# ==========================================
# 2. СОЗДАНИЕ СЧЕТА
# ==========================================

@pay_router.callback_query(F.data.startswith("buy_sub_"))
async def create_order(callback: CallbackQuery):
    try:
        months = int(callback.data.split("_")[2])
    except:
        await callback.answer("Ошибка тарифа", show_alert=True)
        return

    amount = TARIFFS.get(months)
    if not amount:
        await callback.answer("Тариф не найден", show_alert=True)
        return

    user_id = callback.from_user.id
    order_id = str(uuid.uuid4())

    user_data = await db.get_user(user_id)
    balance = user_data['balance'] if user_data else 0.0

    async with db.get_db() as conn:
        await conn.execute(
            "INSERT INTO payments (order_id, user_id, amount, months, created_at) VALUES (?, ?, ?, ?, ?)",
            (order_id, user_id, amount, months, int(time.time()))
        )
        await conn.commit()

    pay_url = PaymentService.generate_url(amount, order_id)

    text = (
        f"🧾 <b>Счет на оплату</b>\n"
        f"➖➖➖➖➖➖➖➖➖\n"
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
        cursor = await conn.execute("SELECT status, user_id, months, amount FROM payments WHERE order_id = ?", (order_id,))
        payment = await cursor.fetchone()
    
    if not payment:
        await callback.answer("❌ Заказ не найден.", show_alert=True)
        return

    status, user_id, months, amount = payment

    if status == 'paid':
        await callback.answer("✅ Этот счет уже оплачен!", show_alert=True)
        return

    await callback.answer("🔄 Проверяю статус платежа...")

    is_paid = await PaymentService.check_status(order_id)
    
    if is_paid:
        await process_success_payment(callback.message, user_id, months, amount, order_id, "AAIO")
    else:
        await callback.message.answer("❌ Оплата пока не поступила. Попробуйте через минуту.", show_alert=True)

# ==========================================
# 4. ОПЛАТА БАЛАНСОМ (ИСПРАВЛЕНО)
# ==========================================

@pay_router.callback_query(F.data.startswith("pay_balance_"))
async def pay_with_balance(callback: CallbackQuery):
    order_id = callback.data.split("pay_balance_")[1]

    async with db.get_db() as conn:
        # Начинаем транзакцию
        await conn.execute("BEGIN TRANSACTION")
        
        try:
            # 1. Получаем данные заказа
            cursor = await conn.execute("SELECT user_id, amount, months, status FROM payments WHERE order_id = ?", (order_id,))
            payment = await cursor.fetchone()
            
            if not payment:
                await conn.rollback()
                await callback.answer("Ошибка заказа", show_alert=True)
                return
                
            p_user_id, p_amount, p_months, p_status = payment
            
            if p_status == 'paid':
                await conn.rollback()
                await callback.answer("Уже оплачено", show_alert=True)
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
                new_balance = current_balance - p_amount
                
                # Обновляем баланс
                await conn.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, p_user_id))
                
                # Обновляем статус заказа
                await conn.execute("UPDATE payments SET status = 'paid' WHERE order_id = ?", (order_id,))
                
                # ИСПРАВЛЕНИЕ: Пишем транзакцию прямо здесь (без вызова db.add_transaction)
                await conn.execute(
                    "INSERT INTO transactions (user_id, amount, type, comment, created_at) VALUES (?, ?, ?, ?, ?)",
                    (p_user_id, -p_amount, "purchase", f"Оплата подписки {p_months} мес.", int(time.time()))
                )
                
                await conn.commit()
                # Переходим к успешной выдаче (уже вне транзакции БД)
                await process_success_payment(callback.message, p_user_id, p_months, p_amount, order_id, "Balance")
            else:
                await conn.rollback()
                await callback.answer("❌ Недостаточно средств на балансе!", show_alert=True)
        except Exception as e:
            await conn.rollback()
            print(f"Error in pay_balance: {e}")
            await callback.answer("Ошибка при оплате", show_alert=True)


# ==========================================
# 🛠 ОБРАБОТКА УСПЕШНОЙ ПОКУПКИ
# ==========================================

async def process_success_payment(message: Message, user_id: int, months: int, amount: float, order_id: str, method: str):
    # 1. Если это внешняя оплата, фиксируем в БД (для баланса уже сделали)
    if method == "AAIO":
        async with db.get_db() as conn:
            await conn.execute("UPDATE payments SET status = 'paid' WHERE order_id = ?", (order_id,))
            # Запись о пополнении
            await conn.execute(
                "INSERT INTO transactions (user_id, amount, type, comment, created_at) VALUES (?, ?, ?, ?, ?)",
                (user_id, amount, "deposit", f"Пополнение AAIO {order_id}", int(time.time()))
            )
            await conn.commit()

    # 2. Продлеваем подписку
    async with db.get_db() as conn:
        cursor = await conn.execute("SELECT sub_expire, referrer_id FROM users WHERE user_id = ?", (user_id,))
        res = await cursor.fetchone()
        
        current_expire = res[0] if res[0] else 0
        referrer_id = res[1] if res[1] else 0
        
        now = int(time.time())
        start_date = max(current_expire, now)
        new_expire = start_date + (months * 30 * 86400)
        
        await conn.execute("UPDATE users SET sub_expire = ? WHERE user_id = ?", (new_expire, user_id))
        await conn.commit()

    # 3. Активируем в Marzban
    await marzban_api.create_or_update_user(user_id, 0)
    
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
        except:
            pass

    try:
        await message.delete()
    except: pass
    
    expire_dt = datetime.datetime.fromtimestamp(new_expire).strftime('%d.%m.%Y')
    
    await message.answer(
        f"🎉 <b>Оплата прошла успешно!</b>\n\n"
        f"✅ Подписка продлена на <b>{months} мес.</b>\n"
        f"⏳ Действует до: {expire_dt}\n\n"
        f"Нажмите кнопку ниже, чтобы получить ключ.",
        reply_markup=inline.back_btn("close"),
        parse_mode="HTML"
    )
