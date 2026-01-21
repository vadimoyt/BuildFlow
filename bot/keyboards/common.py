"""Клавиатуры и кнопки для Telegram бота."""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup
from database.models import UserRole, ProjectStage, TransactionCategory


# ============ ГЛАВНОЕ МЕНЮ ============

def main_menu_kb() -> InlineKeyboardMarkup:
    """Главное меню бота."""
    keyboard = [
        [InlineKeyboardButton(text="📂 Мои проекты", callback_data="menu_my_projects")],
        [InlineKeyboardButton(text="➕ Создать проект", callback_data="menu_create_project")],
        [InlineKeyboardButton(text="💰 Добавить расход", callback_data="menu_add_expense")],
        [InlineKeyboardButton(text="📸 Фото отчёт", callback_data="menu_photo_report")],
        [InlineKeyboardButton(text="📊 Отчёт по проекту", callback_data="menu_project_report")],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="menu_settings")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ============ РОЛИ ПОЛЬЗОВАТЕЛЯ ============

def role_selection_kb() -> InlineKeyboardMarkup:
    """Выбор роли при регистрации."""
    keyboard = [
        [InlineKeyboardButton(text="👷 Прораб", callback_data="role_foreman")],
        [InlineKeyboardButton(text="👤 Заказчик", callback_data="role_client")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ============ РАБОТА С ПРОЕКТАМИ ============

def projects_list_kb(projects: list) -> InlineKeyboardMarkup:
    """Список проектов для выбора."""
    keyboard = []
    for project in projects:
        # Формат: "Название (Адрес)"
        text = f"📦 {project.name}"
        keyboard.append([
            InlineKeyboardButton(
                text=text,
                callback_data=f"proj_{project.id}"
            )
        ])
    
    # Кнопка возврата в меню
    keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def project_actions_kb(project_id: int) -> InlineKeyboardMarkup:
    """Меню действий для проекта."""
    keyboard = [
        [InlineKeyboardButton(text="📋 Детали проекта", callback_data=f"proj_details_{project_id}")],
        [InlineKeyboardButton(text="💰 Добавить расход", callback_data=f"proj_add_expense_{project_id}")],
        [InlineKeyboardButton(text="📸 Загрузить фото", callback_data=f"proj_add_photo_{project_id}")],
        [InlineKeyboardButton(text="📊 Отчёт", callback_data=f"proj_report_{project_id}")],
        [InlineKeyboardButton(text="◀️ Вернуться", callback_data="back_to_menu")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ============ КАТЕГОРИИ РАСХОДОВ ============

def expense_category_kb() -> InlineKeyboardMarkup:
    """Выбор категории расходов."""
    keyboard = [
        [InlineKeyboardButton(text="🏗️ Материалы", callback_data="cat_materials")],
        [InlineKeyboardButton(text="👷 Работа", callback_data="cat_labor")],
        [InlineKeyboardButton(text="📦 Прочее", callback_data="cat_other")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def confirm_expense_kb() -> InlineKeyboardMarkup:
    """Подтверждение создания расхода."""
    keyboard = [
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_expense"),
            InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_expense"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ============ ЭТАПЫ ПРОЕКТА ============

def project_stage_kb() -> InlineKeyboardMarkup:
    """Выбор этапа работ."""
    keyboard = [
        [InlineKeyboardButton(text="📋 Эскиз", callback_data="stage_draft")],
        [InlineKeyboardButton(text="⚡ Электрика", callback_data="stage_electric")],
        [InlineKeyboardButton(text="🎨 Отделка", callback_data="stage_finish")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ============ ФОТО ОТЧЁТ ============

def photo_report_actions_kb() -> InlineKeyboardMarkup:
    """Меню для работы с фото."""
    keyboard = [
        [InlineKeyboardButton(text="➕ Добавить ещё", callback_data="add_more_photos")],
        [InlineKeyboardButton(text="✅ Завершить", callback_data="finish_photos")],
        [InlineKeyboardButton(text="◀️ Вернуться", callback_data="back_to_menu")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ============ ПОДТВЕРЖДЕНИЕ ============

def confirm_kb() -> InlineKeyboardMarkup:
    """Кнопки подтверждения."""
    keyboard = [
        [
            InlineKeyboardButton(text="✅ Да", callback_data="confirm_yes"),
            InlineKeyboardButton(text="❌ Нет", callback_data="confirm_no"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def back_to_menu_kb() -> InlineKeyboardMarkup:
    """Кнопка возврата в меню."""
    keyboard = [[InlineKeyboardButton(text="◀️ В главное меню", callback_data="back_to_menu")]]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ============ УДАЛЕНИЕ КЛАВИАТУРЫ ============

def remove_keyboard() -> ReplyKeyboardMarkup:
    """Удалить стандартную клавиатуру."""
    return ReplyKeyboardMarkup(keyboard=[], remove_keyboard=True)


# ============ РАСШИРЕННЫЕ МЕНЮ ============

def project_details_kb(project_id: int) -> InlineKeyboardMarkup:
    """Меню деталей проекта с расширенными опциями."""
    keyboard = [
        [InlineKeyboardButton(text="📊 Статистика расходов", callback_data=f"stat_expenses_{project_id}")],
        [InlineKeyboardButton(text="📈 Прогресс по этапам", callback_data=f"stat_progress_{project_id}")],
        [InlineKeyboardButton(text="💾 История расходов", callback_data=f"history_expenses_{project_id}")],
        [InlineKeyboardButton(text="📷 Галерея фото", callback_data=f"gallery_{project_id}")],
        [InlineKeyboardButton(text="💰 Обновить бюджет", callback_data=f"update_budget_{project_id}")],
        [InlineKeyboardButton(text="◀️ Вернуться", callback_data="back_to_menu")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def stat_menu_kb(project_id: int) -> InlineKeyboardMarkup:
    """Меню статистики."""
    keyboard = [
        [InlineKeyboardButton(text="🔙 Назад к проекту", callback_data=f"proj_details_{project_id}")],
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="back_to_menu")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def settings_menu_kb() -> InlineKeyboardMarkup:
    """Меню настроек."""
    keyboard = [
        [InlineKeyboardButton(text="🔐 Изменить роль", callback_data="settings_change_role")],
        [InlineKeyboardButton(text="ℹ️ О приложении", callback_data="settings_about")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def photo_continue_kb() -> InlineKeyboardMarkup:
    """Меню для продолжения загрузки фото или завершения."""
    keyboard = [
        [InlineKeyboardButton(text="✅ Завершить", callback_data="finish_photos")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ============ ЗАДАЧИ ============

def my_tasks_menu_kb() -> InlineKeyboardMarkup:
    """Меню управления задачами."""
    keyboard = [
        [InlineKeyboardButton(text="📋 Мои задачи", callback_data="tasks_my_tasks")],
        [InlineKeyboardButton(text="➕ Создать задачу", callback_data="tasks_create")],
        [InlineKeyboardButton(text="✅ Утвержденные задачи", callback_data="tasks_approved")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def tasks_list_kb(tasks: list, show_complete_buttons: bool = True) -> InlineKeyboardMarkup:
    """Список задач с кнопками для управления."""
    keyboard = []
    
    for task in tasks:
        task_id = task.get("id")
        title = task.get("title", "Без названия")[:30]
        status = "✅" if task.get("is_completed") else "⭕"
        
        keyboard.append([
            InlineKeyboardButton(text=f"{status} {title}", callback_data=f"task_view_{task_id}")
        ])
        
        if show_complete_buttons and not task.get("is_completed"):
            keyboard.append([
                InlineKeyboardButton(text="✔️ Отметить выполненной", callback_data=f"task_complete_{task_id}"),
                InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"task_delete_{task_id}"),
            ])
    
    keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="tasks_back")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ============ СОГЛАСОВАНИЯ (CHANGE ORDERS) ============

def approval_requests_menu_kb() -> InlineKeyboardMarkup:
    """Меню запросов на согласование."""
    keyboard = [
        [InlineKeyboardButton(text="📋 Ожидающие согласования", callback_data="approvals_pending")],
        [InlineKeyboardButton(text="✅ Одобренные", callback_data="approvals_approved")],
        [InlineKeyboardButton(text="❌ Отклоненные", callback_data="approvals_rejected")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def approve_reject_kb(change_order_id: int) -> InlineKeyboardMarkup:
    """Кнопки для одобрения или отклонения запроса."""
    keyboard = [
        [
            InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_{change_order_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{change_order_id}"),
        ],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="approvals_pending")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def rejection_reason_kb() -> InlineKeyboardMarkup:
    """Выбор причины отклонения."""
    reasons = [
        ("Превышен бюджет", "reason_budget"),
        ("Плохое качество", "reason_quality"),
        ("Другое", "reason_other"),
        ("Отмена", "reason_cancel"),
    ]
    
    keyboard = [[InlineKeyboardButton(text=text, callback_data=data)] for text, data in reasons]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ============ ГЛАВНОЕ МЕНЮ (ОБНОВЛЕННОЕ) ============

def main_menu_kb_v2() -> InlineKeyboardMarkup:
    """Обновленное главное меню с новыми функциями."""
    keyboard = [
        [InlineKeyboardButton(text="📂 Мои проекты", callback_data="menu_my_projects")],
        [InlineKeyboardButton(text="➕ Создать проект", callback_data="menu_create_project")],
        [InlineKeyboardButton(text="💰 Добавить расход", callback_data="menu_add_expense")],
        [InlineKeyboardButton(text="🎙️ Голосовой ввод", callback_data="menu_voice_input")],
        [InlineKeyboardButton(text="📸 Фото отчёт", callback_data="menu_photo_report")],
        [InlineKeyboardButton(text="📊 Отчёт по проекту", callback_data="menu_project_report")],
        [InlineKeyboardButton(text="📋 Мои задачи", callback_data="menu_my_tasks")],
        [InlineKeyboardButton(text="✅ Согласования", callback_data="menu_approvals")],
        [InlineKeyboardButton(text="💾 Экспорт в Excel", callback_data="menu_export_excel")],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="menu_settings")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
