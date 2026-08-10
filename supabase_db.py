import os
from supabase import create_client, Client
from datetime import datetime
from typing import Optional, List, Tuple

# ========== ПОДКЛЮЧЕНИЕ К SUPABASE ==========
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Переменные SUPABASE_URL и SUPABASE_KEY должны быть установлены!")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# ========== ДНИ РОЖДЕНИЯ ==========

def add_birthday(user_id: int, username: str, birthday: str) -> bool:
    """Добавляет или обновляет день рождения. Возвращает True при успехе."""
    try:
        data = {
            "user_id": user_id,
            "username": username,
            "birthday": birthday
        }
        # Лучше использовать upsert (нужен UNIQUE на user_id)
        supabase.table("birthdays").insert(data).execute()
        print(f"День рождения {username} сохранён")
        return True
    except Exception as e:
        print(f"[ERROR] add_birthday: {e}")
        return False


def get_all_birthdays() -> List[Tuple[int, str, str]]:
    """Возвращает все дни рождения"""
    try:
        response = supabase.table("birthdays").select("*").execute()
        return [(row["user_id"], row["username"], row["birthday"]) for row in response.data]
    except Exception as e:
        print(f"[ERROR] get_all_birthdays: {e}")
        return []


def get_today_birthdays() -> List[Tuple[int, str]]:
    """Возвращает список именинников на сегодня"""
    try:
        today = datetime.now().strftime("%d-%m")
        response = supabase.table("birthdays").select("*").eq("birthday", today).execute()
        return [(row["user_id"], row["username"]) for row in response.data]
    except Exception as e:
        print(f"[ERROR] get_today_birthdays: {e}")
        return []


# ========== ДЕДЛАЙНЫ ==========

def add_deadline(subject: str, title: str, deadline_date: str, comment: str, created_by: int) -> Optional[int]:
    """Добавляет новый дедлайн. Возвращает ID или None при ошибке."""
    try:
        data = {
            "subject": subject,
            "title": title,
            "deadline_date": deadline_date,
            "comment": comment,
            "created_by": created_by
        }
        response = supabase.table("deadlines").insert(data).execute()
        return response.data[0]["id"]
    except Exception as e:
        print(f"[ERROR] add_deadline: {e}")
        return None


def get_all_deadlines() -> List[Tuple]:
    try:
        response = supabase.table("deadlines").select("*").order("deadline_date").execute()
        return [(row["id"], row["subject"], row["title"], row["deadline_date"], row["comment"]) 
                for row in response.data]
    except Exception as e:
        print(f"[ERROR] get_all_deadlines: {e}")
        return []


def get_deadlines_by_subject(subject: str) -> List[Tuple]:
    try:
        response = (supabase.table("deadlines")
                    .select("*")
                    .ilike("subject", f"%{subject}%")
                    .order("deadline_date")
                    .execute())
        return [(row["id"], row["subject"], row["title"], row["deadline_date"], row["comment"]) 
                for row in response.data]
    except Exception as e:
        print(f"[ERROR] get_deadlines_by_subject: {e}")
        return []


def get_past_deadlines() -> List[Tuple]:
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        response = (supabase.table("deadlines")
                    .select("*")
                    .lt("deadline_date", today)
                    .order("deadline_date")
                    .execute())
        return [(row["id"], row["subject"], row["title"], row["deadline_date"], row["comment"]) 
                for row in response.data]
    except Exception as e:
        print(f"[ERROR] get_past_deadlines: {e}")
        return []


def delete_deadline_by_id(deadline_id: int, user_id: int) -> bool:
    """Удаляет дедлайн. Возвращает True, если удалили."""
    try:
        response = (supabase.table("deadlines")
                    .delete()
                    .eq("id", deadline_id)
                    .eq("created_by", user_id)
                    .execute())
        return len(response.data) > 0
    except Exception as e:
        print(f"[ERROR] delete_deadline_by_id: {e}")
        return False