"""Бизнес-операции приложения: регистрация, вход, портфель, сделки и курсы."""

import hashlib
import secrets
from datetime import datetime, timedelta

from valutatrade_hub.core.constants import (
    HASHED_PASSWORD,
    PORTFOLIOS_DATA,
    RATE,
    REGISTRATION_DATE,
    SALT,
    UPDATED_AT,
    USER_ID,
    USER_NAME,
    USERS_DATA,
)
from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.core.models import Portfolio, User
from valutatrade_hub.core.utils import (
    format_amount,
    format_cached_rate,
    format_rate,
    format_trade_rate,
    open_json,
    parse_amount,
    parse_top,
    save_json,
    validate_currency,
)
from valutatrade_hub.decorators import log_action
from valutatrade_hub.infra.settings import SettingsLoader
from valutatrade_hub.parser_service.config import ParserConfig
from valutatrade_hub.parser_service.storage import RatesStorage
from valutatrade_hub.parser_service.updater import RatesUpdater

settings = SettingsLoader()
BASE_CURRENCY = ParserConfig().BASE_CURRENCY
MIN_PASSWORD_LENGTH = 4


# --- Пользователи ---


def is_username_taken(users: list, username: str) -> bool:
    """Проверяет, есть ли пользователь с таким именем."""
    return any(user[USER_NAME] == username for user in users)


def validate_registration(users: list, username: str, password: str) -> None:
    """Бросает ValueError, если имя пустое или занято, а пароль короткий."""
    if not username.strip():
        raise ValueError("Имя пользователя не может быть пустым")
    if is_username_taken(users, username):
        raise ValueError(f"Имя пользователя '{username}' уже занято")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(
            f"Пароль должен быть не короче {MIN_PASSWORD_LENGTH} символов"
        )


def make_user_record(users: list, username: str, password: str) -> dict:
    """Собирает запись нового пользователя для users.json."""
    user_salt = secrets.token_hex(8)
    return {
        USER_ID: max((user[USER_ID] for user in users), default=0) + 1,
        USER_NAME: username,
        HASHED_PASSWORD: hashlib.sha256((password + user_salt).encode()).hexdigest(),
        SALT: user_salt,
        REGISTRATION_DATE: datetime.now().isoformat(timespec="seconds"),
    }


@log_action("REGISTER")
def register(username: str, password: str) -> str:
    """Создаёт пользователя и пустой портфель."""
    users = open_json(USERS_DATA)
    validate_registration(users, username, password)
    new_user = make_user_record(users, username, password)
    save_json(USERS_DATA, users + [new_user])
    save_portfolio(Portfolio(new_user[USER_ID]))
    return (
        f"Пользователь '{username}' зарегистрирован (id={new_user[USER_ID]}). "
        f"Войдите: login --username {username} --password ****"
    )


@log_action("LOGIN")
def login(username: str, password: str) -> User:
    """Возвращает пользователя, если пароль верный; иначе бросает ValueError."""
    row = next(
        (row for row in open_json(USERS_DATA) if row[USER_NAME] == username), None
    )
    if row is None:
        raise ValueError(f"Пользователь '{username}' не найден")
    user = User.from_dict(row)
    if not user.verify_password(password):
        raise ValueError("Неверный пароль")
    return user


# --- Портфели ---


def load_portfolio(user: User) -> Portfolio:
    """Находит портфель пользователя в portfolios.json."""
    for row in open_json(PORTFOLIOS_DATA):
        if row[USER_ID] == user.user_id:
            return Portfolio.from_dict(row, user)
    return Portfolio(user.user_id, user=user)


def save_portfolio(portfolio: Portfolio) -> None:
    """Заменяет портфель пользователя в portfolios.json."""
    rows = [
        row for row in open_json(PORTFOLIOS_DATA) if row[USER_ID] != portfolio.user_id
    ]
    rows.append(portfolio.to_dict())
    save_json(PORTFOLIOS_DATA, sorted(rows, key=lambda row: row[USER_ID]))


def show_portfolio(user: User, base: str = BASE_CURRENCY) -> str:
    """Отчёт по всем кошелькам пользователя в базовой валюте."""
    base = validate_currency(base)
    portfolio = load_portfolio(user)
    wallets = portfolio.wallets
    if not wallets:
        return f"У пользователя '{user.username}' пока нет кошельков"

    usd_rates = {
        code: rate for code, (rate, _) in get_usd_rates([*wallets, base]).items()
    }
    lines = [f"Портфель пользователя '{user.username}' (база: {base}):"]
    for code, wallet in wallets.items():
        value = wallet.balance * usd_rates[code] / usd_rates[base]
        lines.append(
            f"- {code}: {format_amount(code, wallet.balance)}  → {value:.2f} {base}"
        )
    lines.append("-" * 33)
    lines.append(f"ИТОГО: {portfolio.get_total_value(base, usd_rates):,.2f} {base}")
    return "\n".join(lines)


# --- Сделки ---


def trade_report(
    title: str, value_label: str, currency: str, amount: float, rate: float,
    start_balance: float, end_balance: float,
) -> str:
    """Текст отчёта о покупке или продаже."""
    return (
        f"{title}: {amount:.4f} {currency} "
        f"по курсу {format_trade_rate(rate)} {BASE_CURRENCY}/{currency}\n"
        "Изменения в портфеле:\n"
        f"- {currency}: было {start_balance:.4f} → стало {end_balance:.4f}\n"
        f"{value_label}: {amount * rate:,.2f} {BASE_CURRENCY}"
    )


@log_action("BUY", verbose=True)
def buy(user: User, currency: str, amount: str) -> str:
    """Покупает валюту и возвращает отчёт об изменениях."""
    currency = validate_currency(currency)
    amount = parse_amount(amount)
    rate, _ = get_rate(currency, BASE_CURRENCY)

    portfolio = load_portfolio(user)
    if currency not in portfolio.wallets:
        portfolio.add_currency(currency)
    wallet = portfolio.get_wallet(currency)

    start_balance = wallet.balance
    wallet.deposit(amount)
    save_portfolio(portfolio)
    return trade_report(
        "Покупка выполнена", "Оценочная стоимость покупки",
        currency, amount, rate, start_balance, wallet.balance,
    )


@log_action("SELL", verbose=True)
def sell(user: User, currency: str, amount: str) -> str:
    """Продаёт валюту и возвращает отчёт об изменениях."""
    currency = validate_currency(currency)
    amount = parse_amount(amount)
    rate, _ = get_rate(currency, BASE_CURRENCY)

    portfolio = load_portfolio(user)
    if currency not in portfolio.wallets:
        raise ValueError(
            f"У вас нет кошелька '{currency}'. "
            "Добавьте валюту: она создаётся автоматически при первой покупке."
        )
    wallet = portfolio.get_wallet(currency)

    start_balance = wallet.balance
    wallet.withdraw(amount)
    save_portfolio(portfolio)
    return trade_report(
        "Продажа выполнена", "Оценочная выручка",
        currency, amount, rate, start_balance, wallet.balance,
    )


# --- Курсы ---


def pair_key(code: str) -> str:
    """Ключ пары в rates.json: BTC → BTC_USD."""
    return f"{code}_{BASE_CURRENCY}"


def is_fresh(entry: dict | None, now: datetime) -> bool:
    """True, если запись кеша моложе TTL из настроек."""
    if not entry:
        return False
    ttl = timedelta(seconds=settings.get("rates_ttl_seconds"))
    return now - datetime.fromisoformat(entry[UPDATED_AT]) < ttl


def cached_usd_rate(code: str) -> float | None:
    """Курс к USD из кеша без обновления; None, если его нет."""
    if code == BASE_CURRENCY:
        return 1.0
    entry = RatesStorage().load().get(pair_key(code))
    return entry[RATE] if entry else None


def get_usd_rates(codes: list[str]) -> dict[str, tuple[float, datetime]]:
    """Курсы к USD и время их обновления.

    Берёт свежие курсы из rates.json; если хоть один устарел — обновляет кеш
    через Parser Service. Не удалось получить актуальный курс — ApiRequestError.
    """
    codes = [code for code in dict.fromkeys(codes) if code != BASE_CURRENCY]
    rates = RatesStorage().load()
    now = datetime.now()
    if not all(is_fresh(rates.get(pair_key(code)), now) for code in codes):
        try:
            RatesUpdater().run_update()
        except ApiRequestError as e:
            raise ApiRequestError(
                f"кеш курсов устарел, а обновить его не удалось ({e.reason})"
            ) from e
        rates = RatesStorage().load()
        now = datetime.now()

    result = {BASE_CURRENCY: (1.0, now.replace(microsecond=0))}
    for code in codes:
        entry = rates.get(pair_key(code))
        if not is_fresh(entry, now):
            raise ApiRequestError(
                f"нет актуального курса {code}→{BASE_CURRENCY}. "
                "Выполните 'update-rates'"
            )
        result[code] = (entry[RATE], datetime.fromisoformat(entry[UPDATED_AT]))
    return result


def get_rate(from_code: str, to_code: str) -> tuple[float, datetime]:
    """Курс from→to и время его обновления."""
    from_code = validate_currency(from_code)
    to_code = validate_currency(to_code)
    usd_rates = get_usd_rates([from_code, to_code])
    (from_usd, from_time), (to_usd, to_time) = usd_rates[from_code], usd_rates[to_code]
    return from_usd / to_usd, min(from_time, to_time)


def format_rate_report(from_code: str, to_code: str) -> str:
    """Текст для команды get-rate."""
    from_code, to_code = validate_currency(from_code), validate_currency(to_code)
    rate, updated = get_rate(from_code, to_code)
    return (
        f"Курс {from_code}→{to_code}: {format_rate(rate)} "
        f"(обновлено: {updated:%Y-%m-%d %H:%M:%S})\n"
        f"Обратный курс {to_code}→{from_code}: {format_rate(1 / rate)}"
    )


def load_cached_rates() -> tuple[dict[str, float], str]:
    """Курсы к USD из rates.json и время последнего обновления."""
    data = RatesStorage().load()
    usd_rates = {
        pair.split("_")[0]: value[RATE]
        for pair, value in data.items()
        if isinstance(value, dict)
        and RATE in value
        and pair.endswith(f"_{BASE_CURRENCY}")
    }
    if not usd_rates:
        raise ValueError(
            "Локальный кеш курсов пуст. "
            "Выполните 'update-rates', чтобы загрузить данные."
        )
    updated = data.get("last_refresh") or max(
        value[UPDATED_AT] for value in data.values() if isinstance(value, dict)
    )
    return usd_rates, updated


def show_rates(
    currency: str | None = None, top: str | None = None, base: str | None = None
) -> str:
    """Отчёт по курсам из кеша с фильтрами --currency, --top и --base."""
    usd_rates, updated = load_cached_rates()
    usd_rates[BASE_CURRENCY] = 1.0
    base = (base or BASE_CURRENCY).strip().upper()
    if base not in usd_rates:
        raise ValueError(f"Курс для '{base}' не найден в кеше.")
    rates = {
        code: rate / usd_rates[base] for code, rate in usd_rates.items() if code != base
    }

    if currency is not None:
        code = currency.strip().upper()
        if code not in rates:
            raise ValueError(f"Курс для '{code}' не найден в кеше.")
        rates = {code: rates[code]}

    if top is not None:
        crypto = ParserConfig().CRYPTO_CURRENCIES
        items = sorted(
            ((code, rate) for code, rate in rates.items() if code in crypto),
            key=lambda item: item[1],
            reverse=True,
        )[: parse_top(top)]
    else:
        items = sorted(rates.items())

    if not items:
        return "Нет курсов, подходящих под фильтр"
    lines = [f"Rates from cache (updated at {updated}):"]
    lines += [f"- {code}_{base}: {format_cached_rate(rate)}" for code, rate in items]
    return "\n".join(lines)
