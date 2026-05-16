"""
Модуль для работы с GitHub как с базой данных.
Хранит данные в JSON-файле в репозитории.
"""

import json
import os
import base64
from datetime import datetime
from github import Github, GithubException
from dotenv import load_dotenv

# ========== ЗАГРУЗКА ПЕРЕМЕННЫХ ==========
load_dotenv()

# ========== НАСТРОЙКИ ==========
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
REPO_NAME = os.environ.get("REPO_NAME", "Saigafarova/Bottest")
DATA_FILE = "bot_data.json"


# ========== ДАЛЬШЕ ВЕСЬ ОСТАЛЬНОЙ КОД ==========
# (функции get_repo, load_data, save_data и т.д.)

# Структура данных по умолчанию
DEFAULT_DATA = {
    "birthdays": {},      # user_id: {"username": "...", "birthday": "dd-mm"}
    "deadlines": []       # список дедлайнов
}

def get_repo():
    """Подключается к GitHub и возвращает репозиторий"""
    if not GITHUB_TOKEN:
        raise ValueError("Переменная GITHUB_TOKEN не установлена!")
    g = Github(GITHUB_TOKEN)
    return g.get_repo(REPO_NAME)

def load_data():
    """Загружает данные из JSON-файла в репозитории"""
    try:
        repo = get_repo()
        contents = repo.get_contents(DATA_FILE)
        data = json.loads(base64.b64decode(contents.content).decode())
        return data
    except GithubException as e:
        if e.status == 404:
            # Файл не найден — создаём новый
            save_data(DEFAULT_DATA)
            return DEFAULT_DATA.copy()
        else:
            raise e
    except Exception as e:
        print(f"Ошибка загрузки данных: {e}")
        return DEFAULT_DATA.copy()

def save_data(data):
    """Сохраняет данные в JSON-файл в репозитории"""
    try:
        repo = get_repo()
        content = json.dumps(data, indent=2, ensure_ascii=False)
        try:
            # Пробуем обновить существующий файл
            contents = repo.get_contents(DATA_FILE)
            repo.update_file(contents.path, "Update data", content, contents.sha)
        except GithubException as e:
            if e.status == 404:
                # Файла нет — создаём
                repo.create_file(DATA_FILE, "Create data file", content)
            else:
                raise e
        print("Данные сохранены на GitHub")
    except Exception as e:
        print(f"Ошибка сохранения данных: {e}")

# ========== ФУНКЦИИ ДЛЯ ДНЕЙ РОЖДЕНИЯ ==========
def add_birthday_to_github(user_id: int, username: str, birthday: str):
    data = load_data()
    data["birthdays"][str(user_id)] = {"username": username, "birthday": birthday}
    save_data(data)

def get_all_birthdays_from_github():
    data = load_data()
    result = []
    for user_id, info in data["birthdays"].items():
        result.append((int(user_id), info["username"], info["birthday"]))
    return result

def get_today_birthdays_from_github():
    today = datetime.now().strftime("%d-%m")
    data = load_data()
    result = []
    for user_id, info in data["birthdays"].items():
        if info["birthday"] == today:
            result.append((int(user_id), info["username"]))
    return result

# ========== ФУНКЦИИ ДЛЯ ДЕДЛАЙНОВ ==========
def add_deadline_to_github(subject: str, title: str, deadline_date: str, comment: str, created_by: int):
    data = load_data()
    new_id = 1
    if data["deadlines"]:
        new_id = max(d["id"] for d in data["deadlines"]) + 1
    data["deadlines"].append({
        "id": new_id,
        "subject": subject,
        "title": title,
        "deadline_date": deadline_date,
        "comment": comment,
        "created_by": created_by
    })
    save_data(data)
    return new_id

def get_all_deadlines_from_github():
    data = load_data()
    result = []
    for d in data["deadlines"]:
        result.append((d["id"], d["subject"], d["title"], d["deadline_date"], d["comment"]))
    return sorted(result, key=lambda x: x[3])  # сортировка по дате

def get_deadlines_by_subject_from_github(subject: str):
    all_deadlines = get_all_deadlines_from_github()
    return [d for d in all_deadlines if d[1].lower() == subject.lower()]

def get_past_deadlines_from_github():
    today = datetime.now().strftime("%Y-%m-%d")
    all_deadlines = get_all_deadlines_from_github()
    return [d for d in all_deadlines if d[3] < today]

def delete_deadline_from_github(deadline_id: int, user_id: int):
    data = load_data()
    for i, d in enumerate(data["deadlines"]):
        if d["id"] == deadline_id and d["created_by"] == user_id:
            del data["deadlines"][i]
            save_data(data)
            return True
    return False