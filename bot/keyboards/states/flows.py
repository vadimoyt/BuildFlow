"""FSM состояния для диалогов бота."""

from aiogram.fsm.state import StatesGroup, State


class RegistrationState(StatesGroup):
    """Состояния регистрации пользователя."""
    waiting_for_role = State()  # Ожидание выбора роли


class ProjectManagementState(StatesGroup):
    """Состояния управления проектами."""
    waiting_for_project_name = State()  # Ввод названия
    waiting_for_project_address = State()  # Ввод адреса
    waiting_for_project_budget = State()  # Ввод бюджета
    choosing_project = State()  # Выбор проекта
    updating_budget = State()  # Обновление бюджета


class AddExpenseState(StatesGroup):
    """Состояния добавления расхода."""
    choosing_project = State()  # Выбор проекта
    waiting_for_amount = State()  # Ввод суммы
    waiting_for_category = State()  # Выбор категории
    waiting_for_description = State()  # Ввод описания
    waiting_for_photo = State()  # Загрузка фото (опционально)
    confirming = State()  # Подтверждение


class PhotoReportState(StatesGroup):
    """Состояния фото отчёта."""
    choosing_project = State()  # Выбор проекта
    choosing_stage = State()  # Выбор этапа работ
    waiting_for_photos = State()  # Загрузка фото


class ProjectReportState(StatesGroup):
    """Состояния отчёта по проекту."""
    choosing_project = State()  # Выбор проекта


class SettingsState(StatesGroup):
    """Состояния настроек пользователя."""
    viewing_settings = State()  # Просмотр настроек
    changing_role = State()  # Изменение роли
    editing_profile = State()  # Редактирование профиля

