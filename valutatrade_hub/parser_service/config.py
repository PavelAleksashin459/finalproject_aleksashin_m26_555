import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

from valutatrade_hub.infra.settings import PROJECT_ROOT, SettingsLoader

load_dotenv(PROJECT_ROOT / ".env")
settings = SettingsLoader()


@dataclass(frozen=True)
class ParserConfig:
    # Ключ загружается из переменной окружения
    EXCHANGERATE_API_KEY: str | None = field(
        default_factory=lambda: os.getenv("EXCHANGERATE_API_KEY")
    )

    # Эндпоинты
    COINGECKO_URL: str = "https://api.coingecko.com/api/v3/simple/price"
    EXCHANGERATE_API_URL: str = "https://v6.exchangerate-api.com/v6"

    # Списки валют
    BASE_CURRENCY: str = "USD"
    FIAT_CURRENCIES: tuple = ("EUR", "GBP", "RUB")
    CRYPTO_CURRENCIES: tuple = ("BTC", "ETH", "SOL")
    CRYPTO_ID_MAP: dict = field(
        default_factory=lambda: {
            "BTC": "bitcoin",
            "ETH": "ethereum",
            "SOL": "solana",
        }
    )

    # Пути
    RATES_FILE_PATH: Path = field(
        default_factory=lambda: Path(settings.get("data_dir")) / "rates.json"
    )
    HISTORY_FILE_PATH: Path = field(
        default_factory=lambda: Path(settings.get("data_dir")) / "exchange_rates.json"
    )

    # Сетевые параметры
    REQUEST_TIMEOUT: int = 10
