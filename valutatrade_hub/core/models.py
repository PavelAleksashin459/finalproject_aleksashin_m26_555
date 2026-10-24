import hashlib
import secrets
from datetime import datetime

from valutatrade_hub.core.constants import (
    BALANCE,
    HASHED_PASSWORD,
    REGISTRATION_DATE,
    SALT,
    USER_ID,
    USER_NAME,
    WALLETS,
)
from valutatrade_hub.core.currencies import CryptoCurrency, get_currency
from valutatrade_hub.core.exceptions import (
    CurrencyNotFoundError,
    InsufficientFundsError,
)

# Заглушка курсов к USD на случай, если кеш rates.json ещё пуст
EXCHANGE_RATES = {
    "USD": 1.0,
    "EUR": 1.0786,
    "GBP": 1.27,
    "RUB": 0.01016,
    "BTC": 59337.21,
    "ETH": 3720.00,
    "SOL": 145.12,
}


class Wallet:
    """Кошелек пользователя для одной валюты"""

    def __init__(
        self,
        currency_code: str,
        balance: float = 0.0
    ):
        self.currency_code = currency_code
        self.balance = balance

    @property
    def balance(self) -> float:
        """Текущий баланс"""
        return self._balance

    @balance.setter
    def balance(self, value: float) -> None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError("Баланс должен быть числом")
        if value < 0:
            raise ValueError("Баланс не может быть отрицательным")
        self._balance = float(value)

    @staticmethod
    def _validate_amount(amount: float) -> None:
        """Проверяет, что сумма — положительное число."""
        if isinstance(amount, bool) or not isinstance(amount, (int, float)):
            raise TypeError("Сумма должна быть числом")
        if amount <= 0:
            raise ValueError(f"{amount} должен быть положительным числом")

    def deposit(self, amount: float) -> None:
        """Пополняет баланс"""
        self._validate_amount(amount)
        self.balance = self.balance + amount

    def get_balance_info(self) -> str:
        """Баланс кошелька: криптовалюты с 4 знаками, фиат с 2."""
        try:
            crypto = isinstance(get_currency(self.currency_code), CryptoCurrency)
        except CurrencyNotFoundError:
            crypto = False
        balance = f"{self.balance:.4f}" if crypto else f"{self.balance:.2f}"
        return f"{self.currency_code}: {balance}"

    def withdraw(self, amount: float) -> None:
        """Снимает средства, если баланс позволяет."""
        self._validate_amount(amount)
        if amount > self.balance:
            raise InsufficientFundsError(self.balance, amount, self.currency_code)
        self.balance = self.balance - amount


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
        """Идентификатор пользователя."""
        return self._user_id

    @property
    def username(self) -> str:
        """Имя пользователя."""
        return self._username

    @property
    def hashed_password(self) -> str:
        """Хеш пароля с солью."""
        return self._hashed_password

    @property
    def salt(self) -> str:
        """Соль для хеширования пароля."""
        return self._salt

    @property
    def registration_date(self) -> datetime:
        """Дата регистрации."""
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
            USER_ID: self._user_id,
            USER_NAME: self._username,
            HASHED_PASSWORD: self._hashed_password,
            SALT: self._salt,
            REGISTRATION_DATE: self._registration_date.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "User":
        """Создаёт пользователя из записи users.json."""
        return cls(
            user_id=data[USER_ID],
            username=data[USER_NAME],
            hashed_password=data[HASHED_PASSWORD],
            salt=data[SALT],
            registration_date=datetime.fromisoformat(data[REGISTRATION_DATE]),
        )

    def verify_password(self, password: str) -> bool:
        """Проверяет введённый пароль на совпадение."""
        return self._hash(password, self._salt) == self._hashed_password


class Portfolio:
    """Все кошельки одного пользователя"""

    def __init__(
        self,
        user_id: int,
        wallets: dict[str, Wallet] | None = None,
        user: User | None = None
    ):
        self._user_id = user_id
        self._wallets = wallets or {}
        self._user = user

    @property
    def user_id(self) -> int:
        """Идентификатор пользователя."""
        return self._user_id

    @property
    def user(self) -> User | None:
        """Владелец портфеля (только чтение)."""
        return self._user

    @property
    def wallets(self) -> dict[str, Wallet]:
        """Копия словаря кошельков: снаружи его не изменить."""
        return self._wallets.copy()

    def add_currency(self, currency_code: str) -> Wallet:
        """Добавляет пустой кошелёк, если его ещё нет"""
        code = currency_code.upper()
        if code in self._wallets:
            raise ValueError(f"Кошелёк {code} уже существует")
        self._wallets[code] = Wallet(code)
        return self._wallets[code]

    def get_total_value(
        self, base_currency: str = "USD", rates: dict[str, float] | None = None
    ) -> float:
        """Общая стоимость всех кошельков в базовой валюте.

        rates — курсы к USD вида {"BTC": 59337.21}; по умолчанию заглушка.
        """
        rates = rates or EXCHANGE_RATES
        base = base_currency.upper()
        if base not in rates:
            raise ValueError(f"Неизвестная валюта: {base}")
        missing = [code for code in self._wallets if code not in rates]
        if missing:
            raise ValueError(f"Нет курса для: {', '.join(missing)}")
        total_usd = sum(
            wallet.balance * rates[code] for code, wallet in self._wallets.items()
        )
        return total_usd / rates[base]

    def get_wallet(self, currency_code) -> Wallet:
        """Возвращает кошелёк по коду валюты"""
        code = currency_code.upper()
        if code in self._wallets:
            return self._wallets[code]
        else:
            raise ValueError(f"Кошелька {currency_code} не существует")

    @classmethod
    def from_dict(cls, data: dict, user: User | None = None) -> "Portfolio":
        """Создаёт портфель из записи portfolios.json."""
        wallets = {
            code: Wallet(code, info[BALANCE])
            for code, info in data[WALLETS].items()
        }
        return cls(data[USER_ID], wallets, user)

    def to_dict(self) -> dict:
        """Словарь для сохранения в portfolios.json."""
        return {
            USER_ID: self._user_id,
            WALLETS: {
                code: {BALANCE: wallet.balance}
                for code, wallet in self._wallets.items()
            },
        }
