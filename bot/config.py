import json
import logging
import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()
logger = logging.getLogger(__name__)

# --- ОСНОВНЫЕ НАСТРОЙКИ ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
_SUDO_ADMIN_ID_RAW = os.getenv("SUDO_ADMIN_ID")
try:
    ADMIN_ID = int(_SUDO_ADMIN_ID_RAW) if _SUDO_ADMIN_ID_RAW is not None else 0
except ValueError:
    ADMIN_ID = 0
CHANNEL_LOGS = os.getenv("CHANNEL_LOGS")

# Домен для замены в выдаваемых ссылках
SUBSCRIPTION_DOMAIN = os.getenv("SUBSCRIPTION_DOMAIN", "vpn.horizonid.space")

# --- НАСТРОЙКИ MARZBAN ---
# Внутренний адрес панели Marzban
MARZBAN_URL = os.getenv("MARZBAN_URL", "http://127.0.0.1:8000")
MARZBAN_USERNAME = os.getenv("SUDO_USERNAME")
MARZBAN_PASSWORD = os.getenv("SUDO_PASSWORD")
VLESS_FLOW = os.getenv("VLESS_FLOW", "xtls-rprx-vision")

_DEFAULT_SERVERS = [
    {
        "id": "default",
        "name": "Основной сервер",
        "flag": "🌍",
        "marzban_url": MARZBAN_URL,
        "public_ip": os.getenv("DEFAULT_SERVER_PUBLIC_IP"),
        "health_check_url": os.getenv("MARZBAN_HEALTHCHECK_URL", f"{MARZBAN_URL}/api/system"),
    }
]

def load_servers_config():
    raw = os.getenv("SERVERS_CONFIG")
    if not raw:
        return _DEFAULT_SERVERS
    try:
        data = json.loads(raw)
        if isinstance(data, list) and data:
            return data
    except json.JSONDecodeError:
        pass
    return _DEFAULT_SERVERS

SERVERS = load_servers_config()

# --- НАСТРОЙКИ ОПЛАТЫ (AAIO) ---
AAIO_MERCHANT_ID = os.getenv("AAIO_MERCHANT_ID")
AAIO_SECRET_1 = os.getenv("AAIO_SECRET_1")
AAIO_SECRET_2 = os.getenv("AAIO_SECRET_2")
AAIO_API_KEY = os.getenv("AAIO_API_KEY")

# --- НАСТРОЙКИ CLOUDFLARE ---
CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")
CLOUDFLARE_ZONE_ID = os.getenv("CLOUDFLARE_ZONE_ID")
CLOUDFLARE_RECORD_ID = os.getenv("CLOUDFLARE_RECORD_ID")
CLOUDFLARE_DNS_NAME = os.getenv("CLOUDFLARE_DNS_NAME")


def validate_required_settings() -> None:
    missing = []
    invalid = []

    required_vars = [
        "BOT_TOKEN",
        "SUDO_ADMIN_ID",
        "SUDO_USERNAME",
        "SUDO_PASSWORD",
        "AAIO_MERCHANT_ID",
        "AAIO_SECRET_1",
        "AAIO_SECRET_2",
        "AAIO_API_KEY",
        "CLOUDFLARE_API_TOKEN",
        "CLOUDFLARE_ZONE_ID",
        "CLOUDFLARE_RECORD_ID",
        "CLOUDFLARE_DNS_NAME",
    ]

    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)

    if _SUDO_ADMIN_ID_RAW:
        try:
            admin_id = int(_SUDO_ADMIN_ID_RAW)
            if admin_id <= 0:
                invalid.append("SUDO_ADMIN_ID must be a positive integer")
        except ValueError:
            invalid.append("SUDO_ADMIN_ID must be a valid integer")

    if missing:
        logger.error("Missing required environment variables: %s", ", ".join(missing))
    if invalid:
        logger.error("Invalid environment variables: %s", "; ".join(invalid))

    if missing or invalid:
        raise SystemExit("Required environment variables are missing or invalid.")

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
