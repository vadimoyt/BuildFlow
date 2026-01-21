#!/usr/bin/env python
"""Скрипт для инициализации Alembic миграций."""

import os
import sys
import subprocess

def setup_alembic():
    """Инициализировать Alembic для проекта."""
    
    print("🔧 Инициализация Alembic...")
    
    # Проверяем наличие Alembic
    try:
        result = subprocess.run(["alembic", "--version"], capture_output=True, text=True)
        print(f"✅ Alembic найден: {result.stdout.strip()}")
    except FileNotFoundError:
        print("❌ Alembic не найден. Установите: pip install alembic")
        sys.exit(1)
    
    # Инициализируем migrations folder если его нет
    if not os.path.exists("migrations"):
        print("📁 Создание папки migrations...")
        subprocess.run(["alembic", "init", "migrations"], check=True)
    else:
        print("✅ Папка migrations уже существует")
    
    # Обновляем alembic.ini если нужно
    ini_path = "alembic.ini"
    if os.path.exists(ini_path):
        print("✅ alembic.ini найден")
    
    # Обновляем env.py
    env_py = "migrations/env.py"
    if os.path.exists(env_py):
        print("✅ migrations/env.py найден")
        
        # Добавляем импорт моделей
        with open(env_py, "r", encoding="utf-8") as f:
            content = f.read()
        
        if "from database.models import Base" not in content:
            print("📝 Обновляем migrations/env.py...")
            # Вставляем импорт после других импортов
            import_line = "from database.models import Base"
            content = content.replace(
                "from logging.config import fileConfig",
                f"from logging.config import fileConfig\n{import_line}"
            )
            
            with open(env_py, "w", encoding="utf-8") as f:
                f.write(content)
            
            print("✅ migrations/env.py обновлен")
    
    print("\n✅ Alembic инициализирован!")
    print("\nДля создания миграции выполните:")
    print("  alembic revision --autogenerate -m 'Описание изменений'")
    print("\nДля применения миграций выполните:")
    print("  alembic upgrade head")
    print("\nДля отката выполните:")
    print("  alembic downgrade -1")

if __name__ == "__main__":
    setup_alembic()
