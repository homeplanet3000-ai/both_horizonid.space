import logging
import os
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

import aiosqlite

DB_NAME = "bot_users.db"
DB_TIMEOUT_SECONDS = float(os.getenv("DB_TIMEOUT_SECONDS", "10"))

# Путь к базе данных: поднимаемся на уровень выше папки database
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), DB_NAME)

# --- ГЛАВНАЯ ФУНКЦИЯ ПОДКЛЮЧЕНИЯ ---
@asynccontextmanager
async def get_db() -> AsyncIterator[aiosqlite.Connection]:
    """Контекстный менеджер для соединения с базой."""
    db = await aiosqlite.connect(DB_PATH, timeout=DB_TIMEOUT_SECONDS)
    try:
        # Включаем ограничения и режим WAL на каждом соединении
        await db.execute("PRAGMA foreign_keys = ON;")
        await db.execute("PRAGMA journal_mode=WAL;")
        yield db
    finally:
        await db.close()

# --- ИНИЦИАЛИЗАЦИЯ БАЗЫ ---
logger = logging.getLogger(__name__)


async def init_db() -> None:
    async with get_db() as db:
        await db.execute("PRAGMA foreign_keys = ON;")
        await db.execute("PRAGMA journal_mode=WAL;")
        
        # 1. Таблица пользователей
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE,
                username TEXT,
                full_name TEXT,
                balance REAL DEFAULT 0,
                referrer_id INTEGER DEFAULT 0,
                sub_expire INTEGER DEFAULT 0,
                trial_used INTEGER DEFAULT 0,
                server_id TEXT DEFAULT 'default',
                alert_sub_3d_sent INTEGER DEFAULT 0,
                alert_sub_1d_sent INTEGER DEFAULT 0,
                alert_traffic_90_sent INTEGER DEFAULT 0,
                registered_at INTEGER
            )
        """)

        # 2. Таблица платежей
        await db.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT UNIQUE,
                user_id INTEGER,
                amount REAL,
                months INTEGER,
                server_id TEXT DEFAULT 'default',
                status TEXT DEFAULT 'pending',
                created_at INTEGER
            )
        """)

        # 4. Таблица подписок (несколько подписок на пользователя)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                server_id TEXT DEFAULT 'default',
                link TEXT,
                data_limit_bytes INTEGER DEFAULT 0,
                expire_at INTEGER DEFAULT 0,
                is_trial INTEGER DEFAULT 0,
                created_at INTEGER
            )
        """)

        # 3. Таблица транзакций
        await db.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount REAL,
                type TEXT, 
                comment TEXT,
                created_at INTEGER
            )
        """)
        
        await db.commit()

        await _ensure_column(db, "users", "server_id", "TEXT DEFAULT 'default'")
        await _ensure_column(db, "payments", "server_id", "TEXT DEFAULT 'default'")
        await _ensure_column(db, "users", "alert_sub_3d_sent", "INTEGER DEFAULT 0")
        await _ensure_column(db, "users", "alert_sub_1d_sent", "INTEGER DEFAULT 0")
        await _ensure_column(db, "users", "alert_traffic_90_sent", "INTEGER DEFAULT 0")
        await _ensure_column(db, "users", "referrer_id", "INTEGER DEFAULT 0")
        await _ensure_index(db, "users_user_id_idx", "users", "user_id")
        await _ensure_index(db, "payments_order_id_idx", "payments", "order_id")
        await _ensure_index(db, "subscriptions_user_expire_idx", "subscriptions", "user_id, expire_at")

async def _ensure_column(db: aiosqlite.Connection, table: str, column: str, column_def: str) -> None:
    cursor = await db.execute(f"PRAGMA table_info({table})")
    existing = await cursor.fetchall()
    if any(row[1] == column for row in existing):
        return
    await db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_def}")


async def _ensure_index(db: aiosqlite.Connection, name: str, table: str, columns: str) -> None:
    await db.execute(f"CREATE INDEX IF NOT EXISTS {name} ON {table} ({columns})")

# --- ФУНКЦИИ ДЛЯ ПОЛЬЗОВАТЕЛЯ ---

async def add_user(user_id: int, username: str, full_name: str, referrer_id: int = 0) -> bool:
    async with get_db() as db:
        try:
            await db.execute(
                """
                INSERT INTO users (user_id, username, full_name, referrer_id, registered_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = excluded.username,
                    full_name = excluded.full_name,
                    referrer_id = CASE
                        WHEN users.referrer_id = 0 THEN excluded.referrer_id
                        ELSE users.referrer_id
                    END
                """,
                (user_id, username, full_name, referrer_id, int(time.time())),
            )
            await db.commit()
            return True
        except Exception as e:
            logger.warning("Не удалось добавить пользователя %s: %s", user_id, e)
            return False

async def get_user(user_id: int) -> Optional[aiosqlite.Row]:
    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            return await cursor.fetchone()

# --- ФУНКЦИИ ТРАНЗАКЦИЙ ---

async def add_transaction(user_id: int, amount: float, t_type: str, comment: str) -> None:
    """Запись в историю операций (использовать только вне других транзакций)"""
    async with get_db() as db:
        await db.execute(
            "INSERT INTO transactions (user_id, amount, type, comment, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, t_type, comment, int(time.time()))
        )
        await db.commit()

# --- ФУНКЦИИ ПОДПИСОК ---

async def add_subscription(
    user_id: int,
    server_id: str,
    link: str,
    data_limit_bytes: int,
    expire_at: int,
    is_trial: bool,
) -> None:
    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO subscriptions (user_id, server_id, link, data_limit_bytes, expire_at, is_trial, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, server_id, link, data_limit_bytes, expire_at, int(is_trial), int(time.time()))
        )
        await db.commit()

async def get_active_subscriptions(user_id: int) -> list[aiosqlite.Row]:
    now = int(time.time())
    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM subscriptions WHERE user_id = ? AND expire_at > ? ORDER BY expire_at DESC",
            (user_id, now)
        ) as cursor:
            return await cursor.fetchall()

async def get_expired_subscriptions() -> list[aiosqlite.Row]:
    now = int(time.time())
    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT s.*
            FROM subscriptions s
            WHERE s.expire_at > 0
              AND s.expire_at <= ?
              AND NOT EXISTS (
                SELECT 1 FROM subscriptions s2
                WHERE s2.user_id = s.user_id
                  AND s2.expire_at > ?
              )
            """,
            (now, now)
        ) as cursor:
            return await cursor.fetchall()

async def expire_user_subscription(user_id: int, subscription_id: int) -> None:
    """Помечает подписку истекшей и сбрасывает статус пользователя."""
    async with get_db() as db:
        await db.execute("BEGIN IMMEDIATE")
        await db.execute("UPDATE subscriptions SET expire_at = 0 WHERE id = ?", (subscription_id,))
        await db.execute(
            "UPDATE users SET sub_expire = 0, alert_sub_3d_sent = 0, alert_sub_1d_sent = 0, "
            "alert_traffic_90_sent = 0 WHERE user_id = ?",
            (user_id,),
        )
        await db.commit()

# --- ФУНКЦИИ ДЛЯ АДМИНКИ ---

async def get_stats() -> int:
    """Возвращает количество пользователей"""
    async with get_db() as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cursor:
            result = await cursor.fetchone()
            return result[0] if result else 0

async def add_balance(user_id: int, amount: float) -> None:
    """Пополнение баланса через админку"""
    async with get_db() as db:
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        await db.execute(
            "INSERT INTO transactions (user_id, amount, type, comment, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, "admin_deposit", "Пополнение админом", int(time.time()))
        )
        await db.commit()

async def get_all_users() -> list[int]:
    """Получает всех пользователей для рассылки"""
    async with get_db() as db:
        async with db.execute("SELECT user_id FROM users") as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]
