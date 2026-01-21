"""Обработчики для задач и согласований (Change Orders)."""

import logging
from datetime import datetime

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from sqlalchemy.orm import Session

from database.session import get_session
from database import crud
from database.models import UserRole
from bot.utils import (
    format_task_list,
    format_change_order_notification,
    format_task_notification,
)
from bot.keyboards.common import (
    my_tasks_menu_kb,
    tasks_list_kb,
    approval_requests_menu_kb,
    approve_reject_kb,
    rejection_reason_kb,
)

logger = logging.getLogger(__name__)
router = Router()


# ============ STATES ============

class TasksState(StatesGroup):
    """Состояния для управления задачами."""
    browsing_menu = State()
    viewing_tasks = State()
    creating_task = State()
    task_title = State()
    task_description = State()
    task_project = State()
    task_assign_to = State()


class ApprovalsState(StatesGroup):
    """Состояния для согласований."""
    browsing_menu = State()
    viewing_pending = State()
    viewing_approved = State()
    viewing_rejected = State()
    entering_rejection_reason = State()


# ============ ЗАДАЧИ ============

@router.callback_query(F.data == "menu_my_tasks")
async def cb_my_tasks_menu(callback: CallbackQuery, state: FSMContext):
    """Открыть меню задач."""
    logger.info(f"👤 Пользователь {callback.from_user.id} открыл меню задач")
    
    await state.set_state(TasksState.browsing_menu)
    
    await callback.message.edit_text(
        "📋 <b>Управление задачами</b>\n\n"
        "Выберите действие:",
        reply_markup=my_tasks_menu_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "tasks_my_tasks", TasksState.browsing_menu)
async def cb_view_my_tasks(callback: CallbackQuery, state: FSMContext):
    """Показать мои задачи."""
    logger.info(f"👤 Пользователь {callback.from_user.id} просматривает свои задачи")
    
    session: Session = get_session()
    try:
        tasks = crud.get_assigned_tasks(session, callback.from_user.id)
        
        if not tasks:
            text = "📭 <b>У вас нет активных задач</b>"
        else:
            # Форматируем список задач
            text = "📋 <b>Ваши задачи:</b>\n\n"
            for task in tasks:
                text += f"📌 <b>{task.title}</b>\n"
                if task.description:
                    text += f"   {task.description}\n"
                if task.due_date:
                    text += f"   ⏰ Срок: {task.due_date.strftime('%d.%m.%Y')}\n"
                text += "\n"
        
        await state.set_state(TasksState.viewing_tasks)
        await callback.message.edit_text(text, reply_markup=tasks_list_kb(
            [{"id": t.id, "title": t.title, "is_completed": t.is_completed} for t in tasks]
        ))
        
    except Exception as e:
        logger.error(f"❌ Ошибка при получении задач: {e}")
        await callback.answer("❌ Ошибка при получении задач", show_alert=True)
    finally:
        session.close()


@router.callback_query(F.data == "tasks_create", TasksState.browsing_menu)
async def cb_create_task_start(callback: CallbackQuery, state: FSMContext):
    """Начать создание новой задачи."""
    logger.info(f"👤 Пользователь {callback.from_user.id} начинает создавать задачу")
    
    await state.set_state(TasksState.task_title)
    
    await callback.message.edit_text(
        "📝 <b>Введите название задачи:</b>"
    )
    await callback.answer()


@router.message(TasksState.task_title)
async def process_task_title(message: Message, state: FSMContext):
    """Обработать название задачи."""
    logger.info(f"📝 Название задачи: {message.text[:50]}")
    
    await state.update_data(task_title=message.text)
    await state.set_state(TasksState.task_description)
    
    await message.answer(
        "📄 <b>Введите описание задачи (опционально):</b>\n\n"
        "или нажмите /skip чтобы пропустить",
    )


@router.message(TasksState.task_description)
async def process_task_description(message: Message, state: FSMContext):
    """Обработать описание задачи."""
    if message.text and message.text.startswith("/"):
        description = None
    else:
        description = message.text
    
    await state.update_data(task_description=description)
    
    # Получаем список проектов для выбора
    session: Session = get_session()
    try:
        user = crud.get_user_by_tg_id(session, message.from_user.id)
        if not user:
            await message.answer("❌ Пользователь не найден")
            return
        
        projects = crud.get_user_projects(session, user.id)
        
        if not projects:
            await message.answer("❌ У вас нет проектов")
            await state.clear()
            return
        
        await state.set_state(TasksState.task_project)
        
        # Создаем клавиатуру с проектами
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = [
            [InlineKeyboardButton(text=f"📦 {p.name}", callback_data=f"task_proj_{p.id}")]
            for p in projects
        ]
        keyboard.append([InlineKeyboardButton(text="◀️ Отмена", callback_data="tasks_back")])
        
        await message.answer(
            "📂 <b>Выберите проект для задачи:</b>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        )
        
    except Exception as e:
        logger.error(f"❌ Ошибка при получении проектов: {e}")
        await message.answer("❌ Ошибка при получении проектов")
        await state.clear()
    finally:
        session.close()


@router.callback_query(F.data.startswith("task_proj_"))
async def cb_task_select_project(callback: CallbackQuery, state: FSMContext):
    """Выбрать проект для задачи."""
    project_id = int(callback.data.replace("task_proj_", ""))
    
    await state.update_data(task_project_id=project_id)
    logger.info(f"📂 Проект для задачи: {project_id}")
    
    session: Session = get_session()
    try:
        # Сохраняем задачу
        data = await state.get_data()
        
        task = crud.create_task(
            session,
            project_id=project_id,
            title=data.get("task_title"),
            description=data.get("task_description"),
            assigned_to_id=callback.from_user.id,  # Назначаем себе
        )
        
        logger.info(f"✅ Задача создана: {task.id}")
        
        await callback.message.edit_text(
            f"✅ <b>Задача создана!</b>\n\n"
            f"📝 Название: {task.title}\n"
            f"📂 Проект: {task.project.name}\n"
            f"👤 Назначена вам\n\n"
            f"Задача добавлена в ваш список"
        )
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"❌ Ошибка при создании задачи: {e}")
        await callback.answer("❌ Ошибка при создании задачи", show_alert=True)
    finally:
        session.close()


@router.callback_query(F.data.startswith("task_complete_"))
async def cb_complete_task(callback: CallbackQuery):
    """Отметить задачу как выполненную."""
    task_id = int(callback.data.replace("task_complete_", ""))
    
    session: Session = get_session()
    try:
        task = crud.complete_task(session, task_id)
        logger.info(f"✅ Задача {task_id} отмечена выполненной")
        
        await callback.answer("✅ Задача отмечена как выполненная", show_alert=False)
        
        # Обновляем сообщение
        await callback.message.edit_text(
            f"✅ <b>Задача выполнена!</b>\n\n"
            f"📝 {task.title}\n\n"
            f"Хорошей работы! 🎉"
        )
        
    except Exception as e:
        logger.error(f"❌ Ошибка при выполнении задачи: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)
    finally:
        session.close()


@router.callback_query(F.data.startswith("task_delete_"))
async def cb_delete_task(callback: CallbackQuery):
    """Удалить задачу."""
    task_id = int(callback.data.replace("task_delete_", ""))
    
    session: Session = get_session()
    try:
        crud.delete_task(session, task_id)
        logger.info(f"🗑️ Задача {task_id} удалена")
        
        await callback.answer("✅ Задача удалена", show_alert=False)
        await callback.message.edit_text("🗑️ <b>Задача удалена</b>")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при удалении задачи: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)
    finally:
        session.close()


# ============ СОГЛАСОВАНИЯ (CHANGE ORDERS) ============

@router.callback_query(F.data == "menu_approvals")
async def cb_approvals_menu(callback: CallbackQuery, state: FSMContext):
    """Открыть меню согласований."""
    logger.info(f"👤 Пользователь {callback.from_user.id} открыл меню согласований")
    
    await state.set_state(ApprovalsState.browsing_menu)
    
    await callback.message.edit_text(
        "✅ <b>Управление согласованиями</b>\n\n"
        "Выберите категорию:",
        reply_markup=approval_requests_menu_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "approvals_pending", ApprovalsState.browsing_menu)
async def cb_view_pending_approvals(callback: CallbackQuery, state: FSMContext):
    """Показать ожидающие согласования."""
    logger.info(f"👤 Пользователь {callback.from_user.id} просматривает ожидающие согласования")
    
    session: Session = get_session()
    try:
        orders = crud.get_pending_change_orders(session)
        
        if not orders:
            text = "📭 <b>Нет ожидающих согласований</b>"
            await callback.message.edit_text(text, reply_markup=approval_requests_menu_kb())
        else:
            text = "⏳ <b>Ожидающие согласования:</b>\n\n"
            
            for order in orders:
                trans = order.transaction
                requester = order.requester
                text += (
                    f"📋 ID: {order.id}\n"
                    f"💰 Сумма: {trans.amount:,.2f} BYN\n"
                    f"📂 Категория: {trans.category.value}\n"
                    f"👷 Запросил: {requester.name}\n"
                    f"📝 Описание: {trans.description}\n\n"
                )
            
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            keyboard = [
                [InlineKeyboardButton(text=f"📋 Согласование #{order.id}", 
                                     callback_data=f"view_approval_{order.id}")]
                for order in orders
            ]
            keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_approvals")])
            
            await state.set_state(ApprovalsState.viewing_pending)
            await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
        
    except Exception as e:
        logger.error(f"❌ Ошибка при получении согласований: {e}")
        await callback.answer("❌ Ошибка при получении согласований", show_alert=True)
    finally:
        session.close()


@router.callback_query(F.data.startswith("view_approval_"))
async def cb_view_approval_detail(callback: CallbackQuery, state: FSMContext):
    """Просмотреть детали согласования."""
    order_id = int(callback.data.replace("view_approval_", ""))
    
    session: Session = get_session()
    try:
        order = crud.get_change_order(session, order_id)
        
        if not order:
            await callback.answer("❌ Согласование не найдено", show_alert=True)
            return
        
        trans = order.transaction
        requester = order.requester
        
        text = (
            f"📋 <b>Запрос на согласование #{order.id}</b>\n\n"
            f"💰 <b>Сумма:</b> {trans.amount:,.2f} BYN\n"
            f"📂 <b>Категория:</b> {trans.category.value}\n"
            f"👷 <b>Запросил:</b> {requester.name}\n"
            f"📝 <b>Описание:</b> {trans.description}\n"
            f"⏳ <b>Статус:</b> {order.status.value}\n"
            f"📅 <b>Создано:</b> {order.created_at.strftime('%d.%m.%Y %H:%M')}\n"
        )
        
        await state.update_data(current_order_id=order_id)
        await callback.message.edit_text(text, reply_markup=approve_reject_kb(order_id))
        
    except Exception as e:
        logger.error(f"❌ Ошибка при загрузке согласования: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)
    finally:
        session.close()


@router.callback_query(F.data.startswith("approve_"))
async def cb_approve_request(callback: CallbackQuery, state: FSMContext):
    """Одобрить запрос."""
    order_id = int(callback.data.replace("approve_", ""))
    
    session: Session = get_session()
    try:
        order = crud.approve_change_order(session, order_id, callback.from_user.id)
        logger.info(f"✅ Согласование {order_id} одобрено")
        
        await callback.message.edit_text(
            f"✅ <b>Согласование #{order_id} одобрено!</b>\n\n"
            f"Запрос был принят и расход добавлен в проект."
        )
        
        await callback.answer("✅ Согласование одобрено", show_alert=False)
        
    except Exception as e:
        logger.error(f"❌ Ошибка при одобрении: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)
    finally:
        session.close()


@router.callback_query(F.data.startswith("reject_"))
async def cb_reject_request(callback: CallbackQuery, state: FSMContext):
    """Начать процесс отклонения запроса."""
    order_id = int(callback.data.replace("reject_", ""))
    
    await state.update_data(rejection_order_id=order_id)
    await state.set_state(ApprovalsState.entering_rejection_reason)
    
    await callback.message.edit_text(
        "❌ <b>Выберите причину отклонения:</b>",
        reply_markup=rejection_reason_kb(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("reason_"), ApprovalsState.entering_rejection_reason)
async def cb_select_rejection_reason(callback: CallbackQuery, state: FSMContext):
    """Выбрать причину отклонения."""
    reason_code = callback.data
    
    reasons_map = {
        "reason_budget": "Превышен бюджет",
        "reason_quality": "Плохое качество",
        "reason_other": "Другое",
        "reason_cancel": None,
    }
    
    if reason_code == "reason_cancel":
        await callback.answer("Отменено", show_alert=False)
        return
    
    reason = reasons_map.get(reason_code, "Неизвестная причина")
    data = await state.get_data()
    order_id = data.get("rejection_order_id")
    
    session: Session = get_session()
    try:
        order = crud.reject_change_order(
            session,
            order_id,
            callback.from_user.id,
            reason
        )
        logger.info(f"❌ Согласование {order_id} отклонено: {reason}")
        
        await callback.message.edit_text(
            f"❌ <b>Согласование #{order_id} отклонено</b>\n\n"
            f"Причина: {reason}\n\n"
            f"Заказчик получит уведомление об отклонении."
        )
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"❌ Ошибка при отклонении: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)
    finally:
        session.close()


@router.callback_query(F.data == "back_approvals")
async def cb_back_to_approvals(callback: CallbackQuery, state: FSMContext):
    """Вернуться в меню согласований."""
    await state.set_state(ApprovalsState.browsing_menu)
    
    await callback.message.edit_text(
        "✅ <b>Управление согласованиями</b>\n\n"
        "Выберите категорию:",
        reply_markup=approval_requests_menu_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "tasks_back")
async def cb_back_to_tasks(callback: CallbackQuery, state: FSMContext):
    """Вернуться в меню задач."""
    await state.set_state(TasksState.browsing_menu)
    
    await callback.message.edit_text(
        "📋 <b>Управление задачами</b>\n\n"
        "Выберите действие:",
        reply_markup=my_tasks_menu_kb(),
    )
    await callback.answer()
