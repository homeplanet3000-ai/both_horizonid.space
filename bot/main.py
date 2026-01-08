import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, validate_required_settings
from database import db
from handlers import user, pay, admin
from services.scheduler import scheduler_loop
from services.servers import health_check_loop
from services.http import close_session

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

async def main() -> None:
    logger.info("🚀 Запуск бота...")

    validate_required_settings()
    
    # 1. Инициализация БД
    await db.init_db()
    logger.info("✅ База данных подключена")

    # 2. Настройка бота
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # 3. Регистрация роутеров (важен порядок!)
    dp.include_router(admin.admin_router) # Сначала админ
    dp.include_router(pay.pay_router)     # Потом оплата
    dp.include_router(user.user_router)   # В конце юзер

    # 4. Удаление вебхука и старт
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Запуск планировщика в фоне (проверка подписок)
    asyncio.create_task(scheduler_loop(bot))
    asyncio.create_task(health_check_loop())
    
    try:
        await dp.start_polling(bot)
    except Exception:
        logger.exception("Ошибка при запуске")
    finally:
        await close_session()
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен")
