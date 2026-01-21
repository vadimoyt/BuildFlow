#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BuildFlow v3.0 - Скрипт запуска с информативным логированием
"""

import asyncio
import logging
import os
import sys
from io import TextIOWrapper

from dotenv import load_dotenv

# Установка UTF-8 кодировки для вывода на Windows
if sys.platform.startswith('win'):
    sys.stdout = TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Загружаем переменные окружения
load_dotenv()

# Проверяем BOT_TOKEN перед запуском
bot_token = os.getenv("BOT_TOKEN")
if not bot_token:
    print("❌ ОШИБКА: BOT_TOKEN не установлен в .env файле!")
    print("ℹ️  Добавьте в .env: BOT_TOKEN=your_token")
    sys.exit(1)

print("=" * 70)
print("🚀 BuildFlow v3.0")
print("=" * 70)
print(f"✅ BOT_TOKEN найден: {bot_token[:10]}...***")
print(f"✅ Python версия: {sys.version.split()[0]}")
print("=" * 70)

# Теперь импортируем остальное
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.handlers.base import router as base_router
from bot.handlers.tasks_approvals import router as tasks_approvals_router
from bot.handlers.voice_input import router as voice_input_router
from database.session import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Главная функция запуска бота."""
    logger.info("🔄 Инициализация базы данных...")
    init_db()
    logger.info("✅ База данных инициализирована")

    logger.info("🤖 Создание бота...")
    bot = Bot(token=bot_token, parse_mode=ParseMode.HTML)
    dp = Dispatcher(storage=MemoryStorage())
    logger.info("✅ Бот создан")

    logger.info("🛣️  Регистрация обработчиков...")
    dp.include_router(base_router)
    dp.include_router(tasks_approvals_router)
    dp.include_router(voice_input_router)
    logger.info("✅ Все обработчики зарегистрированы")

    print("\n" + "=" * 70)
    print("✅ BuildFlow v3.0 ГОТОВ К РАБОТЕ!")
    print("=" * 70)
    print("📌 Бот слушает команды из Telegram")
    print("📌 Откройте Telegram и нажмите /start")
    print("📌 Для остановки нажмите Ctrl+C")
    print("=" * 70 + "\n")

    logger.info("🚀 Начинаем polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n" + "=" * 70)
        logger.info("⛔ Бот остановлен пользователем (Ctrl+C)")
        print("=" * 70)
    except SystemExit:
        logger.info("⛔ Бот завершил работу")
    except Exception as e:
        print("\n" + "=" * 70)
        logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {e}", exc_info=True)
        print("=" * 70)
        sys.exit(1)
