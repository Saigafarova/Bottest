"""
Модуль с дедлайнами.
Команды: /add_deadline, /deadlines, /deadlines [предмет], /old_deadlines, /del_deadline
"""
from datetime import datetime, timedelta
import sqlite3
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import Message

# ========== НАСТРОЙКИ ==========
ADMIN_USER_ID = 1337585530
DB_NAME = "bot_database.db"

# ========== ФУНКЦИИ БАЗЫ ДАННЫХ ==========

def init_deadlines_table():
    """Создаёт таблицу для дедлайнов с новой структурой (старые данные удаляются)"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Удаляем старую таблицу, если есть
    cursor.execute("DROP TABLE IF EXISTS deadlines")
    
    # Создаём новую
    cursor.execute('''
        CREATE TABLE deadlines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            title TEXT NOT NULL,
            deadline_date TEXT NOT NULL,
            comment TEXT,
            created_by INTEGER
        )
    ''')
    conn.commit()
    conn.close()
    print("✅ Таблица дедлайнов создана (старые данные удалены)")

def add_deadline(subject: str, title: str, deadline_date: str, comment: str, created_by: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO deadlines (subject, title, deadline_date, comment, created_by)
        VALUES (?, ?, ?, ?, ?)
    ''', (subject, title, deadline_date, comment, created_by))
    conn.commit()
    last_id = cursor.lastrowid
    conn.close()
    return last_id

def get_all_deadlines():
    """Возвращает все дедлайны (сортировка по дате)"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, subject, title, deadline_date, comment FROM deadlines
        ORDER BY deadline_date ASC
    ''')
    results = cursor.fetchall()
    conn.close()
    return results

def get_deadlines_by_subject(subject: str):
    """Возвращает дедлайны по предмету (сортировка по дате)"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, subject, title, deadline_date, comment FROM deadlines
        WHERE LOWER(subject) = LOWER(?)
        ORDER BY deadline_date ASC
    ''', (subject,))
    results = cursor.fetchall()
    conn.close()
    return results

def get_past_deadlines():
    """Возвращает дедлайны с датой раньше сегодня"""
    today = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, subject, title, deadline_date, comment FROM deadlines
        WHERE deadline_date < ?
        ORDER BY deadline_date ASC
    ''', (today,))
    results = cursor.fetchall()
    conn.close()
    return results

def delete_deadline_by_id(deadline_id: int, user_id: int):
    """Удаляет дедлайн по ID (только если пользователь — создатель)"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM deadlines WHERE id = ? AND created_by = ?', (deadline_id, user_id))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

def get_all_subjects():
    """Возвращает список всех предметов, у которых есть дедлайны"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT subject FROM deadlines ORDER BY subject')
    results = [row[0] for row in cursor.fetchall()]
    conn.close()
    return results

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ ФОРМАТИРОВАНИЯ ==========

def format_deadline_list(deadlines):
    """Форматирует список дедлайнов в читаемый текст (группировка по предметам)"""
    if not deadlines:
        return None
    
    # Группируем по предметам
    groups = {}
    for _, subject, title, date_str, comment in deadlines:
        if subject not in groups:
            groups[subject] = []
        groups[subject].append((title, date_str, comment))
    
    # Формируем текст
    text = ""
    for subject in sorted(groups.keys()):
        text += f"\n**{subject}**\n"
        for title, date_str, comment in groups[subject]:
            # Преобразуем дату в формат ДД.ММ.ГГГГ
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            formatted_date = date_obj.strftime("%d.%m.%Y")
            text += f"   • **{title}**\n      ⏰ {formatted_date}"
            if comment:
                text += f"\n      📝 {comment}"
            text += "\n"
    
    return text

def format_deadline_for_admin(deadlines):
    """Форматирует список дедлайнов с ID (только для админа)"""
    if not deadlines:
        return None
    
    text = "📋 **Ваши дедлайны (для удаления):**\n\n"
    for did, subject, title, date_str, comment in deadlines:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        formatted_date = date_obj.strftime("%d.%m.%Y")
        text += f"`{did}` — {subject}: {title} ({formatted_date})\n"
    text += "\n_Введите /del_deadline ID_ (например, /del_deadline 3)"
    return text

# ========== ОБРАБОТЧИКИ КОМАНД ==========

router = Router()

@router.message(Command("add_deadline"))
async def add_deadline_command(message: Message):
    """Добавляет новый дедлайн. Формат: /add_deadline Предмет | Название | ГГГГ-ММ-ДД | Комментарий"""
    if message.from_user.id != ADMIN_USER_ID:
        await message.answer("❌ Только староста может добавлять дедлайны.")
        return
    
    text = message.text.replace("/add_deadline", "").strip()
    parts = text.split("|")
    parts = [p.strip() for p in parts]
    
    if len(parts) < 3:
        await message.answer(
            "❌ Неверный формат!\n\n"
            "Используйте:\n"
            "`/add_deadline Предмет | Название | ГГГГ-ММ-ДД`\n"
            "или с комментарием:\n"
            "`/add_deadline Предмет | Название | ГГГГ-ММ-ДД | Комментарий`\n\n"
            "Пример:\n"
            "`/add_deadline Матан | Лабораторная работа №3 | 2026-05-25 | Выполнить задания 1-5`",
            parse_mode="Markdown"
        )
        return
    
    subject = parts[0]
    title = parts[1]
    date_str = parts[2]
    comment = parts[3] if len(parts) > 3 else ""
    
    # Проверка формата даты
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        await message.answer("❌ Неверный формат даты! Используйте ГГГГ-ММ-ДД, например: 2026-05-25")
        return
    
    deadline_id = add_deadline(subject, title, date_str, comment, message.from_user.id)
    
    reply = f"✅ **Дедлайн добавлен!**\n📚 {subject}\n📌 {title}\n⏰ {date_str}"
    if comment:
        reply += f"\n📝 {comment}"
    
    await message.answer(reply, parse_mode="Markdown")

@router.message(Command("deadlines"))
async def show_deadlines(message: Message):
    """Показывает все дедлайны (будущие и прошедшие), сгруппированные по предметам"""
    # Проверяем, есть ли аргумент (предмет)
    args = message.text.split(maxsplit=1)
    if len(args) > 1:
        # /deadlines матан
        subject = args[1]
        deadlines = get_deadlines_by_subject(subject)
        if not deadlines:
            await message.answer(f"📭 По предмету «{subject}» пока нет дедлайнов.")
            return
        text = format_deadline_list(deadlines)
        if text:
            await message.answer(f"📚 **Дедлайны по предмету «{subject}»:**{text}", parse_mode="Markdown")
        else:
            await message.answer(f"📭 По предмету «{subject}» пока нет дедлайнов.")
    else:
        # /deadlines (все предметы)
        deadlines = get_all_deadlines()
        if not deadlines:
            await message.answer("📭 Пока нет ни одного дедлайна.")
            return
        text = format_deadline_list(deadlines)
        await message.answer(f"📚 **Все дедлайны:**{text}", parse_mode="Markdown")

@router.message(Command("old_deadlines"))
async def show_old_deadlines(message: Message):
    """Показывает только прошедшие дедлайны"""
    deadlines = get_past_deadlines()
    if not deadlines:
        await message.answer("📭 Нет прошедших дедлайнов.")
        return
    text = format_deadline_list(deadlines)
    await message.answer(f"⏰ **Прошедшие дедлайны:**{text}", parse_mode="Markdown")

@router.message(Command("del_deadline"))
async def delete_deadline_command(message: Message):
    """Удаляет дедлайн по ID (только для админа)"""
    if message.from_user.id != ADMIN_USER_ID:
        await message.answer("❌ Только староста может удалять дедлайны.")
        return
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        # Если ID не указан — показываем список дедлайнов с ID
        deadlines = get_all_deadlines()
        if not deadlines:
            await message.answer("📭 Нет дедлайнов для удаления.")
            return
        text = format_deadline_for_admin(deadlines)
        await message.answer(text, parse_mode="Markdown")
        return
    
    # Если ID указан — пробуем удалить
    try:
        deadline_id = int(args[1])
    except ValueError:
        await message.answer("❌ ID должен быть числом!")
        return
    
    if delete_deadline_by_id(deadline_id, ADMIN_USER_ID):
        await message.answer(f"✅ Дедлайн {deadline_id} удалён!")
    else:
        await message.answer(f"❌ Дедлайн {deadline_id} не найден или не принадлежит вам.")

# ========== АВТОМАТИЧЕСКИЕ НАПОМИНАНИЯ ==========
async def check_deadlines(bot, group_chat_id: int, topic_id: int):
    """Отправляет в группу напоминания о дедлайнах на сегодня и завтра"""
    today_str = datetime.now().strftime("%Y-%m-%d")
    tomorrow_str = (datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)).strftime("%Y-%m-%d")
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT subject, title, deadline_date, comment FROM deadlines
        WHERE deadline_date IN (?, ?)
        ORDER BY deadline_date ASC
    ''', (today_str, tomorrow_str))
    upcoming = cursor.fetchall()
    conn.close()
    
    if not upcoming:
        return
    
    # Группируем по датам
    today_items = []
    tomorrow_items = []
    for subject, title, date_str, comment in upcoming:
        if date_str == today_str:
            today_items.append((subject, title, comment))
        else:
            tomorrow_items.append((subject, title, comment))
    
    text = "📚 **Напоминание о дедлайнах:**\n\n"
    
    if today_items:
        text += "🔴 **СЕГОДНЯ:**\n"
        for subject, title, comment in today_items:
            text += f"   • {subject}: {title}"
            if comment:
                text += f" ({comment})"
            text += "\n"
        text += "\n"
    
    if tomorrow_items:
        text += "🟡 **ЗАВТРА:**\n"
        for subject, title, comment in tomorrow_items:
            text += f"   • {subject}: {title}"
            if comment:
                text += f" ({comment})"
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
    global _group_chat_id, _topic_id, _bot
    _group_chat_id = group_chat_id
    _topic_id = topic_id
    
    # Создаём таблицу (старые данные удаляются!)
    init_deadlines_table()
    
    # Подключаем роутер к диспетчеру
    dp.include_router(router)