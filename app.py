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
from datetime import datetime
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
    scheduler = AsyncIOScheduler(timezone=pytz.timezone('Europe/Moscow'))
    
    # Дни рождения
    scheduler.add_job(
        check_birthdays, 
        'cron', 
        hour=9, 
        minute=0,
        args=(bot, GROUP_CHAT_ID, TOPIC_BIRTHDAYS),
        id='birthdays_daily',
        replace_existing=True
    )
    
    # Дедлайны
    scheduler.add_job(
        check_deadlines, 
        'cron', 
        hour=9, 
        minute=5,
        args=(bot, GROUP_CHAT_ID, TOPIC_DEADLINES),
        id='deadlines_daily',
        replace_existing=True
    )
    
    scheduler.start()
    
    print("✅ Планировщик APScheduler успешно запущен!")
    print(f"   → Дни рождения: каждый день в 9:00")
    print(f"   → Дедлайны: каждый день в 9:05")
    
    # Показываем текущее время сервера (удобно для проверки)
    moscow_time = datetime.now(pytz.timezone('Europe/Moscow'))
    print(f"   → Текущее время на сервере: {moscow_time.strftime('%H:%M:%S')}")

    print("🤖 Запускаем polling бота...")
    await dp.start_polling(bot)
# ========== ВЕБ-СЕРВЕР ДЛЯ RENDER ==========

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
    flask_thread = threading.Thread(target=run_flask, daemon=True)  # ← Вот здесь добавили daemon=True
    flask_thread.start()
    
    # Регистрируем обработчики (ВАЖНО: перед запуском бота!)
    register_deadline_handlers(dp, GROUP_CHAT_ID, TOPIC_DEADLINES)
    register_birthday_handlers(dp, bot, GROUP_CHAT_ID, TOPIC_BIRTHDAYS)
    
    # Запускаем бота
    asyncio.run(start_bot())