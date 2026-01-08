import aiosqlite
import time
import os

DB_NAME = "bot_users.db"

# Путь к базе данных: поднимаемся на уровень выше папки database
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), DB_NAME)

# --- ГЛАВНАЯ ФУНКЦИЯ ПОДКЛЮЧЕНИЯ ---
def get_db():
    """Контекстный менеджер для соединения"""
    return aiosqlite.connect(DB_PATH)

# --- ИНИЦИАЛИЗАЦИЯ БАЗЫ ---
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
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
                status TEXT DEFAULT 'pending',
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

# --- ФУНКЦИИ ДЛЯ ПОЛЬЗОВАТЕЛЯ ---

async def add_user(user_id, username, full_name, referrer_id=0):
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute(
                "INSERT INTO users (user_id, username, full_name, referrer_id, registered_at) VALUES (?, ?, ?, ?, ?)",
                (user_id, username, full_name, referrer_id, int(time.time()))
            )
            await db.commit()
            return True
        except:
            return False

async def get_user(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            return await cursor.fetchone()

# --- ФУНКЦИИ ТРАНЗАКЦИЙ ---

async def add_transaction(user_id, amount, t_type, comment):
    """Запись в историю операций (использовать только вне других транзакций)"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO transactions (user_id, amount, type, comment, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, t_type, comment, int(time.time()))
        )
        await db.commit()

# --- ФУНКЦИИ ДЛЯ АДМИНКИ ---

async def get_stats():
    """Возвращает количество пользователей"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cursor:
            result = await cursor.fetchone()
            return result[0] if result else 0

async def add_balance(user_id, amount):
    """Пополнение баланса через админку"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        await db.execute(
            "INSERT INTO transactions (user_id, amount, type, comment, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, "admin_deposit", "Пополнение админом", int(time.time()))
        )
        await db.commit()

async def get_all_users():
    """Получает всех пользователей для рассылки"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM users") as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]
