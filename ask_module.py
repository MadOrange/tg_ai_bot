"""
Модуль для отправки вопросов владельцу
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any

from aiogram import Bot
from aiogram.types import (
    Message, 
    CallbackQuery, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton
)
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

logger = logging.getLogger(__name__)


class AskStates(StatesGroup):
    """Состояния для отправки вопроса владельцу"""
    waiting_for_question = State()
    confirming_question = State()


class AskModule:
    """Модуль для обработки вопросов владельцу"""
    
    def __init__(self, dp, bot: Bot, owner_id: str = None):
        """
        Инициализация модуля
        
        Args:
            dp: Dispatcher aiogram
            bot: Bot aiogram
            owner_id: Telegram ID владельца
        """
        self.dp = dp
        self.bot = bot
        self.owner_id = owner_id or os.getenv("OWNER_TELEGRAM_ID")
        
        # Регистрируем обработчики
        self.register_handlers()
    
    def register_handlers(self):
        """Регистрирует обработчики команд"""
        # Команда /ask
        self.dp.message.register(self.cmd_ask_owner, Command("ask"))
        
        # Обработка вопроса
        self.dp.message.register(
            self.process_ask_question, 
            AskStates.waiting_for_question
        )
        
        # Подтверждение отправки
        self.dp.callback_query.register(
            self.handle_ask_confirmation,
            AskStates.confirming_question
        )
        
        # Быстрая отправка через префикс
        from aiogram import F
        self.dp.message.register(
            self.handle_quick_ask,
            F.text.startswith("вопрос:")
        )
        
        # Команда /cancel для этого модуля
        self.dp.message.register(self.cmd_cancel, Command("cancel"))
    
    async def cmd_ask_owner(self, message: Message, state: FSMContext):
        """Начало диалога для отправки вопроса владельцу"""
        if not self.owner_id:
            await message.answer(
                "❌ Функция связи с владельцем временно недоступна.\n"
                "Владелец не указал свои контактные данные."
            )
            return
        
        await message.answer(
            "📝 <b>Вопрос владельцу</b>\n\n"
            "Напишите ваш вопрос или сообщение, которое я передам Дмитрию.\n\n"
            "Для отмены используйте команду /cancel",
            parse_mode="HTML"
        )
        await state.set_state(AskStates.waiting_for_question)
    
    async def process_ask_question(self, message: Message, state: FSMContext):
        """Обработка вопроса пользователя"""
        user_question = message.text.strip()
        
        # Если пользователь отправил команду /cancel
        if user_question.lower() == "/cancel":
            await state.clear()
            await message.answer("❌ Отправка вопроса отменена.")
            return
        
        # Сохраняем вопрос
        await state.update_data(question=user_question)
        
        # Создаем клавиатуру для подтверждения
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Отправить", callback_data="ask_confirm"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="ask_cancel")
            ]
        ])
        
        # Показываем подтверждение
        await message.answer(
            f"<b>Подтвердите отправку:</b>\n\n"
            f"<i>{user_question[:300]}...</i>\n\n"
            f"Отправить этот вопрос Дмитрию?",
            parse_mode="HTML",
            reply_markup=keyboard
        )
        await state.set_state(AskStates.confirming_question)
    
    async def handle_ask_confirmation(self, callback: CallbackQuery, state: FSMContext):
        """Обработка подтверждения отправки вопроса"""
        data = await state.get_data()
        question = data.get("question", "")
        
        if callback.data == "ask_confirm":
            try:
                if not self.owner_id:
                    await callback.message.edit_text(
                        "❌ Ошибка: ID владельца не указан в настройках."
                    )
                    await state.clear()
                    await callback.answer()
                    return
                
                # Формируем сообщение для владельца
                user = callback.from_user
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                owner_message = (
                    f"❓ <b>ВОПРОС ОТ ПОЛЬЗОВАТЕЛЯ</b>\n\n"
                    f"👤 <b>Пользователь:</b>\n"
                    f"ID: {user.id}\n"
                    f"Имя: {user.first_name or 'Не указано'}\n"
                    f"Фамилия: {user.last_name or 'Не указано'}\n"
                    f"Username: @{user.username or 'Не указан'}\n\n"
                    f"💬 <b>Сообщение:</b>\n{question}\n\n"
                    f"⏰ <b>Время:</b> {timestamp}"
                )
                
                # Отправляем владельцу
                await self.bot.send_message(
                    chat_id=int(self.owner_id),
                    text=owner_message,
                    parse_mode="HTML"
                )
                
                # Подтверждаем пользователю
                await callback.message.edit_text(
                    "✅ <b>Ваш вопрос отправлен Дмитрию!</b>\n\n"
                    "Я уведомил его о вашем сообщении. Обычно он отвечает в течение 24 часов.\n\n"
                    "Спасибо за обращение! ✨",
                    parse_mode="HTML"
                )
                
                # Логируем
                logger.info(f"Question sent to owner from user {user.id}: {question[:50]}...")
                
            except Exception as e:
                logger.error(f"Error sending question to owner: {type(e).__name__}: {e}")
                await callback.message.edit_text(
                    "❌ <b>Произошла ошибка при отправке</b>\n\n"
                    "Пожалуйста, попробуйте позже или свяжитесь другим способом.",
                    parse_mode="HTML"
                )
        
        elif callback.data == "ask_cancel":
            await callback.message.edit_text("❌ Отправка вопроса отменена.")
        
        # Очищаем состояние
        await state.clear()
        await callback.answer()
    
    async def handle_quick_ask(self, message: Message):
        """Быстрая отправка вопроса через префикс 'вопрос:'"""
        # Извлекаем текст вопроса
        question_text = message.text.replace("вопрос:", "", 1).strip()
        
        if not question_text:
            await message.answer(
                "Пожалуйста, напишите вопрос после 'вопрос:'\n"
                "Пример: <i>вопрос: Как с вами можно сотрудничать?</i>",
                parse_mode="HTML"
            )
            return
        
        if not self.owner_id:
            await message.answer(
                "❌ Функция связи с владельцем временно недоступна."
            )
            return
        
        try:
            # Формируем сообщение для владельца
            user = message.from_user
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            owner_message = (
                f"❓ <b>ВОПРОС ОТ ПОЛЬЗОВАТЕЛЯ (быстрая отправка)</b>\n\n"
                f"👤 <b>Пользователь:</b>\n"
                f"ID: {user.id}\n"
                f"Имя: {user.first_name or 'Не указано'}\n"
                f"Фамилия: {user.last_name or 'Не указано'}\n"
                f"Username: @{user.username or 'Не указан'}\n\n"
                f"💬 <b>Сообщение:</b>\n{question_text}\n\n"
                f"⏰ <b>Время:</b> {timestamp}"
            )
            
            # Отправляем владельцу
            await self.bot.send_message(
                chat_id=int(self.owner_id),
                text=owner_message,
                parse_mode="HTML"
            )
            
            # Подтверждаем пользователю
            await message.answer(
                "✅ <b>Ваш вопрос отправлен Дмитрию!</b>\n\n"
                "Я уведомил его о вашем сообщении. Он ответит вам при первой возможности.",
                parse_mode="HTML"
            )
            
            # Логируем
            logger.info(f"Quick question sent to owner from user {user.id}")
            
        except Exception as e:
            logger.error(f"Error sending quick question: {type(e).__name__}: {e}")
            await message.answer(
                "❌ Не удалось отправить вопрос. Пожалуйста, попробуйте позже.",
                parse_mode="HTML"
            )
    
    async def cmd_cancel(self, message: Message, state: FSMContext):
        """Отмена любого состояния FSM"""
        current_state = await state.get_state()
        if current_state is None:
            await message.answer("Нет активных действий для отмены.")
            return
        
        await state.clear()
        await message.answer("❌ Действие отменено.")