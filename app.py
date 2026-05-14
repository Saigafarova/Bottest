import asyncio
import os
import threading
from flask import Flask
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import pytz
from deadlines import register_deadline_handlers, check_deadlines, ADMIN_USER_ID
import sqlite3
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()
DB_NAME = "bot_database.db"
from deadlines import register_deadline_handlers, check_deadlines, ADMIN_USER_ID
def init_db():
    """Создаёт таблицы, если их нет"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Таблица для дней рождения
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS birthdays (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            birthday TEXT NOT NULL
        )
    ''')
    
    conn.commit()
    conn.close()
    print("База данных готова!")

def add_birthday(user_id: int, username: str, birthday: str):
    """Добавляет или обновляет день рождения пользователя"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO birthdays (user_id, username, birthday)
        VALUES (?, ?, ?)
    ''', (user_id, username, birthday))
    conn.commit()
    conn.close()

def get_all_birthdays():
    """Возвращает все дни рождения из базы"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, username, birthday FROM birthdays')
    results = cursor.fetchall()
    conn.close()
    return results

def get_today_birthdays():
    """Возвращает список именинников на сегодня"""
    today = datetime.now().strftime("%d-%m")
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, username FROM birthdays WHERE birthday = ?', (today,))
    results = cursor.fetchall()
    conn.close()
    return results
# ========== НАСТРОЙКИ ==========
TOKEN = os.environ.get("TELEGRAM_TOKEN")  # Токен из переменных окружения Render
GROUP_CHAT_ID = -1003994088941  # ID твоей группы
TOPIC_BIRTHDAYS = 5  # ID топика для поздравлений
TOPIC_DEADLINES = 112  # ← ЗАМЕНИ НА РЕАЛЬНЫЙ ID топика "Дедлайны" (узнай через @getmyid_bot)
if not TOKEN:
    raise ValueError("Переменная TELEGRAM_TOKEN не установлена!")

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Инициализируем базу данных при запуске
init_db()

# ========== FSM для добавления дня рождения ==========
class BirthdayForm(StatesGroup):
    waiting_for_birthday = State()

# ========== ОБРАБОТЧИКИ КОМАНД (твои старые обработчики) ==========
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


# ========== ФУНКЦИЯ ДЛЯ ПРОВЕРКИ ДНЕЙ РОЖДЕНИЙ ==========
async def check_birthdays():
    """Проверяет дни рождения и отправляет поздравление в группу"""
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
            message_thread_id=TOPIC_BIRTHDAYS,
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
            chat_id=GROUP_CHAT_ID,
            message_thread_id=TOPIC_BIRTHDAYS,
            text=text,
            parse_mode="Markdown"
        )
        await message.answer("✅ Тестовое поздравление отправлено в группу!")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")


# ========== ЗАПУСК БОТА ==========
async def start_bot():
    """Запускает планировщик и polling бота"""
    scheduler = AsyncIOScheduler(timezone=pytz.timezone('Europe/Moscow'))
    scheduler.add_job(check_birthdays, 'cron', hour=9, minute=0)
    scheduler.add_job(lambda: check_deadlines(bot, GROUP_CHAT_ID, TOPIC_DEADLINES), 'cron', hour=9, minute=5)
    scheduler.add_job(check_deadlines, 'cron', hour=9, minute=5)
    scheduler.start()
    print("🤖 Бот запущен! Планировщик активен.")
    await dp.start_polling(bot)

# ========== ВЕБ-СЕРВЕР ДЛЯ RENDER ==========
# Это чтобы Render не ругался, что нет открытого порта
app = Flask(__name__)

@app.route('/')
def home():
    return "Бот работает!", 200

@app.route('/health')
def health():
    return "OK", 200

def run_flask():
    """Запускает Flask-сервер в отдельном потоке"""
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

# ========== ТОЧКА ВХОДА ==========
if __name__ == "__main__":
    # Запускаем Flask в фоновом потоке
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()
    register_deadline_handlers(dp)
        register_deadline_handlers(dp, GROUP_CHAT_ID, TOPIC_DEADLINES)
    # Запускаем бота (в основном потоке, так как asyncio.run() должен быть в главном)
    asyncio.run(start_bot())