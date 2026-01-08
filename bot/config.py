import json
import logging
import os
from typing import Any, Dict, List
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
MARZBAN_URL = os.getenv("MARZBAN_URL", "http://marzban:8000")
MARZBAN_USERNAME = os.getenv("SUDO_USERNAME")
MARZBAN_PASSWORD = os.getenv("SUDO_PASSWORD")
VLESS_FLOW = os.getenv("VLESS_FLOW", "xtls-rprx-vision")
MARZBAN_TIMEOUT_SECONDS = float(os.getenv("MARZBAN_TIMEOUT_SECONDS", "10"))
MARZBAN_RETRY_COUNT = int(os.getenv("MARZBAN_RETRY_COUNT", "2"))
MARZBAN_RETRY_BACKOFF_SECONDS = float(os.getenv("MARZBAN_RETRY_BACKOFF_SECONDS", "1.5"))
PREFER_MOBILE_VLESS_WS = os.getenv("PREFER_MOBILE_VLESS_WS", "1") == "1"

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

def _validate_server_entry(entry: Dict[str, Any], index: int) -> Dict[str, Any]:
    required_fields = ["id", "name", "marzban_url", "health_check_url"]
    missing = [field for field in required_fields if not entry.get(field)]
    if missing:
        raise ValueError(f"SERVERS_CONFIG[{index}] missing required fields: {', '.join(missing)}")
    if not isinstance(entry["id"], str) or not entry["id"].strip():
        raise ValueError(f"SERVERS_CONFIG[{index}] id must be a non-empty string")
    return entry

def load_servers_config() -> List[Dict[str, Any]]:
    raw = os.getenv("SERVERS_CONFIG")
    if not raw:
        return _DEFAULT_SERVERS
    try:
        data = json.loads(raw)
        if isinstance(data, list) and data:
            validated = []
            seen_ids = set()
            for index, entry in enumerate(data):
                if not isinstance(entry, dict):
                    raise ValueError(f"SERVERS_CONFIG[{index}] must be a JSON object")
                validated_entry = _validate_server_entry(entry, index)
                if validated_entry["id"] in seen_ids:
                    raise ValueError(f"SERVERS_CONFIG contains duplicate id: {validated_entry['id']}")
                seen_ids.add(validated_entry["id"])
                validated.append(validated_entry)
            return validated
    except (json.JSONDecodeError, ValueError) as exc:
        logger.error("Invalid SERVERS_CONFIG: %s", exc)
    return _DEFAULT_SERVERS

SERVERS = load_servers_config()

# --- НАСТРОЙКИ ОПЛАТЫ (AAIO) ---
AAIO_MERCHANT_ID = os.getenv("AAIO_MERCHANT_ID")
AAIO_SECRET_1 = os.getenv("AAIO_SECRET_1")
AAIO_SECRET_2 = os.getenv("AAIO_SECRET_2")
AAIO_API_KEY = os.getenv("AAIO_API_KEY")
PAYMENT_DEFAULT_EMAIL = os.getenv("PAYMENT_DEFAULT_EMAIL")
PAYMENT_TIMEOUT_SECONDS = float(os.getenv("PAYMENT_TIMEOUT_SECONDS", "10"))
PAYMENT_RETRY_COUNT = int(os.getenv("PAYMENT_RETRY_COUNT", "2"))
PAYMENT_RETRY_BACKOFF_SECONDS = float(os.getenv("PAYMENT_RETRY_BACKOFF_SECONDS", "1.5"))

# --- НАСТРОЙКИ CLOUDFLARE ---
CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")
CLOUDFLARE_ZONE_ID = os.getenv("CLOUDFLARE_ZONE_ID")
CLOUDFLARE_RECORD_ID = os.getenv("CLOUDFLARE_RECORD_ID")
CLOUDFLARE_DNS_NAME = os.getenv("CLOUDFLARE_DNS_NAME")
CLOUDFLARE_TIMEOUT_SECONDS = float(os.getenv("CLOUDFLARE_TIMEOUT_SECONDS", "10"))
CLOUDFLARE_RETRY_COUNT = int(os.getenv("CLOUDFLARE_RETRY_COUNT", "2"))
CLOUDFLARE_RETRY_BACKOFF_SECONDS = float(os.getenv("CLOUDFLARE_RETRY_BACKOFF_SECONDS", "1.5"))

# --- НАСТРОЙКИ HEALTH CHECK ---
HEALTHCHECK_INTERVAL_SECONDS = int(os.getenv("HEALTHCHECK_INTERVAL_SECONDS", "300"))
HEALTHCHECK_TIMEOUT_SECONDS = float(os.getenv("HEALTHCHECK_TIMEOUT_SECONDS", "10"))
HEALTHCHECK_LATENCY_WARN_MS = int(os.getenv("HEALTHCHECK_LATENCY_WARN_MS", "200"))
HEALTHCHECK_LATENCY_DOWN_MS = int(os.getenv("HEALTHCHECK_LATENCY_DOWN_MS", "500"))


def validate_required_settings() -> None:
    missing = []
    invalid = []

    required_vars = [
        "BOT_TOKEN",
        "SUDO_ADMIN_ID",
        "SUDO_USERNAME",
        "SUDO_PASSWORD",
    ]
    payment_vars = [
        "AAIO_MERCHANT_ID",
        "AAIO_SECRET_1",
        "AAIO_SECRET_2",
        "AAIO_API_KEY",
    ]
    cloudflare_vars = [
        "CLOUDFLARE_API_TOKEN",
        "CLOUDFLARE_ZONE_ID",
        "CLOUDFLARE_RECORD_ID",
        "CLOUDFLARE_DNS_NAME",
    ]

    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)

    missing_payment = [var for var in payment_vars if not os.getenv(var)]
    missing_cloudflare = [var for var in cloudflare_vars if not os.getenv(var)]

    if _SUDO_ADMIN_ID_RAW:
        try:
            admin_id = int(_SUDO_ADMIN_ID_RAW)
            if admin_id <= 0:
                invalid.append("SUDO_ADMIN_ID must be a positive integer")
        except ValueError:
            invalid.append("SUDO_ADMIN_ID must be a valid integer")

    if missing:
        logger.error("Missing required environment variables: %s", ", ".join(missing))
    if missing_payment:
        logger.warning("Payment environment variables missing: %s", ", ".join(missing_payment))
    if not PAYMENT_DEFAULT_EMAIL:
        logger.warning("PAYMENT_DEFAULT_EMAIL is not set; payment link creation may fail")
    if missing_cloudflare:
        logger.warning("Cloudflare environment variables missing: %s", ", ".join(missing_cloudflare))
    if invalid:
        logger.error("Invalid environment variables: %s", "; ".join(invalid))

    if missing or invalid:
        raise SystemExit("Required environment variables are missing or invalid.")

# --- ЛОГИКА И ЦЕНЫ ---
# Длительность пробного периода (в днях)
TRIAL_DAYS = 1
# Объем пробного периода (в байтах: 1 ГБ = 1073741824)
TRIAL_LIMIT_BYTES = 1073741824 

# --- НАСТРОЙКИ УВЕДОМЛЕНИЙ ---
SUB_ALERT_WINDOW_SECONDS = int(os.getenv("SUB_ALERT_WINDOW_SECONDS", "3600"))
SUB_ALERT_DAYS_3 = int(os.getenv("SUB_ALERT_DAYS_3", "3"))
SUB_ALERT_DAYS_1 = int(os.getenv("SUB_ALERT_DAYS_1", "1"))
TRAFFIC_ALERT_PERCENT = int(os.getenv("TRAFFIC_ALERT_PERCENT", "90"))

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
