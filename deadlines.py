"""
Модуль с дедлайнами.
Команды: /add_deadline, /deadlines, /deadlines [предмет], /old_deadlines, /del_deadline
Данные хранятся на GitHub.
"""

from datetime import datetime, timedelta
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import Message

from github_db import (
    add_deadline_to_github as add_deadline,
    get_all_deadlines_from_github as get_all_deadlines,
    get_deadlines_by_subject_from_github as get_deadlines_by_subject,
    get_past_deadlines_from_github as get_past_deadlines,
    delete_deadline_from_github as delete_deadline
)

# ========== НАСТРОЙКИ ==========
ADMIN_USER_ID = 1337585530  

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
    args = message.text.split(maxsplit=1)
    if len(args) > 1:
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
        deadlines = get_all_deadlines()
        if not deadlines:
            await message.answer("📭 Нет дедлайнов для удаления.")
            return
        text = format_deadline_for_admin(deadlines)
        await message.answer(text, parse_mode="Markdown")
        return
    
    try:
        deadline_id = int(args[1])
    except ValueError:
        await message.answer("❌ ID должен быть числом!")
        return
    
    if delete_deadline(deadline_id, ADMIN_USER_ID):
        await message.answer(f"✅ Дедлайн {deadline_id} удалён!")
    else:
        await message.answer(f"❌ Дедлайн {deadline_id} не найден или не принадлежит вам.")

# ========== АВТОМАТИЧЕСКИЕ НАПОМИНАНИЯ ==========
async def check_deadlines(bot, group_chat_id: int, topic_id: int):
    print(f"[{datetime.now()}] check_deadlines запущена")
    """Отправляет в группу напоминания о дедлайнах на сегодня и завтра"""
    today_str = datetime.now().strftime("%Y-%m-%d")
    tomorrow_str = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    all_deadlines = get_all_deadlines()
    upcoming = [d for d in all_deadlines if d[3] in (today_str, tomorrow_str)]
    
    if not upcoming:
        return
    
    today_items = [d for d in upcoming if d[3] == today_str]
    tomorrow_items = [d for d in upcoming if d[3] == tomorrow_str]
    
    text = "📚 **Напоминание о дедлайнах:**\n\n"
    
    if today_items:
        text += "🔴 **СЕГОДНЯ:**\n"
        for _, subject, title, _, comment in today_items:
            text += f"   • {subject}: {title}"
            if comment:
                text += f" ({comment})"
            text += "\n"
        text += "\n"
    
    if tomorrow_items:
        text += "🟡 **ЗАВТРА:**\n"
        for _, subject, title, _, comment in tomorrow_items:
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
    
    # Подключаем роутер к диспетчеру
    dp.include_router(router)