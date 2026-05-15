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
from dotenv import load_dotenv
from birthdays import register_birthday_handlers, check_birthdays
print("Проверка: модули загружены. Регистрируем команды...")
load_dotenv()
# ========== НАСТРОЙКИ ==========
TOKEN = os.environ.get("TELEGRAM_TOKEN")  # Токен из переменных окружения Render
GROUP_CHAT_ID = -1003994088941 
TOPIC_BIRTHDAYS = 5  
TOPIC_DEADLINES = 112  
if not TOKEN:
    raise ValueError("Переменная TELEGRAM_TOKEN не установлена!")

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


# ========== ОБРАБОТЧИКИ КОМАНД (твои старые обработчики) ==========
@dp.message(Command("start"))
async def start_command(message: Message):
    await message.answer(
        "🎉 Привет! Я бот-староста!\n\n"
        "Доступные команды:\n"
        "/birthday - добавить/обновить день рождения\n"
        "/birthdays - показать все дни рождения\n"
        "Другие команды находятся пока в разработке, но скоро будут! 😉\n\n"
        "А пока что можешь попробовать /help для получения списка всех команд, когда они будут готовы!"
    )

@dp.message(Command("help"))
async def help_command(message: Message):
    await message.answer(
        "📋 **Команды бота:**\n\n"
        "**Дни рождения:**\n"
        "/birthday - добавить свой день рождения\n"
        "/birthdays - показать все дни рождения\n\n"
        "**Дедлайны:**\n"
        "/deadlines - показать список дедлайнов\n"
        "/add\\_deadline - добавить дедлайн (только для старосты)\n"
        "/del\\_deadline - удалить дедлайн (только для старосты)\n\n"
        "**Игры:**\n"
        "/slot - слот-машина 🎰\n\n"
        "/start - приветствие\n"
        "/help - эта справка",
        parse_mode="Markdown"
    )




# ========== ФУНКЦИЯ ДЛЯ ПРОВЕРКИ ДНЕЙ РОЖДЕНИЙ ==========

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


# ========== ЗАПУСК БОТА ==========
async def start_bot():
    """Запускает планировщик и polling бота"""
    scheduler = AsyncIOScheduler(timezone=pytz.timezone('Europe/Moscow'))
    scheduler.add_job(lambda: check_birthdays(bot, GROUP_CHAT_ID, TOPIC_BIRTHDAYS), 'cron', hour=9, minute=0)
    scheduler.add_job(lambda: check_deadlines(bot, GROUP_CHAT_ID, TOPIC_DEADLINES), 'cron', hour=9, minute=5)
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



@dp.message(Command("test_deadline"))
async def test_deadline_cmd(message: Message):
    await message.answer("✅ Команда test_deadline работает! Если вы это видите — бот вообще работает, проблема в подключении deadlines.py")

# Проверка, что обработчики дедлайнов зарегистрированы
print("Проверка: в app.py зарегистрированы обработчики дедлайнов")
# ========== ТОЧКА ВХОДА ==========

if __name__ == "__main__":
    # Запускаем Flask в фоновом потоке
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()
    
    # Регистрируем обработчики дедлайнов
    register_deadline_handlers(dp, GROUP_CHAT_ID, TOPIC_DEADLINES)
    register_birthday_handlers(dp, bot, GROUP_CHAT_ID, TOPIC_BIRTHDAYS)
    # Запускаем бота
    asyncio.run(start_bot())