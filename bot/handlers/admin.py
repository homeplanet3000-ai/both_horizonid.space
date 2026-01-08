from aiogram import Router, F, types, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
import os

# Импортируем функции из базы данных
from database.db import get_stats, add_balance, get_all_users

# !!! ВОТ ЗДЕСЬ БЫЛА ОШИБКА. ТЕПЕРЬ ИМЯ ПРАВИЛЬНОЕ:
admin_router = Router()

# Получаем ID админа из переменных окружения
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

# --- Состояния (шаги диалога) ---
class AdminState(StatesGroup):
    waiting_for_id = State()      # Ждем ID пользователя
    waiting_for_amount = State()  # Ждем сумму денег
    waiting_for_broadcast = State() # Ждем текст рассылки

# --- Проверка: Админ или нет? ---
def is_admin(user_id):
    return user_id == ADMIN_ID

# 👑 ГЛАВНОЕ МЕНЮ АДМИНА
@admin_router.message(Command("admin"))
async def admin_menu(message: types.Message):
    if not is_admin(message.from_user.id):
        return # Игнорируем чужаков

    # Получаем статистику
    try:
        users_count = await get_stats()
    except:
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
async def start_money(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_text("👤 Введите **Telegram ID** пользователя (цифрами):")
    await state.set_state(AdminState.waiting_for_id)

@admin_router.message(AdminState.waiting_for_id)
async def get_user_id(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Это не цифры. Попробуйте снова.")
        return
    
    await state.update_data(target_id=int(message.text))
    await message.answer("💵 Введите **сумму** пополнения (в рублях):")
    await state.set_state(AdminState.waiting_for_amount)

@admin_router.message(AdminState.waiting_for_amount)
async def give_money(message: types.Message, state: FSMContext):
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
        except:
            pass 

    except Exception as e:
        await message.answer(f"❌ Ошибка базы данных: {e}")

    await state.clear()

# --- ЛОГИКА РАССЫЛКИ ---
@admin_router.callback_query(F.data == "admin_broadcast")
async def start_broadcast(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_text(
        "📢 **Режим рассылки**\n\n"
        "Отправьте сообщение (текст, фото или видео), которое получат ВСЕ пользователи.",
        parse_mode="Markdown"
    )
    await state.set_state(AdminState.waiting_for_broadcast)

@admin_router.message(AdminState.waiting_for_broadcast)
async def process_broadcast(message: types.Message, state: FSMContext):
    users = await get_all_users()
    count = 0
    
    status_msg = await message.answer(f"⏳ Начинаю рассылку на {len(users)} человек...")

    for user_id in users:
        try:
            # Копируем сообщение админа и шлем пользователю
            await message.copy_to(user_id)
            count += 1
        except:
            continue # Если юзер заблокировал бота, пропускаем

    await status_msg.edit_text(f"✅ Рассылка завершена!\nПолучили: {count} из {len(users)}")
    await state.clear()

# --- ЗАКРЫТЬ ---
@admin_router.callback_query(F.data == "close_admin")
async def close(call: types.CallbackQuery):
    await call.message.delete()
