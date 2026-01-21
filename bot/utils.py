"""Утилиты форматирования и локализации."""

import logging
import json
import os
from datetime import datetime
from decimal import Decimal
from typing import Any

try:
    from openai import OpenAI, APIError
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

logger = logging.getLogger(__name__)


# Форматирование валют и чисел
CURRENCY = "BYN"  # Валюта: BYN (белорусский рубль) или RUB (рубль)


def format_price(amount: float | Decimal) -> str:
    """Форматировать цену с валютой."""
    return f"{float(amount):,.2f} {CURRENCY}".replace(",", " ")


def format_datetime(dt: datetime) -> str:
    """Форматировать дату и время в формат ДД.ММ.ГГГГ ЧЧ:ММ."""
    return dt.strftime("%d.%m.%Y %H:%M")


def format_date(dt: datetime) -> str:
    """Форматировать дату в формат ДД.ММ.ГГГГ."""
    return dt.strftime("%d.%m.%Y")


def format_transaction_category(category: str) -> str:
    """Переводить категорию на русский."""
    translations = {
        "materials": "🏗️ Материалы",
        "labor": "👷 Работа",
        "other": "📦 Прочее",
    }
    return translations.get(category, category)


def format_project_stage(stage: str) -> str:
    """Переводить этап на русский."""
    translations = {
        "draft": "📋 Эскиз",
        "electric": "⚡ Электрика",
        "finish": "🎨 Отделка",
    }
    return translations.get(stage, stage)


def format_user_role(role: str) -> str:
    """Переводить роль на русский."""
    translations = {
        "foreman": "👷 Прораб",
        "client": "👤 Заказчик",
        "admin": "🔧 Администратор",
    }
    return translations.get(role, role)


def format_project_report(report: dict) -> str:
    """Форматировать отчёт по проекту в красивый текст."""
    if not report:
        return "⚠️ Проект не найден"
    
    return (
        f"📦 <b>{report['name']}</b>\n"
        f"📍 Адрес: <code>{report['address']}</code>\n"
        f"📅 Дата создания: {format_date(report['created_at'])}\n"
        f"\n"
        f"💰 <b>Бюджет:</b>\n"
        f"  План: {format_price(report['budget_plan'])}\n"
        f"  Потрачено: {format_price(report['budget_spent'])}\n"
        f"  Осталось: {format_price(report['budget_remaining'])}\n"
        f"\n"
        f"📊 <b>Статистика:</b>\n"
        f"  Операций: {report['transactions_count']}\n"
        f"  Фотографий: {report['photos_count']}"
    )


def format_expense_summary(amount: float, category: str, description: str | None) -> str:
    """Форматировать сводку по расходу перед подтверждением."""
    summary = (
        f"💰 <b>Проверьте данные расхода:</b>\n"
        f"Сумма: {format_price(amount)}\n"
        f"Категория: {format_transaction_category(category)}\n"
    )
    if description:
        summary += f"Описание: <code>{description}</code>\n"
    return summary


def is_valid_amount(text: str) -> tuple[bool, float | None]:
    """Проверить, является ли текст валидной суммой."""
    try:
        amount = float(text.replace(",", "."))
        if amount <= 0:
            return False, None
        if amount > 999999.99:
            return False, None
        return True, amount
    except ValueError:
        return False, None


def is_valid_project_name(text: str) -> bool:
    """Проверить, является ли текст валидным названием проекта."""
    return 1 <= len(text) <= 255


def is_valid_project_address(text: str) -> bool:
    """Проверить, является ли текст валидным адресом."""
    return 5 <= len(text) <= 512


def format_expense_statistics(stats: dict) -> str:
    """Форматировать статистику расходов по категориям."""
    return (
        f"📊 <b>Расходы по категориям:</b>\n\n"
        f"🏗️ Материалы: {format_price(stats.get('materials', 0))}\n"
        f"👷 Работа: {format_price(stats.get('labor', 0))}\n"
        f"📦 Прочее: {format_price(stats.get('other', 0))}\n\n"
        f"<b>Всего:</b> {format_price(sum(stats.values()))}"
    )


def format_progress_stats(stages: dict) -> str:
    """Форматировать прогресс по этапам."""
    return (
        f"📈 <b>Прогресс работ:</b>\n\n"
        f"📋 Эскиз: {stages.get('draft', 0)} фото\n"
        f"⚡ Электрика: {stages.get('electric', 0)} фото\n"
        f"🎨 Отделка: {stages.get('finish', 0)} фото\n\n"
        f"<b>Всего:</b> {sum(stages.values())} фотографий"
    )


def get_budget_status(budget_plan: float, budget_spent: float) -> str:
    """Получить статус бюджета (статус-бар)."""
    if budget_plan == 0:
        return "📊 Бюджет не установлен"
    
    percent = (budget_spent / budget_plan) * 100
    
    if percent <= 50:
        return f"✅ Хорошо ({percent:.0f}%)"
    elif percent <= 80:
        return f"⚠️ Внимание ({percent:.0f}%)"
    elif percent <= 100:
        return f"🔴 Критично ({percent:.0f}%)"
    else:
        return f"🚨 Превышен ({percent:.0f}%)"


def format_expense_entry(amount: float, category: str, description: str | None, created_at: datetime) -> str:
    """Форматировать одну запись расхода для истории."""
    desc_text = f"\n   Примечание: <code>{description}</code>" if description else ""
    return (
        f"💰 {format_price(amount)}\n"
        f"   Категория: {format_transaction_category(category)}\n"
        f"   Дата: {format_datetime(created_at)}"
        f"{desc_text}"
    )


def format_expense_by_date(expenses_dict: dict) -> str:
    """Форматировать расходы по датам."""
    if not expenses_dict:
        return "📭 Расходов нет"
    
    text = "📅 <b>Расходы по дням:</b>\n\n"
    for date, amount in sorted(expenses_dict.items(), reverse=True):
        text += f"{date}: {format_price(amount)}\n"
    
    total = sum(expenses_dict.values())
    text += f"\n<b>Итого:</b> {format_price(total)}"
    return text


def format_project_settings(project_name: str, project_address: str, budget: float, role: str) -> str:
    """Форматировать информацию проекта для настроек."""
    return (
        f"📋 <b>Информация проекта:</b>\n\n"
        f"📦 Название: <code>{project_name}</code>\n"
        f"📍 Адрес: <code>{project_address}</code>\n"
        f"💰 Бюджет: {format_price(budget)}\n"
        f"👤 Ваша роль: {format_user_role(role)}"
    )


# ============ VOICE & AI PROCESSING ============

async def transcribe_audio_whisper(audio_file_path: str) -> str | None:
    """Транскрибировать аудиофайл используя Whisper API."""
    if not HAS_OPENAI:
        logger.error("OpenAI не установлен. Установите: pip install openai")
        return None
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY не установлен в .env файле")
        return None
    
    try:
        client = OpenAI(api_key=api_key)
        logger.info(f"📝 Транскрибирование аудио: {audio_file_path}")
        
        with open(audio_file_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="ru"
            )
        
        text = transcript.text
        logger.info(f"✅ Успешно транскрибировано: {text[:100]}...")
        return text
        
    except APIError as e:
        logger.error(f"❌ Ошибка Whisper API: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Ошибка при транскрибировании: {e}")
        return None


async def parse_expense_from_voice(text: str) -> dict[str, Any] | None:
    """
    Парсировать расход из текста голосового сообщения используя GPT.
    
    Возвращает словарь вида:
    {
        "amount": 100.50,
        "category": "materials",  # или "labor", "other"
        "description": "Купил цемент",
        "confidence": 0.95
    }
    """
    if not HAS_OPENAI:
        logger.error("OpenAI не установлен")
        return None
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY не установлен")
        return None
    
    try:
        client = OpenAI(api_key=api_key)
        
        prompt = f"""Проанализируй следующий текст расхода и извлеки информацию о расходе.

Текст: {text}

Вернись в формате JSON с полями:
- amount: число (сумма в BYN)
- category: "materials" (материалы), "labor" (работа) или "other" (прочее)
- description: строка (описание)
- confidence: число от 0 до 1 (уверенность в парсинге)

Если не получается распарсить, вернись с confidence: 0 и опиши проблему.

Только JSON, без дополнительного текста."""

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Ты помощник для парсинга расходов. Отвечай только валидным JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=500
        )
        
        result_text = response.choices[0].message.content
        logger.info(f"🤖 GPT ответ: {result_text}")
        
        result = json.loads(result_text)
        
        # Валидация
        if result.get("confidence", 0) < 0.5:
            logger.warning(f"⚠️ Низкая уверенность в парсинге: {result.get('confidence')}")
            return None
        
        logger.info(f"✅ Успешно распарсено: {result}")
        return result
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ GPT вернул невалидный JSON: {e}")
        return None
    except APIError as e:
        logger.error(f"❌ Ошибка GPT API: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Ошибка при парсинге: {e}")
        return None


def format_change_order_notification(
    transaction_id: int,
    amount: float,
    category: str,
    description: str,
    requester_name: str,
) -> str:
    """Форматировать уведомление о новом запросе согласования."""
    return (
        f"📋 <b>Новый запрос на согласование!</b>\n\n"
        f"👷 <b>От:</b> {requester_name}\n"
        f"💰 <b>Сумма:</b> {format_price(amount)}\n"
        f"📂 <b>Категория:</b> {format_transaction_category(category)}\n"
        f"📝 <b>Описание:</b> {description}\n\n"
        f"Нажмите кнопку ниже для одобрения или отклонения"
    )


def format_task_notification(
    task_id: int,
    title: str,
    assigned_by: str,
) -> str:
    """Форматировать уведомление о новой задаче."""
    return (
        f"📌 <b>Вам назначена новая задача!</b>\n\n"
        f"📝 <b>Задача:</b> {title}\n"
        f"👤 <b>Назначил:</b> {assigned_by}\n\n"
        f"Перейдите в раздел 'Мои задачи' для просмотра всех задач"
    )


def format_task_list(tasks: list[dict]) -> str:
    """Форматировать список задач."""
    if not tasks:
        return "📭 <b>Нет активных задач</b>"
    
    text = "📋 <b>Мои задачи:</b>\n\n"
    for i, task in enumerate(tasks, 1):
        status = "✅" if task.get("is_completed") else "⭕"
        due_date = task.get("due_date")
        due_text = f" (до {format_date(due_date)})" if due_date else ""
        assigned_to = f" (назначена: {task.get('assigned_to_name', 'N/A')})" if task.get("assigned_to_id") else ""
        
        text += f"{status} <b>{i}. {task.get('title', 'Без названия')}</b>{due_text}{assigned_to}\n"
        if task.get("description"):
            text += f"   {task['description']}\n"
        text += "\n"
    
    return text