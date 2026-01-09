import datetime
import logging
import time
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, CommandObject

from database import db
from services.marzban import marzban_api
from services.servers import get_active_server, get_server
from keyboards import reply, inline
from config import TRIAL_DAYS, TRIAL_LIMIT_BYTES
from utils.misc import generate_qr
from utils.text import escape_html

user_router = Router()
logger = logging.getLogger(__name__)

# ==========================================
# 🚀 START & MAIN MENU
# ==========================================

@user_router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject) -> None:
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    full_name = message.from_user.full_name
    
    referrer_id = 0
    args = command.args
    if args and args.isdigit():
        candidate_id = int(args)
        if candidate_id != user_id:
            referrer_id = candidate_id

    # БД создаст запись, если юзера нет
    await db.add_user(user_id, username, full_name, referrer_id)
    
    text = (
        f"👋 <b>Привет, {escape_html(full_name)}!</b>\n\n"
        f"🌐 <b>Horizon VPN</b> — это свобода, скорость и анонимность.\n"
        f"Мы используем протоколы <b>VLESS + Reality</b>, которые невозможно отследить.\n\n"
        f"👇 <b>Что вы хотите сделать?</b>"
    )
    
    await message.answer(text, reply_markup=reply.main_menu(user_id), parse_mode="HTML")

# ==========================================
# 👤 USER PROFILE
# ==========================================

@user_router.message(F.text == "👤 Мой профиль")
async def show_profile(message: Message) -> None:
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    
    if not user:
        await message.answer("⚠️ Ошибка профиля. Нажмите /start")
        return

    # Защита от пустых значений
    sub_expire = user['sub_expire'] if user['sub_expire'] is not None else 0
    balance = user['balance'] if user['balance'] is not None else 0.0
    now = int(time.time())
    
    if sub_expire > now:
        # --- ПОДПИСКА АКТИВНА ---
        server_id = user["server_id"] if user["server_id"] else "default"
        server = get_server(server_id)
        base_url = server.get("marzban_url") if server else None
        user_info = await marzban_api.get_user_info(f"user_{user_id}", base_url=base_url)
        key_link = marzban_api.extract_link(user_info)
        used_bytes = user_info.get("used_traffic") if user_info else None
        limit_bytes = user_info.get("data_limit") if user_info else None
        usage_line = ""
        if used_bytes is not None and limit_bytes:
            used_gb = used_bytes / (1024 ** 3)
            limit_gb = limit_bytes / (1024 ** 3)
            percent = (used_bytes / limit_bytes) * 100 if limit_bytes else 0
            usage_line = f"📊 Трафик: <b>{used_gb:.2f}/{limit_gb:.2f} ГБ</b> ({percent:.0f}%)\n"
        active_subs = await db.get_active_subscriptions(user_id)
        expire_date = datetime.datetime.fromtimestamp(sub_expire).strftime('%d.%m.%Y %H:%M')
        
        subs_lines = []
        for sub in active_subs[:10]:
            expire_date_sub = datetime.datetime.fromtimestamp(sub["expire_at"]).strftime('%d.%m.%Y')
            subs_lines.append(f"• {expire_date_sub} — {sub['server_id']}")
        subs_block = "\n".join(subs_lines) if subs_lines else "—"

        if not key_link and active_subs:
            key_link = active_subs[0].get("link")

        key_display = key_link or "Ключ временно недоступен. Попробуйте позже."

        text = (
            f"👤 <b>Личный кабинет</b>\n"
            f"➖➖➖➖➖➖➖➖➖➖\n"
            f"🆔 ID: <code>{user_id}</code>\n"
            f"💰 Баланс (бонусы): <b>{balance:.2f} ₽</b>\n"
            f"✅ <b>Подписка активна до:</b> {expire_date}\n"
            f"{usage_line}\n"
            f"📦 <b>Подписок:</b> {len(active_subs)}\n"
            f"{subs_block}\n\n"
            f"🔑 <b>Ваш ключ доступа:</b>\n"
            f"<code>{key_display}</code>\n\n"
            f"<i>Нажмите на ключ, чтобы скопировать.</i>"
        )
        
        qr_file = generate_qr(key_link) if key_link else None
        
        if qr_file:
            await message.answer_photo(
                photo=qr_file,
                caption=text,
                parse_mode="HTML",
                reply_markup=inline.profile_menu(sub_active=True, key_link=key_link)
            )
        else:
            await message.answer(
                text,
                parse_mode="HTML",
                reply_markup=inline.profile_menu(sub_active=True, key_link=key_link)
            )
            
    else:
        # --- ПОДПИСКА НЕ АКТИВНА ---
        text = (
            f"👤 <b>Личный кабинет</b>\n"
            f"➖➖➖➖➖➖➖➖➖➖\n"
            f"🆔 ID: <code>{user_id}</code>\n"
            f"💰 Баланс (бонусы): <b>{balance:.2f} ₽</b>\n"
            f"🔴 <b>Статус:</b> Нет активной подписки\n\n"
            f"🎁 Вы можете попробовать <b>бесплатный период</b> или купить подписку."
        )
        await message.answer(text, parse_mode="HTML", reply_markup=inline.profile_menu(sub_active=False))

# ==========================================
# 🎁 TRIAL
# ==========================================

@user_router.callback_query(F.data == "get_trial")
async def activate_trial(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    user = await db.get_user(user_id)
    if not user:
        await callback.answer("⚠️ Пользователь не найден. Нажмите /start", show_alert=True)
        return

    trial_used = user['trial_used'] if user['trial_used'] is not None else 0
    sub_expire = user['sub_expire'] if user['sub_expire'] is not None else 0

    if trial_used == 1:
        await callback.answer("⚠️ Вы уже использовали пробный период!", show_alert=True)
        return
    
    if sub_expire > int(time.time()):
        await callback.answer("✅ У вас уже есть активная подписка!", show_alert=True)
        return

    await callback.message.answer("⏳ <b>Активирую тестовый доступ...</b>", parse_mode="HTML")
    
    active_server = get_active_server()
    server_id = active_server["id"] if active_server else "default"
    base_url = active_server.get("marzban_url") if active_server else None
    key_link = await marzban_api.create_or_update_user(user_id, TRIAL_LIMIT_BYTES, base_url=base_url)
    
    if not key_link:
        await callback.message.answer("❌ Ошибка сервера VPN. Попробуйте позже.")
        return

    new_expire = int(time.time()) + (TRIAL_DAYS * 86400)
    
    try:
        async with db.get_db() as conn:
            await conn.execute(
                "UPDATE users SET sub_expire = ?, trial_used = 1, server_id = ?, "
                "alert_sub_3d_sent = 0, alert_sub_1d_sent = 0, alert_traffic_90_sent = 0 "
                "WHERE user_id = ?",
                (new_expire, server_id, user_id)
            )
            await conn.commit()
        await db.add_subscription(
            user_id=user_id,
            server_id=server_id,
            link=key_link,
            data_limit_bytes=TRIAL_LIMIT_BYTES,
            expire_at=new_expire,
            is_trial=True
        )
    except Exception as exc:
        logger.exception("Ошибка при активации тестового периода для пользователя %s: %s", user_id, exc)
        await callback.message.answer("❌ Не удалось сохранить тестовый доступ. Попробуйте позже.")
        return
    
    text = (
        f"🎁 <b>Тестовый период активирован!</b>\n"
        f"⏳ Срок: <b>{TRIAL_DAYS} день</b>\n"
        f"📊 Лимит: <b>1 ГБ</b>\n\n"
        f"🔑 <b>Ваш ключ:</b>\n<code>{key_link}</code>"
    )
    qr_file = generate_qr(key_link)
    
    await callback.message.delete()
    await callback.message.answer_photo(
        qr_file, 
        caption=text, 
        parse_mode="HTML",
        reply_markup=inline.profile_menu(sub_active=True, key_link=key_link)
    )

# ==========================================
# 📚 INSTRUCTIONS & INFO
# ==========================================

@user_router.message(F.text == "📱 Инструкция")
async def show_instructions_main(message: Message) -> None:
    await message.answer("👇 <b>Выберите ваше устройство:</b>", reply_markup=inline.instructions_menu(), parse_mode="HTML")

@user_router.callback_query(F.data == "instr_main")
async def show_instructions_cb(callback: CallbackQuery) -> None:
    if callback.message.photo:
        await callback.message.delete()
        await callback.message.answer("👇 <b>Выберите ваше устройство:</b>", reply_markup=inline.instructions_menu(), parse_mode="HTML")
    else:
        await callback.message.edit_text("👇 <b>Выберите ваше устройство:</b>", reply_markup=inline.instructions_menu(), parse_mode="HTML")

@user_router.callback_query(F.data.startswith("instr_"))
async def show_device_instruction(callback: CallbackQuery) -> None:
    device = callback.data.split("_")[1]
    
    texts = {
        "ios": (
            "🍏 <b>Инструкция для iOS (iPhone / iPad)</b>\n\n"
            "1️⃣ <b>Скачайте приложение:</b>\n"
            "• <a href='https://apps.apple.com/us/app/v2box-v2ray-client/id6446814690'>V2Box</a> (Рекомендуем ✅)\n"
            "• Или <i>Streisand</i> / <i>Shadowrocket</i> ($).\n\n"
            "2️⃣ <b>Скопируйте ключ</b> доступа в боте.\n"
            "3️⃣ Откройте <b>V2Box</b>. Приложение предложит добавить ключ. Нажмите <b>Import</b>.\n"
            "4️⃣ Нажмите переключатель для соединения. Готово! 🚀"
        ),
        "android": (
            "🤖 <b>Инструкция для Android</b>\n\n"
            "1️⃣ <b>Скачайте приложение:</b>\n"
            "• <a href='https://play.google.com/store/apps/details?id=com.v2ray.ang'>v2rayNG</a> (Google Play)\n"
            "• Или <a href='https://github.com/hiddify/hiddify-next/releases'>Hiddify Next</a>.\n\n"
            "2️⃣ <b>Скопируйте ключ</b> в боте.\n"
            "3️⃣ Откройте <b>v2rayNG</b>, нажмите ➕ → <b>Импорт из буфера</b>.\n"
            "4️⃣ Нажмите кнопку <b>V</b> (подключиться). Готово! 🚀"
        ),
        "win": (
            "💻 <b>Инструкция для Windows</b>\n\n"
            "1️⃣ Скачайте <b>Hiddify Next</b>:\n"
            "<a href='https://github.com/hiddify/hiddify-next/releases/latest'>🔗 Скачать с GitHub (Setup.exe)</a>\n\n"
            "2️⃣ Установите и запустите.\n"
            "3️⃣ Скопируйте ключ. В программе нажмите <b>+</b> → <b>Add from Clipboard</b>.\n"
            "4️⃣ Нажмите большую кнопку <b>Connect</b>. 🌍"
        ),
        "mac": (
            "🍎 <b>Инструкция для macOS</b>\n\n"
            "1️⃣ Скачайте <b>V2Box</b> из AppStore.\n"
            "2️⃣ Скопируйте ключ доступа в боте.\n"
            "3️⃣ Откройте приложение, подтвердите импорт.\n"
            "4️⃣ Запустите подключение переключателем."
        )
    }
    
    text = texts.get(device, "Ошибка выбора устройства.")
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=inline.back_btn("instr_main"), disable_web_page_preview=True)

@user_router.message(F.text == "🤝 Партнерка")
async def show_referral(message: Message) -> None:
    user_id = message.from_user.id
    bot_info = await message.bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
    
    async with db.get_db() as conn:
        cursor = await conn.execute("SELECT COUNT(*) FROM users WHERE referrer_id = ?", (user_id,))
        count_res = await cursor.fetchone()
        ref_count = count_res[0] if count_res else 0
        
        cursor = await conn.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        bal_res = await cursor.fetchone()
        balance = bal_res[0] if bal_res else 0.0

    text = (
        f"🤝 <b>Партнерская программа</b>\n\n"
        f"Приглашайте друзей и получайте <b>10%</b> от их пополнений!\n\n"
        f"🔗 <b>Ваша ссылка:</b>\n<code>{ref_link}</code>\n\n"
        f"📊 <b>Статистика:</b>\n"
        f"👥 Приглашено: <b>{ref_count} чел.</b>\n"
        f"💰 Ваш баланс: <b>{balance:.2f} ₽</b>"
    )
    
    await message.answer(text, parse_mode="HTML", reply_markup=inline.back_btn("close"))

@user_router.callback_query(F.data == "referral_info")
async def show_referral_cb(callback: CallbackQuery) -> None:
    await callback.message.delete()
    await show_referral(callback.message)

@user_router.callback_query(F.data == "rules")
async def show_rules(callback: CallbackQuery) -> None:
    text = (
        "📜 <b>ПОЛЬЗОВАТЕЛЬСКОЕ СОГЛАШЕНИЕ (ОФЕРТА)</b>\n\n"
        "<b>1. Общие положения</b>\n"
        "1.1. Оплачивая услуги, вы соглашаетесь с правилами.\n\n"
        "<b>2. Запреты</b>\n"
        "⛔️ Спам, кардинг, DDOS, распространение вредоносного ПО.\n"
        "⛔️ Передача ключей третьим лицам.\n"
        "⛔️ Превышение лимита устройств (макс. 2).\n\n"
        "<b>3. Возврат</b>\n"
        "Возврат только при тех. неисправности в течение 24ч."
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=inline.back_btn("open_tariffs"))

@user_router.message(F.text == "🆘 Поддержка")
async def support_info(message: Message) -> None:
    text = (
        "📬 <b>Техническая поддержка</b>\n\n"
        "Вопросы по оплате или настройке:\n\n"
        "👨‍💻 Админ: @ITENZORU\n"
        "⏰ Время работы: 10:00 - 22:00 (МСК)"
    )
    await message.answer(text, parse_mode="HTML")

@user_router.message(F.text == "🧠 Blueprint")
async def show_blueprint(message: Message) -> None:
    text = (
        "🧠 <b>The System Architect Mindset (The Blueprint)</b>\n"
        "<i>\"The system must survive if I get hit by a bus. It must scale if 100,000 users join tomorrow.\"</i>\n\n"
        "<b>Decoupling (Frontend vs. Backend):</b>\n"
        "• <b>Frontend:</b> The Telegram Bot (Python/Go). It handles buttons, payments, and user support. It never touches the traffic.\n"
        "• <b>Backend:</b> The VPN Nodes (servers in Netherlands, USA, Germany).\n"
        "<b>The Bridge:</b> An API. When the Bot receives payment, it sends a request to the API → The API talks to the server → "
        "The server generates a key → The Bot delivers the key.\n\n"
        "<b>Infrastructure as Code (IaC):</b>\n"
        "Never configure a server manually.\n"
        "<b>Architect Thought:</b> Cattle, not pets.\n"
        "If a server (IP) gets blocked by a censor, you destroy it and spin up a new one automatically using scripts "
        "(Ansible/Terraform). The user shouldn't even notice.\n\n"
        "<b>Protocol Agnosticism:</b>\n"
        "Censorship evolves. Your tech must evolve.\n"
        "Don't marry one protocol. Build a system that supports WireGuard, VLESS (Reality), and Shadowsocks.\n"
        "<b>Architect Thought:</b> Redundancy. If Protocol A is blocked, the bot automatically suggests Protocol B.\n\n"
        "🧩 <b>The Synthesis: How to execute this today</b>\n"
        "<b>Phase 1: The MVP (Minimum Viable Product)</b>\n"
        "Tech: Python (aiogram), SQLite database, one VP server (VLESS-Reality protocol).\n"
        "Business: Sell to 50 people manually to test pricing.\n"
        "Mindset: \"Does the product work?\"\n\n"
        "<b>Phase 2: The Scalable System</b>\n"
        "Tech: Move to PostgreSQL. Add a panel (like Marzban or 3X-UI) to manage users via API. "
        "Separate the bot code from the server management.\n"
        "Business: Automate crypto payments.\n"
        "Mindset: \"Can I handle 1,000 users without sleeping?\"\n\n"
        "<b>Phase 3: The Super App Ecosystem</b>\n"
        "Tech: Load Balancers. Multiple locations. Smart routing (Netflix goes via US, Instagram via EU).\n"
        "Business: Paid ads. Affiliate partnerships with other Telegram channels.\n"
        "Mindset: \"Total Market Dominance.\""
    )
    await message.answer(text, parse_mode="HTML")

@user_router.callback_query(F.data == "close")
async def close_msg(callback: CallbackQuery) -> None:
    try:
        await callback.message.delete()
    except Exception as e:
        logger.debug("Не удалось удалить сообщение: %s", e)
