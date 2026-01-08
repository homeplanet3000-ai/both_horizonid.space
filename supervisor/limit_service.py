import time
import re
import os
import sqlite3
import requests
import datetime
import threading
from loguru import logger
from dotenv import load_dotenv

# Загружаем настройки
env_file = os.getenv("ENV_FILE", "/opt/marzban/.env")
load_dotenv(env_file)

# --- КОНФИГУРАЦИЯ ---
LOG_FILE = os.getenv("LOG_FILE", "/var/lib/marzban/access.log")
DB_FILE = os.getenv("DB_FILE", "/app/policeman.db")
PANEL_URL = os.getenv("PANEL_URL", "http://marzban:8000")
ADMIN_USER = os.getenv("SUDO_USERNAME")
ADMIN_PASS = os.getenv("SUDO_PASSWORD")
BOT_TOKEN = os.getenv("BOT_TOKEN")
LOG_RETRY_SECONDS = float(os.getenv("LOG_RETRY_SECONDS", "2"))

# Правила
WINDOW_SECONDS = 600  # 10 минут
MAX_IPS = 2           # Больше 2-х (то есть 3 и выше) = Нарушение
BAN_TIME = 3600       # 1 час (в секундах)
MAX_STRIKES = 3       # 3 нарушения = Вечный бан

# Хранилище в памяти: { 'user_id': [ (ip, timestamp), ... ] }
active_sessions = {}

# --- БАЗА ДАННЫХ (Для истории нарушений) ---
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS violations (
                username TEXT PRIMARY KEY,
                strikes INTEGER DEFAULT 0,
                last_ban_time INTEGER DEFAULT 0
            )
        """)

def add_strike(username):
    """Добавляет нарушение и возвращает их количество"""
    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.execute("SELECT strikes FROM violations WHERE username = ?", (username,))
        row = cur.fetchone()
        strikes = (row[0] + 1) if row else 1
        
        conn.execute("""
            INSERT INTO violations (username, strikes, last_ban_time) 
            VALUES (?, ?, ?) 
            ON CONFLICT(username) DO UPDATE SET 
                strikes = strikes + 1,
                last_ban_time = ?
        """, (username, strikes, int(time.time()), int(time.time())))
        return strikes

# --- API MARZBAN ---
def get_token():
    try:
        resp = requests.post(
            f"{PANEL_URL}/api/admin/token",
            data={"username": ADMIN_USER, "password": ADMIN_PASS},
            timeout=10
        )
        if resp.status_code == 200:
            return resp.json().get("access_token")
    except Exception as e:
        logger.error(f"Login failed: {e}")
    return None

def ban_user(username, reason_msg):
    token = get_token()
    if not token:
        logger.warning("Skip ban: no Marzban token")
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    # Ставим статус disabled
    requests.put(
        f"{PANEL_URL}/api/user/{username}",
        json={"status": "disabled"},
        headers=headers,
        timeout=10
    )
    
    # Шлем уведомление в Telegram
    if not BOT_TOKEN:
        logger.warning("BOT_TOKEN is missing; cannot notify user %s", username)
        return
    try:
        tg_id = username.replace("user_", "")
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": tg_id, "text": reason_msg, "parse_mode": "HTML"},
            timeout=10
        )
    except Exception as e:
        logger.warning("Failed to notify user %s: %s", username, e)

def unban_user(username):
    token = get_token()
    if not token:
        logger.warning("Skip unban: no Marzban token")
        return
    headers = {"Authorization": f"Bearer {token}"}
    # Возвращаем active
    requests.put(
        f"{PANEL_URL}/api/user/{username}",
        json={"status": "active"},
        headers=headers,
        timeout=10
    )
    
    if not BOT_TOKEN:
        logger.warning("BOT_TOKEN is missing; cannot notify user %s", username)
        return
    try:
        tg_id = username.replace("user_", "")
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={
                "chat_id": tg_id,
                "text": "✅ <b>Доступ восстановлен!</b>\nПожалуйста, соблюдайте правила (макс 2 устройства).",
                "parse_mode": "HTML"
            },
            timeout=10
        )
    except Exception as e:
        logger.warning("Failed to notify user %s: %s", username, e)

# --- ФОНОВЫЙ ПРОЦЕСС РАЗБАНА ---
def unban_worker():
    while True:
        time.sleep(60)
        now = int(time.time())
        with sqlite3.connect(DB_FILE) as conn:
            # Ищем тех, кого пора разбанить (если страйков < 3)
            cursor = conn.execute(
                "SELECT username FROM violations WHERE last_ban_time < ? AND strikes < ?", 
                (now - BAN_TIME, MAX_STRIKES)
            )
            users_to_unban = cursor.fetchall()
            
            for (user,) in users_to_unban:
                # Проверяем, забанен ли он сейчас, чтобы не спамить
                # (Упрощенно просто шлем разбан)
                logger.info(f"Разбаниваю {user}...")
                unban_user(user)
                # Сбрасываем время бана, чтобы не разбанить снова
                conn.execute("UPDATE violations SET last_ban_time = 0 WHERE username = ?", (user,))

# --- ОСНОВНОЙ ЛОГЕР ---
def validate_required_settings():
    missing = []
    if not ADMIN_USER:
        missing.append("SUDO_USERNAME")
    if not ADMIN_PASS:
        missing.append("SUDO_PASSWORD")
    if missing:
        logger.error("Missing required environment variables: %s", ", ".join(missing))
        raise SystemExit("Required environment variables are missing or invalid.")
    if not BOT_TOKEN:
        logger.warning("BOT_TOKEN missing; user notifications will be disabled")

def _open_log_file():
    if not os.path.exists(LOG_FILE):
        raise FileNotFoundError(f"Log file not found: {LOG_FILE}")
    if not os.access(LOG_FILE, os.R_OK):
        raise PermissionError(f"Log file is not readable: {LOG_FILE}")
    return open(LOG_FILE, "r")

def tail_logs():
    logger.info("👮‍♂️ Надзиратель заступил на смену...")

    file_handle = None
    current_inode = None
    while True:
        if file_handle is None:
            try:
                file_handle = _open_log_file()
                file_handle.seek(0, 2)
                current_inode = os.fstat(file_handle.fileno()).st_ino
                logger.info("Log file opened: %s", LOG_FILE)
            except (FileNotFoundError, PermissionError) as e:
                logger.warning("%s; retrying in %.1f seconds", e, LOG_RETRY_SECONDS)
                time.sleep(LOG_RETRY_SECONDS)
                continue

        line = file_handle.readline()
        if not line:
            try:
                if os.path.exists(LOG_FILE):
                    inode = os.stat(LOG_FILE).st_ino
                    if inode != current_inode:
                        logger.info("Detected log rotation; reopening log file")
                        file_handle.close()
                        file_handle = None
                        continue
            except Exception as e:
                logger.warning("Failed to check log file status: %s", e)
            time.sleep(0.1)
            continue
            
        # Парсим строку лога Xray
        # Пример: ... email: user_12345 ... 192.168.1.1:54321
        if "email:" in line and "accepted" in line:
            try:
                # Извлекаем email (user_id)
                user = re.search(r'email:\s+(\S+)', line).group(1)
                # Извлекаем IP (первая часть адреса tcp:...)
                ip_match = re.search(r'tcp:(\d+\.\d+\.\d+\.\d+)', line)
                if not ip_match: continue
                ip = ip_match.group(1)
                
                now = time.time()
                
                # Инициализация
                if user not in active_sessions:
                    active_sessions[user] = []
                
                # Добавляем IP
                active_sessions[user].append((ip, now))
                
                # Очистка старых записей (> 10 минут)
                active_sessions[user] = [
                    (i, t) for (i, t) in active_sessions[user] 
                    if now - t < WINDOW_SECONDS
                ]
                
                # Считаем уникальные IP
                unique_ips = set(i for i, t in active_sessions[user])
                
                if len(unique_ips) > MAX_IPS:
                    # НАРУШЕНИЕ!
                    strikes = add_strike(user)
                    
                    if strikes < MAX_STRIKES:
                        msg = (
                            f"🚫 <b>ВРЕМЕННАЯ БЛОКИРОВКА (1 час)</b>\n\n"
                            f"Обнаружено {len(unique_ips)} одновременных устройств (Лимит: 2).\n"
                            f"⚠️ Нарушение {strikes} из {MAX_STRIKES}.\n\n"
                            f"Доступ вернется автоматически через час."
                        )
                        logger.warning(f"BAN (TEMP) -> {user} ({strikes} strikes)")
                        ban_user(user, msg)
                    else:
                        msg = (
                            f"⛔️ <b>ПОДПИСКА АННУЛИРОВАНА</b>\n\n"
                            f"Вы нарушили правила 3 раза.\n"
                            f"Ваш аккаунт заблокирован навсегда без возврата средств."
                        )
                        logger.warning(f"BAN (PERM) -> {user}")
                        ban_user(user, msg)
                    
                    # Очищаем сессию, чтобы не банить каждую секунду
                    active_sessions[user] = []
                    
            except Exception as e:
                logger.warning("Failed to process log line: %s", e)

if __name__ == "__main__":
    validate_required_settings()
    init_db()
    # Запускаем поток разбана
    t = threading.Thread(target=unban_worker)
    t.daemon = True
    t.start()
    
    # Запускаем чтение логов
    tail_logs()
