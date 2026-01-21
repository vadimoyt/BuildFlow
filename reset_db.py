#!/usr/bin/env python3
"""
Скрипт для полной переинициализации базы данных.
Используется только при разработке для сброса схемы.
"""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from database.session import reset_db

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    print("\n" + "="*70)
    print("🔄 ПОЛНАЯ ПЕРЕИНИЦИАЛИЗАЦИЯ БД")
    print("="*70)
    print("\n⚠️ Все данные будут удалены!\n")
    
    confirmation = input("Вы уверены? Введите 'yes': ").strip().lower()
    
    if confirmation == "yes":
        print("\n🔧 Сбрасываю и пересоздаю БД...")
        try:
            reset_db()
            print("\n" + "="*70)
            print("✅ БД успешно переинициализирована!")
            print("="*70)
        except Exception as exc:
            print(f"\n❌ Ошибка: {exc}")
            exit(1)
    else:
        print("\n❌ Отменено")
