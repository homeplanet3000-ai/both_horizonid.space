import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# --- ОСНОВНЫЕ НАСТРОЙКИ ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("SUDO_ADMIN_ID", 0))
CHANNEL_LOGS = os.getenv("CHANNEL_LOGS")

# !!! ТА САМАЯ ПЕРЕМЕННАЯ, КОТОРОЙ НЕ ХВАТАЛО !!!
SUBSCRIPTION_DOMAIN = "vpn.horizonid.space"

# --- НАСТРОЙКИ MARZBAN ---
# Внутренний адрес в Docker сети
MARZBAN_URL = "http://127.0.0.1:8000"
MARZBAN_USERNAME = os.getenv("SUDO_USERNAME")
MARZBAN_PASSWORD = os.getenv("SUDO_PASSWORD")

# --- НАСТРОЙКИ ОПЛАТЫ (AAIO) ---
AAIO_MERCHANT_ID = os.getenv("AAIO_MERCHANT_ID")
AAIO_SECRET_1 = os.getenv("AAIO_SECRET_1")
AAIO_SECRET_2 = os.getenv("AAIO_SECRET_2")
AAIO_API_KEY = os.getenv("AAIO_API_KEY")

# --- ЛОГИКА И ЦЕНЫ ---
# Длительность пробного периода (в днях)
TRIAL_DAYS = 1
# Объем пробного периода (в байтах: 1 ГБ = 1073741824)
TRIAL_LIMIT_BYTES = 1073741824 

# Тарифы: key = кол-во месяцев, value = цена в рублях
TARIFFS = {
    1: 125,
    2: 230,
    3: 320,
    6: 600,
    12: 1100
}

# Реферальная система
REFERRAL_BONUS_PERCENT = 10  # 10% от суммы пополнения реферала
