import logging

from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import ADMIN_ID
# Импортируем функции из базы данных
from database.db import get_stats, add_balance, get_all_users

# !!! ВОТ ЗДЕСЬ БЫЛА ОШИБКА. ТЕПЕРЬ ИМЯ ПРАВИЛЬНОЕ:
admin_router = Router()

logger = logging.getLogger(__name__)

# --- Состояния (шаги диалога) ---
class AdminState(StatesGroup):
    waiting_for_id = State()  # Ждем ID пользователя
    waiting_for_amount = State()  # Ждем сумму денег
    waiting_for_broadcast = State()  # Ждем текст рассылки

# --- Проверка: Админ или нет? ---
def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

# 👑 ГЛАВНОЕ МЕНЮ АДМИНА
@admin_router.message(Command("admin"))
@admin_router.message(F.text == "👑 Админ-панель")
async def admin_menu(message: types.Message) -> None:
    if not is_admin(message.from_user.id):
        return # Игнорируем чужаков

    # Получаем статистику
    try:
        users_count = await get_stats()
    except Exception as e:
        logger.error("Ошибка БД при получении статистики: %s", e)
        users_count = "Ошибка БД"

    text = (
        f"👑 **Админ-Панель**\n\n"
        f"👥 Пользователей в боте: `{users_count}`\n"
        f"⚙️ Система работает исправно."
    )

    # Создаем кнопки
    kb = InlineKeyboardBuilder()
    kb.button(text="💰 Выдать деньги", callback_data="admin_money")
    kb.button(text="📢 Рассылка", callback_data="admin_broadcast")
    kb.button(text="❌ Закрыть", callback_data="close_admin")
    kb.adjust(1) # Кнопки в один столбик

    await message.answer(text, reply_markup=kb.as_markup(), parse_mode="Markdown")

# --- ЛОГИКА ВЫДАЧИ ДЕНЕГ ---
@admin_router.callback_query(F.data == "admin_money")
async def start_money(call: types.CallbackQuery, state: FSMContext) -> None:
    await call.message.edit_text("👤 Введите **Telegram ID** пользователя (цифрами):")
    await state.set_state(AdminState.waiting_for_id)

@admin_router.message(AdminState.waiting_for_id)
async def get_user_id(message: types.Message, state: FSMContext) -> None:
    if not message.text.isdigit():
        await message.answer("❌ Это не цифры. Попробуйте снова.")
        return
    
    await state.update_data(target_id=int(message.text))
    await message.answer("💵 Введите **сумму** пополнения (в рублях):")
    await state.set_state(AdminState.waiting_for_amount)

@admin_router.message(AdminState.waiting_for_amount)
async def give_money(message: types.Message, state: FSMContext) -> None:
    if not message.text.isdigit():
        await message.answer("❌ Сумма должна быть числом.")
        return

    data = await state.get_data()
    target_id = data['target_id']
    amount = int(message.text)

    try:
        await add_balance(target_id, amount)
        await message.answer(f"✅ Успешно! Пользователю `{target_id}` начислено `{amount}₽`.")
        
        # Попробуем уведомить пользователя
        try:
            await message.bot.send_message(target_id, f"🎁 Администратор пополнил ваш баланс на {amount}₽!")
        except Exception as e:
            logger.warning("Не удалось отправить уведомление пользователю %s: %s", target_id, e)

    except Exception as e:
        await message.answer(f"❌ Ошибка базы данных: {e}")

    await state.clear()

# --- ЛОГИКА РАССЫЛКИ ---
@admin_router.callback_query(F.data == "admin_broadcast")
async def start_broadcast(call: types.CallbackQuery, state: FSMContext) -> None:
    await call.message.edit_text(
        "📢 **Режим рассылки**\n\n"
        "Отправьте сообщение (текст, фото или видео), которое получат ВСЕ пользователи.",
        parse_mode="Markdown"
    )
    await state.set_state(AdminState.waiting_for_broadcast)

@admin_router.message(AdminState.waiting_for_broadcast)
async def process_broadcast(message: types.Message, state: FSMContext) -> None:
    users = await get_all_users()
    count = 0
    
    status_msg = await message.answer(f"⏳ Начинаю рассылку на {len(users)} человек...")

    for user_id in users:
        try:
            # Копируем сообщение админа и шлем пользователю
            await message.copy_to(user_id)
            count += 1
        except Exception as e:
            logger.warning("Рассылка: не удалось отправить пользователю %s: %s", user_id, e)
            continue # Если юзер заблокировал бота, пропускаем

    await status_msg.edit_text(f"✅ Рассылка завершена!\nПолучили: {count} из {len(users)}")
    await state.clear()

# --- ЗАКРЫТЬ ---
@admin_router.callback_query(F.data == "close_admin")
async def close(call: types.CallbackQuery) -> None:
    await call.message.delete()
