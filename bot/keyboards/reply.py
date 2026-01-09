from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from config import ADMIN_ID

def main_menu(user_id: int):
    # Базовые кнопки
    buttons = [
        [KeyboardButton(text="👤 Мой профиль"), KeyboardButton(text="💎 Купить подписку")],
        [KeyboardButton(text="📱 Инструкция"), KeyboardButton(text="🆘 Поддержка")],
        [KeyboardButton(text="🤝 Партнерка")],
        [KeyboardButton(text="🧠 Blueprint")]
    ]

    # Кнопка админа (показываем только администратору)
    if user_id == ADMIN_ID:
        buttons.append([KeyboardButton(text="👑 Админ-панель")])

    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True, # Делает кнопки компактными
        input_field_placeholder="Выберите действие..."
    )
