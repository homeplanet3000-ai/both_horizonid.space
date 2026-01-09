import os
import time
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv
from loguru import logger

env_file = os.getenv("ENV_FILE", "/opt/marzban/.env")
load_dotenv(env_file)

HEARTBEAT_INTERVAL_SECONDS = float(os.getenv("HEARTBEAT_INTERVAL_SECONDS", "60"))
HEARTBEAT_TEST_URL = os.getenv("HEARTBEAT_TEST_URL", "https://api.ipify.org?format=json")
HEARTBEAT_PROXY_URL = os.getenv("HEARTBEAT_PROXY_URL")
HEARTBEAT_TIMEOUT_SECONDS = float(os.getenv("HEARTBEAT_TIMEOUT_SECONDS", "10"))

TELEGRAM_BOT_TOKEN = os.getenv("HEARTBEAT_TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("HEARTBEAT_TELEGRAM_CHAT_ID")


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def send_telegram(message: str) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram settings missing; cannot send heartbeat alert")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        requests.post(
            url,
            json={"chat_id": TELEGRAM_CHAT_ID, "text": message},
            timeout=HEARTBEAT_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        logger.warning("Failed to send heartbeat alert: %s", exc)


def check_vpn() -> None:
    proxies = None
    if HEARTBEAT_PROXY_URL:
        proxies = {"http": HEARTBEAT_PROXY_URL, "https": HEARTBEAT_PROXY_URL}

    resp = requests.get(
        HEARTBEAT_TEST_URL,
        timeout=HEARTBEAT_TIMEOUT_SECONDS,
        proxies=proxies,
    )
    resp.raise_for_status()


def main() -> None:
    logger.info("Starting VPN heartbeat checks against %s", HEARTBEAT_TEST_URL)
    last_ok = None

    while True:
        ok = True
        error_message = ""
        try:
            check_vpn()
        except requests.RequestException as exc:
            ok = False
            error_message = str(exc)

        if ok:
            if last_ok is False:
                send_telegram(f"✅ VPN heartbeat восстановлен ({_now_utc()}).")
            logger.debug("Heartbeat OK")
        else:
            if last_ok is not False:
                send_telegram(
                    "🚨 VPN heartbeat failed.\n"
                    f"Time: {_now_utc()}\n"
                    f"Error: {error_message}"
                )
            logger.warning("Heartbeat failed: %s", error_message)

        last_ok = ok
        time.sleep(HEARTBEAT_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
