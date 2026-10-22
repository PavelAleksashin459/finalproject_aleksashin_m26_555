import hashlib
import secrets
import json
from pathlib import Path
from datetime import datetime

from constants import PORTFOLIOS_DATA
from models import EXCHANGE_RATES, Portfolio, User
from constants import USER_ID, USER_NAME, HASHED_PASSWORD, SALT, REGISTRATION_DATE, DATA_PATH, USERS_DATA, CRYPTO


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

def load_portfolio(user: User) -> Portfolio:
    """Находит портфель пользователя в portfolios.json."""
    for row in open_json(PORTFOLIOS_DATA):
        if row[USER_ID] == user.user_id:
            return Portfolio.from_dict(row, user)
    return Portfolio(user.user_id, user=user)

def show_portfolio(user: User, base: str = "USD") -> str:
    """Отчёт по всем кошелькам пользователя в базовой валюте."""
    base = base.upper()
    if base not in EXCHANGE_RATES:
        raise ValueError(f"Неизвестная базовая валюта '{base}'")
    portfolio = load_portfolio(user)
    wallets = portfolio.wallets
    if not wallets:
        return f"У пользователя '{user.username}' пока нет кошельков"
    lines = [f"Портфель пользователя '{user.username}' (база: {base}):"]
    for code, wallet in wallets.items():
        value = wallet.balance * EXCHANGE_RATES[code] / EXCHANGE_RATES[base]
        amount = (
            f"{wallet.balance:.4f}" if code in CRYPTO else f"{wallet.balance:.2f}"
        )
        lines.append(f"- {code}: {amount}  → {value:.2f} {base}")
    lines.append("-" * 33)
    lines.append(f"ИТОГО: {portfolio.get_total_value(base):,.2f} {base}")
    return "\n".join(lines)


def parse_amount(raw: str) -> float:
    """Превращает строку в положительное число."""
    try:
        amount = float(raw)
    except ValueError:
        raise ValueError("'amount' должен быть положительным числом") from None
    if amount <= 0:
        raise ValueError("'amount' должен быть положительным числом")
    return amount

def validate_currency(code: str) -> str:
    """Проверяет формат кода валюты и наличие курса."""
    code = code.strip().upper()
    if not (code.isalpha() and 2 <= len(code) <= 5):
        raise ValueError(f"Некорректный код валюты: '{code}'")
    if code not in EXCHANGE_RATES:
        raise ValueError(f"Не удалось получить курс для {code}")
    return code

def save_portfolio(portfolio: Portfolio) -> None:
    """Заменяет портфель пользователя в portfolios.json"""
    rows = [
        row for row in open_json(PORTFOLIOS_DATA)
        if row[USER_ID] != portfolio.user_id
    ]
    rows.append(portfolio.to_dict())
    save_json(PORTFOLIOS_DATA, sorted(rows, key=lambda row: row[USER_ID]))

def buy(user: User, currency:str, amount:str) -> str:
    """Покупает валюту и возвращает отчёт об изменениях"""
    currency = validate_currency(currency)
    amount = parse_amount(amount)

    portfolio = load_portfolio(user)
    if currency not in portfolio.wallets:
        portfolio.add_currency(currency)
    wallet = portfolio.get_wallet(currency)

    start_balance = wallet.balance
    wallet.deposit(amount)
    save_portfolio(portfolio)

    rate = EXCHANGE_RATES[currency]
    rate_text = f"{rate:.2f}" if rate >= 100 else f"{rate:.4f}"
    text = (
        f"Покупка выполнена: {amount:.4f} {currency} "
        f"по курсу {rate_text} USD/{currency}\n"
        "Изменения в портфеле:\n"
        f"- {currency}: было {start_balance:.4f} → стало {wallet.balance:.4f}\n"
        f"Оценочная стоимость покупки: {amount * rate:,.2f} USD"
    )
    return text

