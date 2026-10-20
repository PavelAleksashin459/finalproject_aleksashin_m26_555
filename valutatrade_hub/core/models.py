import secrets
import hashlib
from datetime import datetime



class Wallet:
    def __init__(self):
        pass

    def deposit(amount: float):
        pass

    def get_balance_info():
        pass

    def withdraw(amount: float):
        pass

class User:
    """Пользователь системы."""

    def __init__(
        self,
        user_id: int,
        username: str,
        hashed_password: str,
        salt: str,
        registration_date: datetime,
    ):
        self._user_id = user_id
        self.username = username
        self._hashed_password = hashed_password
        self._salt = salt
        self._registration_date = registration_date

    @staticmethod
    def _hash(password: str, salt: str) -> str:
        """Односторонний псевдо-хеш пароля с солью."""
        return hashlib.sha256((password + salt).encode()).hexdigest()

    @property
    def user_id(self) -> int:
        return self._user_id
    @property
    def username(self) -> str:
        return self._username
    @property
    def hashed_password(self) -> str:
        return self._hashed_password
    @property
    def salt(self) -> str:
        return self._salt
    @property
    def registration_date(self) -> datetime:
        return self._registration_date

    @username.setter
    def username(self, value: str) -> None:
        if not value or not value.strip():
            raise ValueError("Имя не может быть пустым")
        self._username = value

    def get_user_info(self) -> str:
        """Возвращает информацию о пользователе без пароля."""
        return (
            f"ID: {self._user_id}, имя: {self._username}, "
            f"дата регистрации: {self._registration_date.isoformat()}"
        )

    def change_password(self, new_password: str) -> None:
        """Меняет пароль: генерирует новую соль и хеширует пароль."""
        if len(new_password) < 4:
            raise ValueError("Пароль должен быть не короче 4 символов")
        self._salt = secrets.token_hex(8)
        self._hashed_password = self._hash(new_password, self._salt)
    
    def to_dict(self) -> dict:
        """Словарь для сохранения в users.json."""
        return {
            "user_id": self._user_id,
            "username": self._username,
            "hashed_password": self._hashed_password,
            "salt": self._salt,
            "registration_date": self._registration_date.isoformat(),
        }
    @classmethod
    def from_dict(cls, data: dict) -> "User":
        """Создаёт пользователя из записи users.json."""
        return cls(
            user_id=data["user_id"],
            username=data["username"],
            hashed_password=data["hashed_password"],
            salt=data["salt"],
            registration_date=datetime.fromisoformat(data["registration_date"]),
        )

    def verify_password(self, password: str) -> bool:
        """Проверяет введённый пароль на совпадение."""
        return self._hash(password, self._salt) == self._hashed_password

class Portfolio:
    def __init__(self):
        pass

    def add_currency(currency_code: str):
        pass 

    def get_total_value(base_currency='USD'):
        pass

    def get_wallet(currency_code):
        pass

