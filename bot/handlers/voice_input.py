"""Обработчики для голосовых сообщений и AI функций."""

import logging
import os
from pathlib import Path

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from sqlalchemy.orm import Session

from database.session import get_session
from database import crud
from bot.utils import (
    transcribe_audio_whisper,
    parse_expense_from_voice,
    format_transaction_category,
)
from bot.keyboards.common import (
    main_menu_kb_v2,
)
from database.models import TransactionCategory

logger = logging.getLogger(__name__)
router = Router()


# ============ STATES ============

class VoiceInputState(StatesGroup):
    """Состояния для голосового ввода расходов."""
    waiting_audio = State()
    confirming_expense = State()
    selecting_project = State()


# ============ ГОЛОСОВОЙ ВВОД ============

@router.callback_query(F.data == "menu_voice_input")
async def cb_voice_input_menu(callback: CallbackQuery, state: FSMContext):
    """Открыть меню голосового ввода."""
    logger.info(f"👤 Пользователь {callback.from_user.id} открыл голосовой ввод")
    
    await state.set_state(VoiceInputState.waiting_audio)
    
    await callback.message.edit_text(
        "🎙️ <b>Голосовой ввод расходов</b>\n\n"
        "📱 Отправьте голосовое сообщение с описанием расхода.\n"
        "Например: 'Купил 5 мешков цемента за 250 рублей'\n\n"
        "Я транскрибирую сообщение и помогу заполнить расход.",
    )
    await callback.answer()


@router.message(VoiceInputState.waiting_audio, F.voice)
async def process_voice_message(message: Message, state: FSMContext):
    """Обработать голосовое сообщение."""
    logger.info(f"🎙️ Получено голосовое сообщение от {message.from_user.id}")
    
    # Показываем, что обрабатываем
    status_msg = await message.answer("⏳ <b>Обработка голосового сообщения...</b>")
    
    try:
        # Скачиваем голосовой файл
        voice_file = await message.bot.get_file(message.voice.file_id)
        voice_path = f"temp_voice_{message.from_user.id}_{message.message_id}.ogg"
        
        await message.bot.download_file(voice_file.file_path, voice_path)
        logger.info(f"📥 Голосовой файл сохранен: {voice_path}")
        
        # Транскрибируем
        await status_msg.edit_text("📝 <b>Транскрибирование...</b>")
        
        text = await transcribe_audio_whisper(voice_path)
        
        if not text:
            await status_msg.edit_text(
                "❌ <b>Ошибка при транскрибировании</b>\n\n"
                "Убедитесь, что:\n"
                "1. OPENAI_API_KEY установлен в .env\n"
                "2. API ключ действителен\n\n"
                "Попробуйте позже или используйте текстовый ввод."
            )
            return
        
        logger.info(f"✅ Транскрибировано: {text[:100]}")
        
        # Парсируем расход
        await status_msg.edit_text("🤖 <b>Анализирование расхода...</b>")
        
        expense_data = await parse_expense_from_voice(text)
        
        if not expense_data:
            # Низкая уверенность - просим уточнить
            await status_msg.edit_text(
                f"❓ <b>Я не совсем понял расход</b>\n\n"
                f"Вы сказали: \"{text}\"\n\n"
                f"Пожалуйста, повторите или используйте текстовый ввод.\n\n"
                f"Формат: 'Категория: Сумма - Описание'\n"
                f"Пример: 'Материалы: 500 - Цемент'"
            )
            return
        
        logger.info(f"✅ Расход распарсен: {expense_data}")
        
        # Сохраняем в state
        await state.update_data(
            voice_text=text,
            expense_amount=expense_data.get("amount"),
            expense_category=expense_data.get("category"),
            expense_description=expense_data.get("description"),
            confidence=expense_data.get("confidence"),
        )
        
        # Показываем подтверждение
        category_name = format_transaction_category(expense_data.get("category", "other"))
        confidence_percent = int(expense_data.get("confidence", 0) * 100)
        
        confirmation_text = (
            f"✅ <b>Я распарсил расход:</b>\n\n"
            f"💰 <b>Сумма:</b> {expense_data.get('amount', 0):.2f} BYN\n"
            f"📂 <b>Категория:</b> {category_name}\n"
            f"📝 <b>Описание:</b> {expense_data.get('description', 'Нет')}\n"
            f"🔍 <b>Уверенность:</b> {confidence_percent}%\n\n"
            f"Это верно? Нажмите <b>Продолжить</b> для добавления в проект."
        )
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = [
            [
                InlineKeyboardButton(text="✅ Продолжить", callback_data="voice_confirm"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="voice_cancel"),
            ]
        ]
        
        await state.set_state(VoiceInputState.confirming_expense)
        await status_msg.edit_text(confirmation_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
        
        # Удаляем временный файл
        if os.path.exists(voice_path):
            os.remove(voice_path)
        
    except Exception as e:
        logger.error(f"❌ Ошибка при обработке голоса: {e}")
        await status_msg.edit_text(
            f"❌ <b>Ошибка при обработке голоса:</b>\n\n{str(e)[:200]}"
        )
        
        # Очищаем временный файл если есть
        try:
            if os.path.exists(voice_path):
                os.remove(voice_path)
        except:
            pass


@router.message(VoiceInputState.waiting_audio)
async def process_non_voice_in_voice_state(message: Message):
    """Если в режиме голосового ввода отправили не голос."""
    logger.warning(f"⚠️ Ожидалось голосовое сообщение, но получено: {message.content_type}")
    
    await message.answer(
        "🎙️ <b>Пожалуйста, отправьте голосовое сообщение</b>\n\n"
        "Используйте значок микрофона в вашем клиенте Telegram."
    )


@router.callback_query(F.data == "voice_confirm", VoiceInputState.confirming_expense)
async def cb_confirm_voice_expense(callback: CallbackQuery, state: FSMContext):
    """Подтвердить распарсенный расход."""
    logger.info(f"✅ Пользователь {callback.from_user.id} подтвердил расход")
    
    session: Session = get_session()
    try:
        # Получаем список проектов
        user = crud.get_user_by_tg_id(session, callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        projects = crud.get_user_projects(session, user.id)
        
        if not projects:
            await callback.message.edit_text("❌ <b>У вас нет проектов</b>")
            await state.clear()
            return
        
        # Показываем список проектов
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = [
            [InlineKeyboardButton(text=f"📦 {p.name}", callback_data=f"voice_proj_{p.id}")]
            for p in projects
        ]
        keyboard.append([InlineKeyboardButton(text="◀️ Отмена", callback_data="voice_cancel")])
        
        await state.set_state(VoiceInputState.selecting_project)
        await callback.message.edit_text(
            "📂 <b>Выберите проект для расхода:</b>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"❌ Ошибка при выборе проекта: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)
    finally:
        session.close()


@router.callback_query(F.data.startswith("voice_proj_"), VoiceInputState.selecting_project)
async def cb_voice_select_project(callback: CallbackQuery, state: FSMContext):
    """Выбрать проект и сохранить расход."""
    project_id = int(callback.data.replace("voice_proj_", ""))
    
    session: Session = get_session()
    try:
        data = await state.get_data()
        
        # Создаем транзакцию
        transaction = crud.create_transaction(
            session,
            project_id=project_id,
            amount=data.get("expense_amount", 0),
            category=TransactionCategory(data.get("expense_category", "other")),
            description=data.get("expense_description", ""),
            photo_url=None,
            created_by_id=callback.from_user.id,
        )
        
        logger.info(f"✅ Расход {transaction.id} создан из голоса")
        
        await callback.message.edit_text(
            f"✅ <b>Расход добавлен!</b>\n\n"
            f"💰 Сумма: {transaction.amount:.2f} BYN\n"
            f"📂 Проект: {transaction.project.name}\n"
            f"📝 Описание: {transaction.description}\n\n"
            f"Спасибо! 🎉"
        )
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"❌ Ошибка при создании расхода: {e}")
        await callback.answer("❌ Ошибка при создании расхода", show_alert=True)
    finally:
        session.close()


@router.callback_query(F.data == "voice_cancel")
async def cb_voice_cancel(callback: CallbackQuery, state: FSMContext):
    """Отменить голосовой ввод."""
    logger.info(f"❌ Голосовой ввод отменен пользователем {callback.from_user.id}")
    
    await callback.message.edit_text(
        "❌ <b>Действие отменено</b>\n\n"
        "Используйте главное меню для других функций."
    )
    
    await state.clear()
