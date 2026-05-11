import asyncio
import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
import pytz
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

# Импортируем нашу базу данных
from database import init_db, add_birthday, get_all_birthdays, get_today_birthdays
GROUP_CHAT_ID = -1003994088941 
TOPIC_BIRTHDAYS = 5
TOKEN = "8261368233:AAEi1IDTo3HJ_xoxemn6Fmz41yh4Nz1sB-w"

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Инициализируем базу данных при запуске
init_db()

# ========== FSM для добавления дня рождения ==========
class BirthdayForm(StatesGroup):
    waiting_for_birthday = State()

# ========== ОБРАБОТЧИКИ КОМАНД ==========

@dp.message(Command("start"))
async def start_command(message: Message):
    await message.answer(
        "🎉 Привет! Я бот-староста!\n\n"
        "Доступные команды:\n"
        "/birthday - добавить/обновить день рождения\n"
        "/birthdays - показать все дни рождения\n"
        "/help - помощь"
    )

@dp.message(Command("help"))
async def help_command(message: Message):
    await message.answer(
        "📋 Команды бота:\n\n"
        "/birthday - добавить или обновить свой день рождения\n"
        "/birthdays - показать список всех дней рождений в группе\n"
        "/start - приветствие\n"
        "/help - эта справка"
    )

@dp.message(Command("birthday"))
async def birthday_command(message: Message, state: FSMContext):
    """Начинает диалог добавления дня рождения"""
    await message.answer(
        "🎂 Введите дату вашего дня рождения в формате **ДД-ММ**\n"
        "Например: 15-03\n\n"
        "Чтобы отменить - отправьте /cancel",
        parse_mode="Markdown"
    )
    await state.set_state(BirthdayForm.waiting_for_birthday)

@dp.message(Command("cancel"))
async def cancel_command(message: Message, state: FSMContext):
    """Отменяет текущий диалог"""
    await state.clear()
    await message.answer("❌ Действие отменено.")

@dp.message(BirthdayForm.waiting_for_birthday)
async def process_birthday(message: Message, state: FSMContext):
    """Обрабатывает введённую дату и сохраняет в БД"""
    birthday = message.text.strip()
    
    # Простая проверка формата ДД-ММ
    if len(birthday) != 5 or birthday[2] != '-':
        await message.answer("❌ Неверный формат! Используйте ДД-ММ, например: 15-03")
        return
    
    day, month = birthday.split('-')
    if not (day.isdigit() and month.isdigit()):
        await message.answer("❌ День и месяц должны быть числами! Например: 15-03")
        return
    
    day_num, month_num = int(day), int(month)
    if day_num < 1 or day_num > 31 or month_num < 1 or month_num > 12:
        await message.answer("❌ Неверная дата! День от 1 до 31, месяц от 1 до 12")
        return
    
    # Сохраняем в базу
    username = message.from_user.first_name or message.from_user.username or "Друг"
    add_birthday(message.from_user.id, username, birthday)
    
    await message.answer(f"✅ День рождения {birthday} сохранён! 🎉")
    await state.clear()

@dp.message(Command("birthdays"))
async def show_birthdays(message: Message):
    """Показывает все дни рождения"""
    birthdays = get_all_birthdays()
    
    if not birthdays:
        await message.answer("📭 Пока никто не добавил свой день рождения.")
        return
    
    # Сортируем по дате
    birthdays_sorted = sorted(birthdays, key=lambda x: x[2])
    
    text = "🎂 **Список дней рождений:**\n\n"
    for user_id, username, bday in birthdays_sorted:
        text += f"• {username}: {bday}\n"
    
    await message.answer(text, parse_mode="Markdown")

async def check_birthdays():
    today_birthdays = get_today_birthdays()
    if not today_birthdays:
        return
    
    if len(today_birthdays) == 1:
        user_id, username = today_birthdays[0]
        text = f"🎉🎂 **С ДНЁМ РОЖДЕНИЯ, {username}!** 🎂🎉\n\nПоздравляем от всей группы! 🥳"
    else:
        names = [username for _, username in today_birthdays]
        text = f"🎉🎂 **С ДНЁМ РОЖДЕНИЯ!** 🎂🎉\n\nСегодня празднуют: {', '.join(names)}\n\nПоздравляем от всей группы! 🥳"
    
    try:
        await bot.send_message(
            chat_id=GROUP_CHAT_ID,
            message_thread_id=TOPIC_BIRTHDAYS,  # ← ГЛАВНОЕ ДОБАВЛЕНИЕ
            text=text,
            parse_mode="Markdown"
        )
        print(f"Поздравление отправлено в топик {TOPIC_BIRTHDAYS}")
    except Exception as e:
        print(f"Не удалось отправить: {e}")

@dp.message(Command("slot"))
async def slot_machine(message: Message):
    """Отправляет анимированный слот"""
    try:
        await bot.send_dice(
            chat_id=message.chat.id,
            message_thread_id=message.message_thread_id,  # если в топике
            emoji="🎰"
        )
    except Exception as e:
        await message.answer("😔 Не получилось запустить слот...")


@dp.message(Command("test_group"))
async def test_group(message: Message):
    try:
        await bot.send_message(
            chat_id=GROUP_CHAT_ID,  # без message_thread_id
            text="🧪 Тест! Бот работает в группе"
        )
        await message.answer("✅ Сообщение отправлено в группу!")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")


@dp.message(Command("test_birthday"))
async def test_birthday_group(message: Message):
    """Принудительно проверяет дни рождения и отправляет поздравление в группу"""
    # Временно подставим тестового именинника
    today_birthdays = get_today_birthdays()
    
    if not today_birthdays:
        # Если сегодня ничьей нет, создадим тестовое сообщение
        text = "🧪 **Тестовое поздравление!** \n\nСегодня мог бы быть день рождения у... 🎂"
    else:
        # Если есть реальные именинники
        names = [username for _, username in today_birthdays]
        text = f"🎉 **Тест!** \n\nСегодня день рождения у: {', '.join(names)} 🎂"
    
    try:
        await bot.send_message(
            chat_id=-1003994088941,
            message_thread_id=5,
            text=text,
            parse_mode="Markdown"
        )
        await message.answer("✅ Тестовое поздравление отправлено в группу!")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")





# ========== ЗАПУСК БОТА ==========
async def main():
    # Настраиваем планировщик
    scheduler = AsyncIOScheduler(timezone=pytz.timezone('Europe/Moscow'))
    
    # Добавляем задачу: каждый день в 9:00 проверять дни рождения
    scheduler.add_job(check_birthdays, 'cron', hour=9, minute=0)
    
    scheduler.start()
    print("🤖 Бот запущен! Планировщик активен.")
    
    await dp.start_polling(bot)



if __name__ =="__main__":
    asyncio.run(main())