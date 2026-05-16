"""
Модуль с днями рождения.
Содержит команды для добавления, просмотра и автоматические поздравления.
Данные хранятся на GitHub.
"""

from datetime import datetime
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from github_db import (
    add_birthday_to_github as add_birthday,
    get_all_birthdays_from_github as get_all_birthdays,
    get_today_birthdays_from_github as get_today_birthdays
)

# ========== FSM ==========
class BirthdayForm(StatesGroup):
    waiting_for_birthday = State()

# ========== ОБРАБОТЧИКИ КОМАНД ==========
router = Router()

@router.message(Command("birthday"))
async def birthday_command(message: Message, state: FSMContext):
    await message.answer(
        "🎂 Введите дату вашего дня рождения в формате **ДД-ММ**\n"
        "Например: 15-03\n\n"
        "Чтобы отменить - отправьте /cancel",
        parse_mode="Markdown"
    )
    await state.set_state(BirthdayForm.waiting_for_birthday)

@router.message(Command("cancel"))
async def cancel_command(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Действие отменено.")

@router.message(BirthdayForm.waiting_for_birthday)
async def process_birthday(message: Message, state: FSMContext):
    birthday = message.text.strip()
    if len(birthday) != 5 or birthday[2] != '-':
        await message.answer("❌ Неверный формат! Используйте ДД-ММ, например: 15-03")
        return
    day, month = birthday.split('-')
    if not (day.isdigit() and month.isdigit()):
        await message.answer("❌ День и месяц должны быть числами!")
        return
    day_num, month_num = int(day), int(month)
    if day_num < 1 or day_num > 31 or month_num < 1 or month_num > 12:
        await message.answer("❌ Неверная дата! День 1-31, месяц 1-12")
        return
    # Дополнительная проверка существования даты
    try:
        datetime.strptime(f"{day}-{month}-{datetime.now().year}", "%d-%m-%Y")
    except ValueError:
        await message.answer("❌ Такой даты не существует!")
        return

    if message.from_user.username:
        username = f"@{message.from_user.username}"
    else:
        username = message.from_user.first_name or "Дорогой одногруппник"

    add_birthday(message.from_user.id, username, birthday)
    await message.answer(f"✅ День рождения {birthday} сохранён! 🎉")
    await state.clear()

@router.message(Command("birthdays"))
async def show_birthdays(message: Message):
    birthdays = get_all_birthdays()
    if not birthdays:
        await message.answer("📭 Пока никто не добавил свой день рождения.")
        return
    birthdays_sorted = sorted(birthdays, key=lambda x: x[2])
    text = "🎂 **Список дней рождений:**\n\n"
    for _, username, bday in birthdays_sorted:
        text += f"• {username}: {bday}\n"
    await message.answer(text, parse_mode="Markdown")

# ========== АВТОМАТИЧЕСКИЕ ПРОВЕРКИ ==========
async def check_birthdays(bot, group_chat_id: int, topic_id: int):
    print(f"[{datetime.now()}] check_birthdays запущена")
    print(f"DEBUG: check_birthdays вызвана с bot={bot}, group_chat_id={group_chat_id}, topic_id={topic_id}")
    today_birthdays = get_today_birthdays()
    if not today_birthdays:
        return
    if len(today_birthdays) == 1:
        _, username = today_birthdays[0]
        text = f"🎉🎂 **С ДНЁМ РОЖДЕНИЯ, {username}!** 🎂🎉\n\nПоздравляем от всей группы! 🥳"
    else:
        names = [username for _, username in today_birthdays]
        text = f"🎉🎂 **С ДНЁМ РОЖДЕНИЯ!** 🎂🎉\n\nСегодня празднуют: {', '.join(names)}\n\nПоздравляем от всей группы! 🥳"
    try:
        await bot.send_message(
            chat_id=group_chat_id,
            message_thread_id=topic_id,
            text=text,
            parse_mode="Markdown"
        )
        print(f"Поздравление отправлено в топик {topic_id}")
    except Exception as e:
        print(f"Не удалось отправить: {e}")

# ========== РЕГИСТРАЦИЯ МОДУЛЯ ==========
def register_birthday_handlers(dp, bot, group_chat_id: int, topic_id: int):
    """Регистрирует обработчики и сохраняет параметры"""
    global _bot, _group_chat_id, _topic_id
    _bot = bot
    _group_chat_id = group_chat_id
    _topic_id = topic_id

    @router.message(Command("test_birthday"))
    async def test_birthday_group(message: Message):
        today_birthdays = get_today_birthdays()
        if not today_birthdays:
            text = "🧪 **Тестовое поздравление!** \n\nСегодня мог бы быть день рождения у... 🎂"
        else:
            names = [username for _, username in today_birthdays]
            text = f"🎉 **Тест!** \n\nСегодня день рождения у: {', '.join(names)} 🎂"
        try:
            await _bot.send_message(
                chat_id=_group_chat_id,
                message_thread_id=_topic_id,
                text=text,
                parse_mode="Markdown"
            )
            await message.answer("✅ Тестовое поздравление отправлено в группу!")
        except Exception as e:
            await message.answer(f"❌ Ошибка: {e}")

    dp.include_router(router)