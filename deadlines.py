"""
Модуль с дедлайнами и администрированием.
Содержит команды для добавления, просмотра и удаления дедлайнов,
а также автоматические утренние напоминания.
"""

import sqlite3
from datetime import datetime, timedelta
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import Message

# ========== НАСТРОЙКИ ==========
# ⚠️ ЗАМЕНИ НА СВОЙ TELEGRAM ID (можно узнать у бота @userinfobot)
ADMIN_USER_ID = 123456789  # ← СЮДА ВСТАВЬ СВОЙ ID

# ID группы и топика для дедлайнов (возьмём из app.py позже)
# Пока оставим пустыми, заполним при регистрации
GROUP_CHAT_ID = None
TOPIC_DEADLINES_ID = None

# ========== ФУНКЦИИ БАЗЫ ДАННЫХ ==========
DB_NAME = "bot_database.db"

def init_deadlines_table():
    """Создаёт таблицу для дедлайнов, если её нет"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS deadlines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            deadline_date TEXT NOT NULL,
            comment TEXT,
            created_by INTEGER,
            is_completed INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

def add_deadline(title: str, deadline_date: str, comment: str, created_by: int):
    """Добавляет новый дедлайн"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO deadlines (title, deadline_date, comment, created_by)
        VALUES (?, ?, ?, ?)
    ''', (title, deadline_date, comment, created_by))
    conn.commit()
    last_id = cursor.lastrowid
    conn.close()
    return last_id

def get_all_deadlines():
    """Возвращает все незавершённые дедлайны, сортирует по дате"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, title, deadline_date, comment FROM deadlines
        WHERE is_completed = 0
        ORDER BY deadline_date ASC
    ''')
    results = cursor.fetchall()
    conn.close()
    return results

def get_deadlines_for_date(date_str: str):
    """Возвращает дедлайны на конкретную дату"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, title, comment FROM deadlines
        WHERE deadline_date = ? AND is_completed = 0
    ''', (date_str,))
    results = cursor.fetchall()
    conn.close()
    return results

def get_upcoming_deadlines(days: int = 2):
    """Возвращает дедлайны на ближайшие N дней (включая сегодня)"""
    today = datetime.now().strftime("%Y-%m-%d")
    future = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, title, deadline_date, comment FROM deadlines
        WHERE deadline_date >= ? AND deadline_date <= ? AND is_completed = 0
        ORDER BY deadline_date ASC
    ''', (today, future))
    results = cursor.fetchall()
    conn.close()
    return results

def delete_deadline(deadline_id: int, user_id: int):
    """Удаляет дедлайн (только если пользователь — создатель)"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM deadlines WHERE id = ? AND created_by = ?', (deadline_id, user_id))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

# ========== КОМАНДЫ БОТА ==========
router = Router()

@router.message(Command("add_deadline"))
async def add_deadline_command(message: Message):
    """Добавляет новый дедлайн. Доступно только админу."""
    if message.from_user.id != ADMIN_USER_ID:
        await message.answer("❌ Извини, только староста может добавлять дедлайны.")
        return
    
    # Разбираем сообщение: /add_deadline Название | ГГГГ-ММ-ДД | Комментарий
    text = message.text.replace("/add_deadline", "").strip()
    parts = text.split("|")
    parts = [p.strip() for p in parts]
    
    if len(parts) < 2:
        await message.answer(
            "❌ Неверный формат!\n\n"
            "**Вариант 1 (без комментария):**\n"
            "`/add_deadline Название | ГГГГ-ММ-ДД`\n\n"
            "**Вариант 2 (с комментарием):**\n"
            "`/add_deadline Название | ГГГГ-ММ-ДД | Комментарий`\n\n"
            "Пример:\n"
            "`/add_deadline Лаба по матану | 2026-05-25 | Выполнить задания 1-5`",
            parse_mode="Markdown"
        )
        return
    
    title = parts[0]
    date_str = parts[1]
    comment = parts[2] if len(parts) > 2 else ""
    
    # Проверка формата даты
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        await message.answer("❌ Неверный формат даты! Используйте ГГГГ-ММ-ДД, например: 2026-05-25")
        return
    
    deadline_id = add_deadline(title, date_str, comment, message.from_user.id)
    
    reply = f"✅ **Дедлайн добавлен!** (ID: {deadline_id})\n📌 {title}\n⏰ {date_str}"
    if comment:
        reply += f"\n📝 {comment}"
    
    await message.answer(reply, parse_mode="Markdown")

@router.message(Command("deadlines"))
async def show_deadlines(message: Message):
    """Показывает все предстоящие дедлайны (доступно всем)"""
    deadlines = get_all_deadlines()
    
    if not deadlines:
        await message.answer("📭 Пока нет ни одного дедлайна.")
        return
    
    text = "📋 **Предстоящие дедлайны:**\n\n"
    for did, title, date_str, comment in deadlines:
        text += f"**{did}.** {title}\n   ⏰ {date_str}"
        if comment:
            text += f"\n   📝 {comment}"
        text += "\n\n"
    
    await message.answer(text, parse_mode="Markdown")

@router.message(Command("del_deadline"))
async def delete_deadline_command(message: Message):
    """Удаляет дедлайн по ID (только для админа)"""
    if message.from_user.id != ADMIN_USER_ID:
        await message.answer("❌ Только староста может удалять дедлайны.")
        return
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("❌ Укажите ID дедлайна.\nПример: `/del_deadline 3`", parse_mode="Markdown")
        return
    
    try:
        deadline_id = int(args[1])
    except ValueError:
        await message.answer("❌ ID должен быть числом!")
        return
    
    if delete_deadline(deadline_id, ADMIN_USER_ID):
        await message.answer(f"✅ Дедлайн {deadline_id} удалён!")
    else:
        await message.answer(f"❌ Дедлайн {deadline_id} не найден.")

# ========== АВТОМАТИЧЕСКИЕ НАПОМИНАНИЯ ==========
async def check_deadlines(bot, group_chat_id: int, topic_id: int):
    """Отправляет в группу напоминания о ближайших дедлайнах (сегодня и завтра)"""
    upcoming = get_upcoming_deadlines(days=2)
    
    if not upcoming:
        return
    
    # Группируем по датам
    deadlines_by_date = {}
    for did, title, date_str, comment in upcoming:
        if date_str not in deadlines_by_date:
            deadlines_by_date[date_str] = []
        deadlines_by_date[date_str].append((title, comment))
    
    today = datetime.now().strftime("%Y-%m-%d")
    text = "📚 **Напоминание о дедлайнах:**\n\n"
    
    for date_str, items in deadlines_by_date.items():
        if date_str == today:
            text += "🔴 **СЕГОДНЯ:**\n"
        else:
            # Преобразуем дату в читаемый формат
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            formatted_date = date_obj.strftime("%d.%m.%Y")
            text += f"🟡 **{formatted_date}:**\n"
        
        for title, comment in items:
            text += f"   • {title}"
            if comment:
                text += f" ({comment})"
            text += "\n"
        text += "\n"
    
    try:
        await bot.send_message(
            chat_id=group_chat_id,
            message_thread_id=topic_id,
            text=text,
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"Не удалось отправить напоминание о дедлайнах: {e}")

# ========== РЕГИСТРАЦИЯ МОДУЛЯ ==========
def register_deadline_handlers(dp, group_chat_id: int, topic_id: int):
    """Регистрирует обработчики команд и передаёт ID группы и топика"""
    global GROUP_CHAT_ID, TOPIC_DEADLINES_ID
    GROUP_CHAT_ID = group_chat_id
    TOPIC_DEADLINES_ID = topic_id
    
    # Инициализируем таблицу в БД
    init_deadlines_table()
    
    # Подключаем роутер к диспетчеру
    dp.include_router(router)