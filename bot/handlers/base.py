"""Основные обработчики команд и событий бота - ПОЛНОСТЬЮ ПЕРЕРАБОТАННАЯ ВЕРСИЯ."""

import logging
from typing import Any

from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from bot.keyboards.common import (
    main_menu_kb, role_selection_kb, projects_list_kb, 
    project_actions_kb, expense_category_kb, project_stage_kb,
    confirm_expense_kb, back_to_menu_kb, confirm_kb,
    project_details_kb, stat_menu_kb, settings_menu_kb,
    photo_continue_kb
)
from bot.keyboards.states import (
    RegistrationState,
    ProjectManagementState,
    AddExpenseState,
    PhotoReportState,
    ProjectReportState,
    SettingsState,
)
from bot.utils import (
    format_price, format_datetime, format_project_report,
    format_expense_summary, format_transaction_category,
    format_project_stage, is_valid_amount, is_valid_project_name,
    is_valid_project_address, format_expense_entry, format_project_settings
)
from database.session import SessionLocal
from database.models import User, UserRole, TransactionCategory, ProjectStage
from database import crud

logger = logging.getLogger(__name__)
router = Router()


# ============ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ============

def get_db_session():
    """Получить сессию БД."""
    return SessionLocal()


def get_user_from_db(tg_id: int) -> User | None:
    """Получить пользователя из БД по Telegram ID."""
    session = get_db_session()
    try:
        return crud.get_user_by_tg_id(session, tg_id)
    finally:
        session.close()


def get_or_create_user_in_db(tg_id: int, name: str | None) -> User:
    """Получить или создать пользователя."""
    session = get_db_session()
    try:
        return crud.get_or_create_user(session, tg_id, name or f"user_{tg_id}")
    except Exception as exc:
        logger.exception("Ошибка при работе с пользователем: %s", exc)
        raise
    finally:
        session.close()


def format_role_display(role: UserRole) -> str:
    """Переводить роль для отображения."""
    return "👷 Прораб" if role == UserRole.FOREMAN else "👤 Заказчик"


# ============ КОМАНДА /START - РЕГИСТРАЦИЯ ============

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    """Обработчик команды /start. Регистрирует пользователя и показывает меню выбора роли."""
    tg_user = message.from_user
    if tg_user is None:
        await message.answer("❌ Не удалось определить пользователя Telegram.")
        return

    try:
        # Создаём или получаем пользователя из БД
        user = get_or_create_user_in_db(tg_id=tg_user.id, name=tg_user.full_name)
        logger.info(f"Пользователь {tg_user.id} запустил бота. Роль: {user.role}")
    except Exception as exc:
        logger.exception(f"Ошибка при регистрации пользователя: {exc}")
        await message.answer("❌ Ошибка при подключении к базе данных. Попробуйте позже.")
        return

    await state.clear()
    
    # Если это первый раз, спрашиваем роль
    user_from_db = get_user_from_db(tg_user.id)
    if user_from_db and user_from_db.role == UserRole.FOREMAN:
        # Уже зарегистрирован, показываем меню
        await message.answer(
            f"👋 Добро пожаловать в <b>BuildFlow v2.0</b>!\n\n"
            f"Вы вошли как: <b>{format_role_display(user_from_db.role)}</b>\n\n"
            f"Выберите действие:",
            reply_markup=main_menu_kb(),
            parse_mode="HTML"
        )
    else:
        # Первый раз - просим выбрать роль
        await state.set_state(RegistrationState.waiting_for_role)
        await message.answer(
            "👋 Добро пожаловать в <b>BuildFlow v2.0</b>!\n\n"
            "Это приложение для управления строительными проектами.\n\n"
            "Пожалуйста, выберите вашу роль:",
            reply_markup=role_selection_kb(),
            parse_mode="HTML"
        )


# ============ РЕГИСТРАЦИЯ - ВЫБОР РОЛИ ============

@router.callback_query(RegistrationState.waiting_for_role, F.data.startswith("role_"))
async def cb_select_role(callback: CallbackQuery, state: FSMContext) -> None:
    """Обработчик выбора роли при регистрации."""
    tg_user = callback.from_user
    
    # Определяем выбранную роль
    role_map = {
        "role_foreman": UserRole.FOREMAN,
        "role_client": UserRole.CLIENT,
    }
    selected_role = role_map.get(callback.data)
    
    if not selected_role:
        await callback.answer("❌ Неизвестная роль", show_alert=True)
        return
    
    # Обновляем роль в БД
    session = get_db_session()
    try:
        user = crud.get_user_by_tg_id(session, tg_user.id)
        if user:
            crud.update_user_role(session, user.id, selected_role)
            logger.info(f"Пользователь {tg_user.id} выбрал роль: {selected_role}")
    except Exception as exc:
        logger.exception(f"Ошибка при обновлении роли: {exc}")
        await callback.answer("❌ Ошибка при сохранении роли", show_alert=True)
        return
    finally:
        session.close()
    
    await state.clear()
    await callback.message.edit_text(
        f"✅ Роль установлена: <b>{format_role_display(selected_role)}</b>\n\n"
        f"Добро пожаловать в BuildFlow!",
        reply_markup=main_menu_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


# ============ ГЛАВНОЕ МЕНЮ ============

@router.callback_query(F.data == "back_to_menu")
async def cb_back_to_menu(callback: CallbackQuery, state: FSMContext) -> None:
    """Вернуться в главное меню."""
    await state.clear()
    await callback.message.edit_text(
        "📋 Главное меню. Выберите действие:",
        reply_markup=main_menu_kb()
    )
    await callback.answer()


# ============ УПРАВЛЕНИЕ ПРОЕКТАМИ ============

@router.callback_query(F.data == "menu_my_projects")
async def cb_my_projects(callback: CallbackQuery, state: FSMContext) -> None:
    """Показать мои проекты."""
    tg_user = callback.from_user
    session = get_db_session()
    
    try:
        # Получаем пользователя и его проекты
        user = crud.get_user_by_tg_id(session, tg_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        projects = crud.get_projects_by_user(session, user.id)
        
        if not projects:
            await callback.message.edit_text(
                "📂 У вас нет проектов.\n\n"
                "Создайте новый проект, чтобы начать.",
                reply_markup=back_to_menu_kb()
            )
        else:
            await state.set_state(ProjectManagementState.choosing_project)
            await callback.message.edit_text(
                f"📂 Ваши проекты ({len(projects)}):\n\n"
                "Выберите проект для открытия:",
                reply_markup=projects_list_kb(projects)
            )
    except Exception as exc:
        logger.exception(f"Ошибка при получении проектов: {exc}")
        await callback.answer("❌ Ошибка при загрузке проектов", show_alert=True)
    finally:
        session.close()
    
    await callback.answer()


# ============ ВЫБОР ПРОЕКТА ИЗ СПИСКА - ИСПРАВЛЕННЫЙ ============

@router.callback_query(ProjectManagementState.choosing_project, F.data.startswith("proj_"))
async def cb_project_list_select(callback: CallbackQuery, state: FSMContext) -> None:
    """Выбор проекта из списка - ПРАВИЛЬНАЯ ОБРАБОТКА."""
    # Парсим: callback_data = "proj_5"
    project_id_str = callback.data.replace("proj_", "")
    
    # Убеждаемся, что это чистое число
    if not project_id_str.isdigit():
        await callback.answer("❌ Ошибка при обработке ID проекта", show_alert=True)
        return
    
    project_id = int(project_id_str)
    session = get_db_session()
    
    try:
        project = crud.get_project(session, project_id)
        if not project:
            await callback.answer("❌ Проект не найден", show_alert=True)
            return
        
        await state.update_data(selected_project_id=project_id)
        
        # Показываем меню действий с проектом
        await callback.message.edit_text(
            f"📦 <b>{project.name}</b>\n"
            f"📍 {project.address}\n"
            f"💰 Бюджет: {format_price(project.budget)}\n\n"
            f"Выберите действие:",
            reply_markup=project_actions_kb(project_id),
            parse_mode="HTML"
        )
    except Exception as exc:
        logger.exception(f"Ошибка при загрузке проекта: {exc}")
        await callback.answer("❌ Ошибка при загрузке проекта", show_alert=True)
    finally:
        session.close()
    
    await callback.answer()


# ============ СОЗДАНИЕ ПРОЕКТА ============

@router.callback_query(F.data == "menu_create_project")
async def cb_create_project_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Начать создание нового проекта."""
    tg_user = callback.from_user
    session = get_db_session()
    
    try:
        user = crud.get_user_by_tg_id(session, tg_user.id)
        if not user or user.role != UserRole.FOREMAN:
            await callback.answer(
                "❌ Только прорабы могут создавать проекты",
                show_alert=True
            )
            return
    finally:
        session.close()
    
    await state.set_state(ProjectManagementState.waiting_for_project_name)
    await callback.message.edit_text(
        "📝 Введите название проекта:\n\n"
        "Например: 'Ремонт офиса на ул. Ленина'"
    )
    await callback.answer()


@router.message(ProjectManagementState.waiting_for_project_name)
async def msg_project_name(message: Message, state: FSMContext) -> None:
    """Получить название проекта."""
    name = message.text
    
    if not name or not is_valid_project_name(name):
        await message.answer(
            "❌ Название должно быть от 1 до 255 символов.\n"
            "Попробуйте снова:"
        )
        return
    
    await state.update_data(project_name=name)
    await state.set_state(ProjectManagementState.waiting_for_project_address)
    await message.answer(
        "📍 Введите адрес объекта:\n\n"
        "Например: 'г. Минск, ул. Ленина, 10-15'"
    )


@router.message(ProjectManagementState.waiting_for_project_address)
async def msg_project_address(message: Message, state: FSMContext) -> None:
    """Получить адрес проекта."""
    address = message.text
    
    if not address or not is_valid_project_address(address):
        await message.answer(
            "❌ Адрес должен быть от 5 до 512 символов.\n"
            "Попробуйте снова:"
        )
        return
    
    await state.update_data(project_address=address)
    await state.set_state(ProjectManagementState.waiting_for_project_budget)
    await message.answer(
        "💰 Введите примерный бюджет проекта (в BYN):\n\n"
        "Например: 50000 или 50000.50"
    )


@router.message(ProjectManagementState.waiting_for_project_budget)
async def msg_project_budget(message: Message, state: FSMContext) -> None:
    """Получить бюджет проекта и создать его."""
    is_valid, amount = is_valid_amount(message.text)
    
    if not is_valid or amount is None:
        await message.answer(
            "❌ Введите корректную сумму (больше 0):\n"
            "Например: 50000 или 50000.50"
        )
        return
    
    # Сохраняем все данные проекта
    data = await state.get_data()
    tg_user = message.from_user
    session = get_db_session()
    
    try:
        user = crud.get_user_by_tg_id(session, tg_user.id)
        if not user:
            await message.answer("❌ Ошибка: пользователь не найден")
            return
        
        # Создаём проект
        project = crud.create_project(
            session,
            name=data["project_name"],
            address=data["project_address"],
            budget=amount,
            owner_id=user.id
        )
        
        logger.info(f"Создан проект {project.id} пользователем {tg_user.id}")
        
        await state.clear()
        await message.answer(
            f"✅ <b>Проект создан!</b>\n\n"
            f"📦 {project.name}\n"
            f"📍 {project.address}\n"
            f"💰 Бюджет: {format_price(project.budget)}\n\n"
            f"Теперь вы можете добавлять расходы и фото!",
            reply_markup=main_menu_kb(),
            parse_mode="HTML"
        )
    except Exception as exc:
        logger.exception(f"Ошибка при создании проекта: {exc}")
        await message.answer("❌ Ошибка при создании проекта. Попробуйте позже.")
    finally:
        session.close()


# ============ ДОБАВЛЕНИЕ РАСХОДА ============

@router.callback_query(F.data == "menu_add_expense")
async def cb_add_expense_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Начать добавление расхода - выбор проекта."""
    tg_user = callback.from_user
    session = get_db_session()
    
    try:
        user = crud.get_user_by_tg_id(session, tg_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        projects = crud.get_projects_by_user(session, user.id)
        
        if not projects:
            await callback.message.edit_text(
                "❌ У вас нет проектов.\n\n"
                "Сначала создайте проект.",
                reply_markup=back_to_menu_kb()
            )
        else:
            await state.set_state(AddExpenseState.choosing_project)
            await callback.message.edit_text(
                f"💰 Выберите проект для добавления расхода ({len(projects)}):",
                reply_markup=projects_list_kb(projects)
            )
    except Exception as exc:
        logger.exception(f"Ошибка при получении проектов: {exc}")
        await callback.answer("❌ Ошибка при загрузке проектов", show_alert=True)
    finally:
        session.close()
    
    await callback.answer()


@router.callback_query(AddExpenseState.choosing_project, F.data.startswith("proj_"))
async def cb_expense_project_selected(callback: CallbackQuery, state: FSMContext) -> None:
    """Проект выбран для добавления расхода."""
    project_id_str = callback.data.replace("proj_", "")
    
    if not project_id_str.isdigit():
        await callback.answer("❌ Ошибка обработки ID проекта", show_alert=True)
        return
    
    project_id = int(project_id_str)
    await state.update_data(expense_project_id=project_id)
    await state.set_state(AddExpenseState.waiting_for_amount)
    await callback.message.edit_text(
        "💰 Введите сумму расхода (в BYN):\n\n"
        "Например: 1250.50"
    )
    await callback.answer()


@router.message(AddExpenseState.waiting_for_amount)
async def msg_expense_amount(message: Message, state: FSMContext) -> None:
    """Получить сумму расхода."""
    is_valid, amount = is_valid_amount(message.text)
    
    if not is_valid or amount is None:
        await message.answer(
            "❌ Введите корректную сумму (больше 0):\n"
            "Например: 1250.50"
        )
        return
    
    await state.update_data(expense_amount=amount)
    await state.set_state(AddExpenseState.waiting_for_category)
    await message.answer(
        "📋 Выберите категорию расхода:",
        reply_markup=expense_category_kb()
    )


@router.callback_query(AddExpenseState.waiting_for_category, F.data.startswith("cat_"))
async def cb_expense_category(callback: CallbackQuery, state: FSMContext) -> None:
    """Выбрана категория расхода."""
    category_map = {
        "cat_materials": TransactionCategory.MATERIALS,
        "cat_labor": TransactionCategory.LABOR,
        "cat_other": TransactionCategory.OTHER,
    }
    category = category_map.get(callback.data)
    
    if not category:
        await callback.answer("❌ Неизвестная категория", show_alert=True)
        return
    
    await state.update_data(expense_category=category.value)
    await state.set_state(AddExpenseState.waiting_for_description)
    await callback.message.edit_text(
        "📝 Введите описание расхода (опционально):\n\n"
        "Или напишите <code>-</code> чтобы пропустить",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AddExpenseState.waiting_for_description)
async def msg_expense_description(message: Message, state: FSMContext) -> None:
    """Получить описание расхода."""
    description = None if message.text == "-" else message.text
    
    await state.update_data(expense_description=description)
    await state.set_state(AddExpenseState.confirming)
    
    # Показываем сводку для подтверждения
    data = await state.get_data()
    summary = format_expense_summary(
        data["expense_amount"],
        data["expense_category"],
        description
    )
    
    await message.answer(
        summary + "\n\nПодтвердить?",
        reply_markup=confirm_expense_kb(),
        parse_mode="HTML"
    )


@router.callback_query(AddExpenseState.confirming, F.data == "confirm_expense")
async def cb_confirm_expense(callback: CallbackQuery, state: FSMContext) -> None:
    """Подтвердить создание расхода."""
    tg_user = callback.from_user
    data = await state.get_data()
    session = get_db_session()
    
    try:
        # Создаём расход в БД
        transaction = crud.create_transaction(
            session,
            project_id=data["expense_project_id"],
            amount=data["expense_amount"],
            category=TransactionCategory(data["expense_category"]),
            description=data["expense_description"],
            photo_url=None
        )
        
        logger.info(f"Создан расход {transaction.id} пользователем {tg_user.id}")
        
        await state.clear()
        await callback.message.edit_text(
            f"✅ <b>Расход добавлен!</b>\n\n"
            f"Сумма: {format_price(transaction.amount)}\n"
            f"Категория: {format_transaction_category(transaction.category.value)}\n"
            f"Дата: {format_datetime(transaction.created_at)}",
            reply_markup=main_menu_kb(),
            parse_mode="HTML"
        )
    except Exception as exc:
        logger.exception(f"Ошибка при создании расхода: {exc}")
        await callback.message.edit_text(
            "❌ Ошибка при добавлении расхода",
            reply_markup=back_to_menu_kb()
        )
    finally:
        session.close()
    
    await callback.answer()


@router.callback_query(AddExpenseState.confirming, F.data == "cancel_expense")
async def cb_cancel_expense(callback: CallbackQuery, state: FSMContext) -> None:
    """Отменить добавление расхода."""
    await state.clear()
    await callback.message.edit_text(
        "❌ Добавление расхода отменено",
        reply_markup=main_menu_kb()
    )
    await callback.answer()


# ============ ФОТО ОТЧЁТ ============

@router.callback_query(F.data == "menu_photo_report")
async def cb_photo_report_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Начать фото отчёт - выбор проекта."""
    tg_user = callback.from_user
    session = get_db_session()
    
    try:
        user = crud.get_user_by_tg_id(session, tg_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        projects = crud.get_projects_by_user(session, user.id)
        
        if not projects:
            await callback.message.edit_text(
                "❌ У вас нет проектов",
                reply_markup=back_to_menu_kb()
            )
        else:
            await state.set_state(PhotoReportState.choosing_project)
            await callback.message.edit_text(
                f"📸 Выберите проект для фото отчёта ({len(projects)}):",
                reply_markup=projects_list_kb(projects)
            )
    except Exception as exc:
        logger.exception(f"Ошибка при получении проектов: {exc}")
        await callback.answer("❌ Ошибка при загрузке проектов", show_alert=True)
    finally:
        session.close()
    
    await callback.answer()


@router.callback_query(PhotoReportState.choosing_project, F.data.startswith("proj_"))
async def cb_photo_project_selected(callback: CallbackQuery, state: FSMContext) -> None:
    """Проект выбран для фото отчёта."""
    project_id_str = callback.data.replace("proj_", "")
    
    if not project_id_str.isdigit():
        await callback.answer("❌ Ошибка обработки ID проекта", show_alert=True)
        return
    
    project_id = int(project_id_str)
    await state.update_data(photo_project_id=project_id)
    await state.set_state(PhotoReportState.choosing_stage)
    await callback.message.edit_text(
        "📸 Выберите этап работ:",
        reply_markup=project_stage_kb()
    )
    await callback.answer()


@router.callback_query(PhotoReportState.choosing_stage, F.data.startswith("stage_"))
async def cb_photo_stage_selected(callback: CallbackQuery, state: FSMContext) -> None:
    """Этап выбран, начинаем загрузку фото."""
    stage_map = {
        "stage_draft": ProjectStage.DRAFT,
        "stage_electric": ProjectStage.ELECTRIC,
        "stage_finish": ProjectStage.FINISH,
    }
    stage = stage_map.get(callback.data)
    
    if not stage:
        await callback.answer("❌ Неизвестный этап", show_alert=True)
        return
    
    await state.update_data(photo_stage=stage.value, photos_count=0)
    await state.set_state(PhotoReportState.waiting_for_photos)
    await callback.message.edit_text(
        f"📸 Загружайте фото для этапа: <b>{format_project_stage(stage.value)}</b>\n\n"
        f"Отправляйте фотографии одну за другой.\n"
        f"Вы можете загружать неограниченное количество фото.",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(PhotoReportState.waiting_for_photos)
async def msg_photo_upload(message: Message, state: FSMContext) -> None:
    """Получить фото для отчёта."""
    if not message.photo:
        await message.answer("❌ Пожалуйста, отправьте фотографию")
        return
    
    data = await state.get_data()
    photo_file_id = message.photo[-1].file_id  # Берём самое качественное
    tg_user = message.from_user
    session = get_db_session()
    
    try:
        # Сохраняем фото в БД
        photo = crud.create_progress_photo(
            session,
            project_id=data["photo_project_id"],
            photo_id=photo_file_id,
            stage=ProjectStage(data["photo_stage"])
        )
        
        logger.info(f"Загружено фото {photo.id} пользователем {tg_user.id}")
        
        # Увеличиваем счётчик фото
        photo_count = data.get("photos_count", 0) + 1
        await state.update_data(photos_count=photo_count)
        
        await message.answer(
            f"✅ Фото #{photo_count} сохранено!\n\n"
            f"Загружайте ещё фото или завершите отчёт.",
            reply_markup=photo_continue_kb(),
        )
    except Exception as exc:
        logger.exception(f"Ошибка при сохранении фото: {exc}")
        await message.answer("❌ Ошибка при сохранении фото")


@router.callback_query(PhotoReportState.waiting_for_photos, F.data == "finish_photos")
async def cb_finish_photos(callback: CallbackQuery, state: FSMContext) -> None:
    """Завершить загрузку фото."""
    data = await state.get_data()
    photo_count = data.get("photos_count", 0)
    
    await state.clear()
    await callback.message.edit_text(
        f"✅ <b>Фото отчёт завершён!</b>\n\n"
        f"📸 Загружено фотографий: {photo_count}\n"
        f"📋 Этап: {format_project_stage(data['photo_stage'])}\n\n"
        f"Спасибо за отчёт!",
        reply_markup=main_menu_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


# ============ ОТЧЁТ ПО ПРОЕКТУ ============

@router.callback_query(F.data == "menu_project_report")
async def cb_project_report_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Начать запрос отчёта - выбор проекта."""
    tg_user = callback.from_user
    session = get_db_session()
    
    try:
        user = crud.get_user_by_tg_id(session, tg_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        projects = crud.get_projects_by_user(session, user.id)
        
        if not projects:
            await callback.message.edit_text(
                "❌ У вас нет проектов",
                reply_markup=back_to_menu_kb()
            )
        else:
            await state.set_state(ProjectReportState.choosing_project)
            await callback.message.edit_text(
                f"📊 Выберите проект для отчёта ({len(projects)}):",
                reply_markup=projects_list_kb(projects)
            )
    except Exception as exc:
        logger.exception(f"Ошибка при получении проектов: {exc}")
        await callback.answer("❌ Ошибка при загрузке проектов", show_alert=True)
    finally:
        session.close()
    
    await callback.answer()


@router.callback_query(ProjectReportState.choosing_project, F.data.startswith("proj_"))
async def cb_report_project_selected(callback: CallbackQuery, state: FSMContext) -> None:
    """Проект выбран для отчёта."""
    project_id_str = callback.data.replace("proj_", "")
    
    if not project_id_str.isdigit():
        await callback.answer("❌ Ошибка обработки ID проекта", show_alert=True)
        return
    
    project_id = int(project_id_str)
    session = get_db_session()
    try:
        report = crud.get_project_report(session, project_id)
        
        if not report:
            await callback.message.edit_text(
                "❌ Проект не найден",
                reply_markup=back_to_menu_kb()
            )
        else:
            await state.clear()
            await callback.message.edit_text(
                format_project_report(report),
                reply_markup=back_to_menu_kb(),
                parse_mode="HTML"
            )
    except Exception as exc:
        logger.exception(f"Ошибка при получении отчёта: {exc}")
        await callback.answer("❌ Ошибка при загрузке отчёта", show_alert=True)
    finally:
        session.close()
    
    await callback.answer()


# ============ ДЕТАЛИ ПРОЕКТА С РАСШИРЕННОЙ СТАТИСТИКОЙ ============

@router.callback_query(F.data.startswith("proj_details_"))
async def cb_proj_details(callback: CallbackQuery, state: FSMContext) -> None:
    """Открыть детали проекта с расширенными опциями."""
    project_id_str = callback.data.replace("proj_details_", "")
    
    if not project_id_str.isdigit():
        await callback.answer("❌ Ошибка обработки ID", show_alert=True)
        return
    
    project_id = int(project_id_str)
    session = get_db_session()
    
    try:
        report = crud.get_project_report(session, project_id)
        
        if report:
            await callback.message.edit_text(
                format_project_report(report),
                reply_markup=project_details_kb(project_id),
                parse_mode="HTML"
            )
        else:
            await callback.answer("❌ Проект не найден", show_alert=True)
    except Exception as exc:
        logger.exception(f"Ошибка при загрузке деталей: {exc}")
        await callback.answer("❌ Ошибка при загрузке", show_alert=True)
    finally:
        session.close()
    
    await callback.answer()


# ============ СТАТИСТИКА РАСХОДОВ ============

@router.callback_query(F.data.startswith("stat_expenses_"))
async def cb_stat_expenses(callback: CallbackQuery, state: FSMContext) -> None:
    """Показать статистику расходов по категориям."""
    project_id_str = callback.data.replace("stat_expenses_", "")
    
    if not project_id_str.isdigit():
        await callback.answer("❌ Ошибка обработки ID", show_alert=True)
        return
    
    project_id = int(project_id_str)
    session = get_db_session()
    
    try:
        stats = crud.get_budget_by_category(session, project_id)
        
        from bot.utils import format_expense_statistics
        text = format_expense_statistics(stats)
        
        await callback.message.edit_text(
            text,
            reply_markup=stat_menu_kb(project_id),
            parse_mode="HTML"
        )
    except Exception as exc:
        logger.exception(f"Ошибка при загрузке статистики: {exc}")
        await callback.answer("❌ Ошибка при загрузке", show_alert=True)
    finally:
        session.close()
    
    await callback.answer()


# ============ ПРОГРЕСС ПО ЭТАПАМ ============

@router.callback_query(F.data.startswith("stat_progress_"))
async def cb_stat_progress(callback: CallbackQuery, state: FSMContext) -> None:
    """Показать прогресс работ по этапам."""
    project_id_str = callback.data.replace("stat_progress_", "")
    
    if not project_id_str.isdigit():
        await callback.answer("❌ Ошибка обработки ID", show_alert=True)
        return
    
    project_id = int(project_id_str)
    session = get_db_session()
    
    try:
        stages = crud.get_project_progress(session, project_id)
        
        from bot.utils import format_progress_stats
        text = format_progress_stats(stages)
        
        await callback.message.edit_text(
            text,
            reply_markup=stat_menu_kb(project_id),
            parse_mode="HTML"
        )
    except Exception as exc:
        logger.exception(f"Ошибка при загрузке прогресса: {exc}")
        await callback.answer("❌ Ошибка при загрузке", show_alert=True)
    finally:
        session.close()
    
    await callback.answer()


# ============ ИСТОРИЯ РАСХОДОВ ============

@router.callback_query(F.data.startswith("history_expenses_"))
async def cb_history_expenses(callback: CallbackQuery, state: FSMContext) -> None:
    """Показать историю расходов с пагинацией."""
    project_id_str = callback.data.replace("history_expenses_", "")
    
    if not project_id_str.isdigit():
        await callback.answer("❌ Ошибка обработки ID", show_alert=True)
        return
    
    project_id = int(project_id_str)
    session = get_db_session()
    
    try:
        transactions = crud.get_project_transactions(session, project_id)
        
        if not transactions:
            await callback.message.edit_text(
                "📭 История расходов пуста",
                reply_markup=back_to_menu_kb()
            )
            await callback.answer()
            return
        
        # Показываем последние 10 расходов
        recent = sorted(transactions, key=lambda x: x.created_at, reverse=True)[:10]
        
        history_text = "📋 <b>История расходов (последние 10):</b>\n\n"
        for idx, t in enumerate(recent, 1):
            history_text += f"{idx}. " + format_expense_entry(
                float(t.amount), t.category.value, t.description, t.created_at
            ) + "\n\n"
        
        total = sum(float(t.amount) for t in recent)
        history_text += f"<b>Итого:</b> {format_price(total)}"
        
        await callback.message.edit_text(
            history_text,
            reply_markup=stat_menu_kb(project_id),
            parse_mode="HTML"
        )
    except Exception as exc:
        logger.exception(f"Ошибка при загрузке истории: {exc}")
        await callback.answer("❌ Ошибка при загрузке", show_alert=True)
    finally:
        session.close()
    
    await callback.answer()


# ============ ГАЛЕРЕЯ ============

@router.callback_query(F.data.startswith("gallery_"))
async def cb_gallery(callback: CallbackQuery, state: FSMContext) -> None:
    """Открыть галерею фото проекта."""
    project_id_str = callback.data.replace("gallery_", "")
    
    if not project_id_str.isdigit():
        await callback.answer("❌ Ошибка обработки ID", show_alert=True)
        return
    
    project_id = int(project_id_str)
    session = get_db_session()
    
    try:
        photos = crud.get_all_project_photos(session, project_id)
        
        if not photos:
            await callback.message.edit_text(
                "📭 Галерея пуста. Загрузите фотографии.",
                reply_markup=back_to_menu_kb()
            )
            await callback.answer()
            return
        
        # Показываем первое фото
        photo = photos[0]
        await state.update_data(
            gallery_project_id=project_id,
            gallery_index=0,
            gallery_photos=[p.photo_id for p in photos]
        )
        
        caption = (
            f"📸 <b>Фото 1 из {len(photos)}</b>\n"
            f"Этап: {format_project_stage(photo.stage.value)}\n"
            f"Дата: {format_datetime(photo.created_at)}"
        )
        
        await callback.message.edit_media(
            media=None  # Will be replaced below
        )
        await callback.message.answer_photo(
            photo=photo.photo_id,
            caption=caption,
            parse_mode="HTML"
        )
        
        await callback.message.edit_text(
            f"📷 Галерея ({len(photos)} фото)",
            reply_markup=back_to_menu_kb()
        )
    except Exception as exc:
        logger.exception(f"Ошибка при открытии галереи: {exc}")
        await callback.answer("❌ Ошибка при открытии галереи", show_alert=True)
    finally:
        session.close()
    
    await callback.answer()


# ============ ОБНОВЛЕНИЕ БЮДЖЕТА ============

@router.callback_query(F.data.startswith("update_budget_"))
async def cb_update_budget_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Начать обновление бюджета проекта."""
    project_id_str = callback.data.replace("update_budget_", "")
    
    if not project_id_str.isdigit():
        await callback.answer("❌ Ошибка обработки ID", show_alert=True)
        return
    
    await state.set_state(ProjectManagementState.updating_budget)
    await state.update_data(budget_project_id=int(project_id_str))
    
    await callback.message.edit_text(
        "💰 Введите новый бюджет проекта (в BYN):\n\n"
        "Текущий бюджет будет заменён на новое значение."
    )
    await callback.answer()


@router.message(ProjectManagementState.updating_budget)
async def msg_update_budget(message: Message, state: FSMContext) -> None:
    """Получить новый бюджет и сохранить."""
    is_valid, amount = is_valid_amount(message.text)
    
    if not is_valid or amount is None:
        await message.answer(
            "❌ Введите корректную сумму (больше 0):\n"
            "Например: 50000 или 50000.50"
        )
        return
    
    data = await state.get_data()
    project_id = data.get("budget_project_id")
    
    if not project_id:
        await message.answer("❌ Ошибка: ID проекта не найден")
        return
    
    session = get_db_session()
    try:
        success = crud.update_project_budget(session, project_id, amount)
        
        if success:
            await state.clear()
            await message.answer(
                f"✅ <b>Бюджет обновлён!</b>\n\n"
                f"Новый бюджет: {format_price(amount)}",
                reply_markup=main_menu_kb(),
                parse_mode="HTML"
            )
        else:
            await message.answer("❌ Проект не найден")
    except Exception as exc:
        logger.exception(f"Ошибка при обновлении бюджета: {exc}")
        await message.answer("❌ Ошибка при обновлении бюджета")
    finally:
        session.close()


# ============ НАСТРОЙКИ ============

@router.callback_query(F.data == "menu_settings")
async def cb_settings_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Открыть меню настроек."""
    tg_user = callback.from_user
    session = get_db_session()
    
    try:
        user = crud.get_user_by_tg_id(session, tg_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        await state.set_state(SettingsState.viewing_settings)
        
        settings_text = (
            f"⚙️ <b>Мои настройки:</b>\n\n"
            f"👤 Ваш ID: <code>{tg_user.id}</code>\n"
            f"📝 Имя: <code>{tg_user.full_name}</code>\n"
            f"🔐 Роль: <b>{format_role_display(user.role)}</b>\n\n"
            f"Выберите действие:"
        )
        
        await callback.message.edit_text(
            settings_text,
            reply_markup=settings_menu_kb(),
            parse_mode="HTML"
        )
    except Exception as exc:
        logger.exception(f"Ошибка при открытии настроек: {exc}")
        await callback.answer("❌ Ошибка при загрузке настроек", show_alert=True)
    finally:
        session.close()
    
    await callback.answer()


@router.callback_query(SettingsState.viewing_settings, F.data == "settings_change_role")
async def cb_settings_change_role(callback: CallbackQuery, state: FSMContext) -> None:
    """Изменить роль в настройках."""
    await state.set_state(SettingsState.changing_role)
    await callback.message.edit_text(
        "🔐 Выберите новую роль:",
        reply_markup=role_selection_kb()
    )
    await callback.answer()


@router.callback_query(SettingsState.changing_role, F.data.startswith("role_"))
async def cb_settings_role_changed(callback: CallbackQuery, state: FSMContext) -> None:
    """Сохранить изменённую роль."""
    tg_user = callback.from_user
    
    role_map = {
        "role_foreman": UserRole.FOREMAN,
        "role_client": UserRole.CLIENT,
    }
    selected_role = role_map.get(callback.data)
    
    if not selected_role:
        await callback.answer("❌ Неизвестная роль", show_alert=True)
        return
    
    session = get_db_session()
    try:
        user = crud.get_user_by_tg_id(session, tg_user.id)
        if user:
            crud.update_user_role(session, user.id, selected_role)
            logger.info(f"Пользователь {tg_user.id} изменил роль на: {selected_role}")
            
            await state.clear()
            await callback.message.edit_text(
                f"✅ Роль изменена на: <b>{format_role_display(selected_role)}</b>",
                reply_markup=main_menu_kb(),
                parse_mode="HTML"
            )
        else:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
    except Exception as exc:
        logger.exception(f"Ошибка при изменении роли: {exc}")
        await callback.answer("❌ Ошибка при сохранении", show_alert=True)
    finally:
        session.close()
    
    await callback.answer()


@router.callback_query(SettingsState.viewing_settings, F.data == "settings_about")
async def cb_settings_about(callback: CallbackQuery, state: FSMContext) -> None:
    """Показать информацию о приложении."""
    about_text = (
        "ℹ️ <b>О BuildFlow v2.0:</b>\n\n"
        "Приложение для управления строительными проектами на Telegram.\n\n"
        "<b>Функции:</b>\n"
        "✅ Создание и управление проектами\n"
        "✅ Отслеживание расходов по категориям\n"
        "✅ Ведение фотографического отчета\n"
        "✅ Контроль бюджета\n"
        "✅ Анализ прогресса работ\n"
        "✅ Детальная статистика\n\n"
        "<b>Версия:</b> 2.0\n"
        "<b>Разработчик:</b> BuildFlow Team\n"
        "<b>Поддержка:</b> @support_buildflow"
    )
    
    await callback.message.edit_text(
        about_text,
        reply_markup=back_to_menu_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


# ============ СПРАВКА И КОМАНДЫ ============

@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Показать справку по командам."""
    help_text = (
        "<b>📚 Справка по командам:</b>\n\n"
        "<code>/start</code> – начать работу / главное меню\n"
        "<code>/help</code> – эта справка\n"
        "<code>/status</code> – статус бота\n\n"
        "<b>Основные функции:</b>\n"
        "👷 Прорабы могут создавать проекты\n"
        "💰 Добавляйте расходы по категориям\n"
        "📸 Загружайте фото прогресса по этапам\n"
        "📊 Смотрите отчёты и статистику\n"
        "⚙️ Управляйте своими настройками\n\n"
        "<b>Советы:</b>\n"
        "• Используйте меню для навигации\n"
        "• Нажимайте «Назад» для возврата на предыдущий экран\n"
        "• Все данные сохраняются автоматически"
    )
    
    await message.answer(help_text, reply_markup=main_menu_kb(), parse_mode="HTML")


@router.message(Command("status"))
async def cmd_status(message: Message) -> None:
    """Показать статус бота."""
    await message.answer(
        "✅ Бот <b>BuildFlow v2.0</b> работает отлично!\n\n"
        "Все функции доступны. Начните с /start",
        parse_mode="HTML"
    )


# ============ ОБРАБОТЧИК НЕИЗВЕСТНЫХ СООБЩЕНИЙ ============

@router.message()
async def msg_unknown(message: Message, state: FSMContext) -> None:
    """Обработчик всех остальных сообщений."""
    current_state = await state.get_state()
    
    if current_state is None:
        # Если нет активного состояния, показываем главное меню
        await message.answer(
            "🤔 Я не понял вашу команду.\n\n"
            "Используйте меню ниже или отправьте /help для справки.",
            reply_markup=main_menu_kb()
        )
    # Если есть активное состояние, обработчик состояния займётся ответом
