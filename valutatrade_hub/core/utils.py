import hashlib
import secrets
import json
from pathlib import Path
from datetime import datetime

from models import User
from constants import USER_ID, USER_NAME, HASHED_PASSWORD, SALT, REGISTRATION_DATE, DATA_PATH, USERS_DATA


def open_json(file_name):
    "Открывает json"
    with open(Path(DATA_PATH) / file_name, "r") as file:
            return json.load(file)

def save_json(file_name, data):
    "Сохраняет json"
    with open(Path(DATA_PATH) / file_name, "w") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)


def register_user(username: str, password: str) -> dict | None:
    "Регистрация пользователя с записью"
    users = open_json(USERS_DATA)
    user_salt = secrets.token_hex(8)
    new_user = {
        USER_ID: max((user[USER_ID] for user in users), default=0) + 1,
        USER_NAME: username,
        HASHED_PASSWORD: hashlib.sha256((password + user_salt).encode()).hexdigest(),
        SALT: user_salt,
        REGISTRATION_DATE: datetime.now().isoformat(timespec="seconds"),
    }
    return new_user

def login(username: str, password: str) -> User | None:
    """Ищет пользователя и проверяет пароль."""
    for row in open_json(USERS_DATA):
        if row[USER_NAME] == username:
            user = User.from_dict(row)
            if user.verify_password(password) == True:
                print(f"Вы вошли как '{username}'")
                return user
            print("Введен неверный пароль")
            return None
    print(f"Пользователя {username} не существует")
    return None