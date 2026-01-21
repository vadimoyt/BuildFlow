#!/usr/bin/env python3
"""
BuildFlow v3.0 - Проверка целостности и готовности
"""

import os
import sys
from pathlib import Path

def check_files():
    """Проверить что все необходимые файлы присутствуют."""
    print("📁 Проверка файлов...")
    
    required_files = {
        "main.py": "Точка входа",
        ".env.example": "Шаблон конфигурации",
        "requirements.txt": "Зависимости",
        "database/models.py": "Модели БД",
        "database/crud.py": "CRUD операции",
        "database/session.py": "Подключение БД",
        "bot/handlers/base.py": "Основные обработчики",
        "bot/handlers/voice_input.py": "Голосовой ввод (v3.0)",
        "bot/handlers/tasks_approvals.py": "Задачи и согласования (v3.0)",
        "bot/keyboards/common.py": "Клавиатуры",
        "bot/utils.py": "Утилиты",
        "bot/excel_export.py": "Excel экспорт (v3.0)",
        "setup_alembic.py": "Инициализация миграций (v3.0)",
        "V3_FEATURES.md": "Документация v3.0",
        "INSTALL.md": "Руководство установки",
        "README.md": "Главный README",
    }
    
    missing = []
    for file, desc in required_files.items():
        path = Path(file)
        if path.exists():
            size = path.stat().st_size
            print(f"  ✅ {file} ({size} bytes) - {desc}")
        else:
            print(f"  ❌ {file} - ОТСУТСТВУЕТ")
            missing.append(file)
    
    return len(missing) == 0, missing


def check_imports():
    """Проверить что все импорты работают."""
    print("\n📦 Проверка импортов...")
    
    try:
        print("  ✓ Импорт aiogram...")
        import aiogram
        print(f"    ✅ aiogram {aiogram.__version__}")
    except ImportError as e:
        print(f"    ❌ Ошибка: {e}")
        return False
    
    try:
        print("  ✓ Импорт sqlalchemy...")
        import sqlalchemy
        print(f"    ✅ sqlalchemy {sqlalchemy.__version__}")
    except ImportError as e:
        print(f"    ❌ Ошибка: {e}")
        return False
    
    try:
        print("  ✓ Импорт python-dotenv...")
        import dotenv
        print(f"    ✅ python-dotenv")
    except ImportError as e:
        print(f"    ❌ Ошибка: {e}")
        return False
    
    try:
        print("  ✓ Импорт pydantic...")
        import pydantic
        print(f"    ✅ pydantic {pydantic.__version__}")
    except ImportError as e:
        print(f"    ❌ Ошибка: {e}")
        return False
    
    print("  ✓ Проверка v3.0 пакетов...")
    
    optional = {
        "openai": "Для голосового ввода",
        "pandas": "Для Excel",
        "openpyxl": "Для Excel",
        "alembic": "Для миграций",
    }
    
    for pkg, desc in optional.items():
        try:
            __import__(pkg)
            print(f"    ✅ {pkg} - {desc}")
        except ImportError:
            print(f"    ⚠️  {pkg} - не установлен ({desc})")
    
    return True


def check_config():
    """Проверить конфигурацию .env."""
    print("\n⚙️  Проверка конфигурации...")
    
    env_file = Path(".env")
    env_example = Path(".env.example")
    
    if env_file.exists():
        print("  ✅ Файл .env найден")
        with open(env_file) as f:
            content = f.read()
            if "BOT_TOKEN" in content:
                print("  ✅ BOT_TOKEN установлен")
            else:
                print("  ⚠️  BOT_TOKEN не установлен")
            
            if "OPENAI_API_KEY" in content:
                print("  ✅ OPENAI_API_KEY установлен (голосовой ввод)")
            else:
                print("  ⚠️  OPENAI_API_KEY не установлен (опционально)")
    else:
        print("  ⚠️  Файл .env не найден")
        if env_example.exists():
            print("  ℹ️  Скопируйте .env.example в .env и отредактируйте")
        return False
    
    return True


def check_database():
    """Проверить БД."""
    print("\n🗄️  Проверка базы данных...")
    
    if Path("buildflow.db").exists():
        print("  ✅ SQLite БД найдена (buildflow.db)")
    else:
        print("  ℹ️  SQLite БД будет создана при первом запуске")
    
    return True


def check_models():
    """Проверить что модели v3.0 присутствуют."""
    print("\n📊 Проверка моделей БД...")
    
    try:
        from database.models import (
            User, Project, Transaction, ProgressPhoto,
            ChangeOrder, Task, TransactionStatus
        )
        print("  ✅ User модель")
        print("  ✅ Project модель")
        print("  ✅ Transaction модель")
        print("  ✅ ProgressPhoto модель")
        print("  ✅ ChangeOrder модель (v3.0)")
        print("  ✅ Task модель (v3.0)")
        print("  ✅ TransactionStatus enum (v3.0)")
        return True
    except ImportError as e:
        print(f"  ❌ Ошибка импорта: {e}")
        return False


def check_handlers():
    """Проверить что обработчики v3.0 присутствуют."""
    print("\n🎛️  Проверка обработчиков...")
    
    try:
        print("  ✓ Импорт base handlers...")
        from bot.handlers import base
        print("  ✅ bot.handlers.base")
        
        print("  ✓ Импорт voice handlers (v3.0)...")
        from bot.handlers import voice_input
        print("  ✅ bot.handlers.voice_input (v3.0)")
        
        print("  ✓ Импорт tasks/approvals handlers (v3.0)...")
        from bot.handlers import tasks_approvals
        print("  ✅ bot.handlers.tasks_approvals (v3.0)")
        
        return True
    except ImportError as e:
        print(f"  ❌ Ошибка импорта: {e}")
        return False


def check_utils():
    """Проверить что утилиты v3.0 присутствуют."""
    print("\n🛠️  Проверка утилит...")
    
    try:
        from bot import utils
        
        if hasattr(utils, 'transcribe_audio_whisper'):
            print("  ✅ transcribe_audio_whisper (v3.0)")
        else:
            print("  ❌ transcribe_audio_whisper не найдена")
        
        if hasattr(utils, 'parse_expense_from_voice'):
            print("  ✅ parse_expense_from_voice (v3.0)")
        else:
            print("  ❌ parse_expense_from_voice не найдена")
        
        if hasattr(utils, 'format_change_order_notification'):
            print("  ✅ format_change_order_notification (v3.0)")
        else:
            print("  ❌ format_change_order_notification не найдена")
        
        if hasattr(utils, 'format_task_notification'):
            print("  ✅ format_task_notification (v3.0)")
        else:
            print("  ❌ format_task_notification не найдена")
        
        return True
    except ImportError as e:
        print(f"  ❌ Ошибка импорта: {e}")
        return False


def main():
    """Главная функция проверки."""
    print("=" * 60)
    print("🎉 BuildFlow v3.0 - Проверка целостности")
    print("=" * 60)
    
    results = {
        "Файлы": check_files(),
        "Импорты": check_imports(),
        "Конфигурация": check_config(),
        "БД": check_database(),
        "Модели": check_models(),
        "Обработчики": check_handlers(),
        "Утилиты": check_utils(),
    }
    
    print("\n" + "=" * 60)
    print("📋 ИТОГИ ПРОВЕРКИ")
    print("=" * 60)
    
    for name, result in results.items():
        if isinstance(result, tuple):
            status = result[0]
            status_str = "✅ ОК" if status else "❌ ОШИБКА"
            print(f"{name}: {status_str}")
            if len(result) > 1 and result[1]:  # Если есть missing
                for item in result[1]:
                    print(f"  - {item}")
        else:
            status = result
            status_str = "✅ ОК" if status else "❌ ОШИБКА"
            print(f"{name}: {status_str}")
    
    all_ok = all(r[0] if isinstance(r, tuple) else r for r in results.values())
    
    print("\n" + "=" * 60)
    if all_ok:
        print("✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ!")
        print("\nДля запуска бота выполните:")
        print("  python main.py")
    else:
        print("❌ НАЙДЕНЫ ПРОБЛЕМЫ")
        print("\nПожалуйста, установите зависимости:")
        print("  pip install -r requirements.txt")
    print("=" * 60)
    
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
