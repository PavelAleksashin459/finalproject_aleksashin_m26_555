"""Вспомогательные функции: JSON-хранилище, разбор аргументов, форматирование."""

import json
from pathlib import Path

from valutatrade_hub.core.currencies import CryptoCurrency, get_currency
from valutatrade_hub.infra.settings import SettingsLoader
from valutatrade_hub.parser_service.storage import write_json_atomic

settings = SettingsLoader()


def data_path(file_name: str) -> Path:
    """Полный путь к файлу в каталоге данных из настроек."""
    return Path(settings.get("data_dir")) / file_name


def open_json(file_name: str, default=None):
    """Читает json из data/; если файла нет — возвращает default (по умолчанию [])."""
    path = data_path(file_name)
    if not path.exists():
        return [] if default is None else default
    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    except json.JSONDecodeError as e:
        raise ValueError(f"Файл {file_name} повреждён: {e}") from None


def save_json(file_name: str, data) -> None:
    """Атомарно сохраняет json в data/: временный файл и подмена."""
    write_json_atomic(data_path(file_name), data)


def parse_amount(raw: str) -> float:
    """Превращает строку в положительное число."""
    try:
        amount = float(raw)
    except ValueError:
        raise ValueError("'amount' должен быть положительным числом") from None
    if amount <= 0:
        raise ValueError("'amount' должен быть положительным числом")
    return amount


def parse_top(raw: str) -> int:
    """Превращает строку в положительное целое для --top."""
    try:
        top = int(raw)
    except ValueError:
        raise ValueError("'top' должен быть положительным целым числом") from None
    if top <= 0:
        raise ValueError("'top' должен быть положительным целым числом")
    return top


def validate_currency(code: str) -> str:
    """Проверяет код валюты по реестру, бросает CurrencyNotFoundError."""
    return get_currency(code).code


def is_crypto(code: str) -> bool:
    """True, если валюта из реестра — криптовалюта."""
    return isinstance(get_currency(code), CryptoCurrency)


def format_amount(code: str, amount: float) -> str:
    """Криптовалюты с 4 знаками, фиат с 2."""
    return f"{amount:.4f}" if is_crypto(code) else f"{amount:.2f}"


def format_rate(rate: float) -> str:
    """Маленькие курсы с 8 знаками, остальные с 2."""
    return f"{rate:.8f}" if rate < 1 else f"{rate:.2f}"


def format_trade_rate(rate: float) -> str:
    """Курс в отчёте о сделке: крупные с 2 знаками, мелкие с 4."""
    return f"{rate:.2f}" if rate >= 100 else f"{rate:.4f}"


def format_cached_rate(rate: float) -> str:
    """Крупные курсы с 2 знаками, мелкие без лишних нулей: 0.01016."""
    return f"{rate:.2f}" if rate >= 1 else f"{rate:.8f}".rstrip("0")
