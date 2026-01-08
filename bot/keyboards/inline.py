from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import TARIFFS

# --- ТАРИФЫ ---
def tariffs_menu():
    # Генерация кнопок на основе настроек в config.py
    # Это решает пункт плана №4 (легкое редактирование цен)
    buttons = []
    for months, price in TARIFFS.items():
        # Формируем текст: "📅 1 Месяц — 125₽"
        text = f"📅 {months} {'Месяц' if months == 1 else 'Месяца' if months < 5 else 'Месяцев'} — {price}₽"
        buttons.append([InlineKeyboardButton(text=text, callback_data=f"buy_sub_{months}")])

    buttons.append([InlineKeyboardButton(text="📜 Правила и Оферта", callback_data="rules")])
    buttons.append([InlineKeyboardButton(text="⬅️ Закрыть", callback_data="close")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

# --- ПРОФИЛЬ ---
def profile_menu(sub_active=False):
    kb = []
    if sub_active:
        kb.append([InlineKeyboardButton(text="🔄 Продлить подписку", callback_data="open_tariffs")])
        kb.append([InlineKeyboardButton(text="🍏/🤖 Инструкция по подключению", callback_data="instr_main")])
    else:
        kb.append([InlineKeyboardButton(text="💎 Купить подписку", callback_data="open_tariffs")])
        kb.append([InlineKeyboardButton(text="🎁 Попробовать бесплатно", callback_data="get_trial")])

    # Кнопка рефералки внутри профиля
    kb.append([InlineKeyboardButton(text="🤝 Пригласить друга", callback_data="referral_info")])
    kb.append([InlineKeyboardButton(text="⬅️ Закрыть", callback_data="close")])

    return InlineKeyboardMarkup(inline_keyboard=kb)

# --- ОПЛАТА ---
def payment_menu(url: str, order_id: str, amount: float, user_balance: float):
    kb = []

    # 1. Ссылка на кассу
    kb.append([InlineKeyboardButton(text="💳 Оплатить картой/криптой", url=url)])

    # 2. Оплата балансом (если хватает денег)
    if user_balance >= amount:
        kb.append([InlineKeyboardButton(text=f"💰 Оплатить с баланса ({amount}₽)", callback_data=f"pay_balance_{order_id}")])

    # 3. Кнопка проверки
    kb.append([InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"check_pay_{order_id}")])
    kb.append([InlineKeyboardButton(text="❌ Отмена", callback_data="open_tariffs")])

    return InlineKeyboardMarkup(inline_keyboard=kb)

# --- ИНСТРУКЦИИ ---
def instructions_menu():
    kb = [
        [InlineKeyboardButton(text="🍏 iOS (iPhone/iPad)", callback_data="instr_ios")],
        [InlineKeyboardButton(text="🤖 Android", callback_data="instr_android")],
        [InlineKeyboardButton(text="💻 Windows", callback_data="instr_win")],
        [InlineKeyboardButton(text="🍎 macOS", callback_data="instr_mac")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="close")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

# --- КНОПКА НАЗАД (Утилита) ---
def back_btn(callback_data="close"):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Закрыть", callback_data=callback_data)]])
