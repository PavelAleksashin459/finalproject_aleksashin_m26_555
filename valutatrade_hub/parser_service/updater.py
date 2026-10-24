from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from valutatrade_hub.core.constants import RATE, SOURCE, UPDATED_AT
from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.infra.settings import PROJECT_ROOT
from valutatrade_hub.logging_config import setup_parser_logging
from valutatrade_hub.parser_service.api_clients import (
    BaseApiClient,
    CoinGeckoClient,
    ExchangeRateApiClient,
)
from valutatrade_hub.parser_service.storage import RatesStorage

SOURCES = {
    "coingecko": CoinGeckoClient,
    "exchangerate": ExchangeRateApiClient,
}


def display_path(path: Path) -> Path:
    """Путь относительно корня проекта, чтобы сообщения были короткими."""
    path = Path(path)
    return path.relative_to(PROJECT_ROOT) if path.is_relative_to(PROJECT_ROOT) else path


@dataclass
class UpdateResult:
    """Итог обновления: сколько курсов записано и какие источники упали."""

    total: int
    last_refresh: str
    errors: list[str] = field(default_factory=list)


class RatesUpdater:
    """Опрашивает источники курсов и сохраняет результат в rates.json."""

    def __init__(
        self,
        clients: dict[str, BaseApiClient] | None = None,
        storage: RatesStorage | None = None,
    ):
        self.clients = clients or {name: cls() for name, cls in SOURCES.items()}
        self.storage = storage or RatesStorage()
        self.logger = setup_parser_logging()

    def _select_clients(self, source: str | None) -> list[BaseApiClient]:
        if source is None:
            return list(self.clients.values())
        key = source.strip().lower()
        if key not in self.clients:
            raise ValueError(
                f"Неизвестный источник '{source}'. "
                f"Доступны: {', '.join(self.clients)}"
            )
        return [self.clients[key]]

    def run_update(self, source: str | None = None) -> UpdateResult:
        """Обновляет курсы из всех источников или из одного.

        Сбой отдельного источника не прерывает обновление; ApiRequestError
        бросается, только если не удалось получить ни одного курса.
        """
        clients = self._select_clients(source)
        self.logger.info("Starting rates update...")
        timestamp = datetime.now().replace(microsecond=0).isoformat()
        utc_timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        pairs, history, errors = {}, [], []
        for client in clients:
            try:
                rates = client.fetch_rates()
            except ApiRequestError as e:
                self.logger.error("Failed to fetch from %s", e.reason)
                errors.append(e.reason)
                continue
            self.logger.info(
                "Fetching from %s... OK (%d rates)", client.name, len(rates)
            )
            for pair, rate in rates.items():
                pairs[pair] = {RATE: rate, UPDATED_AT: timestamp, SOURCE: client.name}
                from_code, to_code = pair.split("_")
                history.append(
                    {
                        "id": f"{pair}_{utc_timestamp}",
                        "from_currency": from_code,
                        "to_currency": to_code,
                        RATE: rate,
                        "timestamp": utc_timestamp,
                        SOURCE: client.name,
                    }
                )

        if not pairs:
            raise ApiRequestError("не удалось получить курсы ни из одного источника")

        self.logger.info(
            "Writing %d rates to %s...", len(pairs), display_path(self.storage.path)
        )
        self.storage.save(pairs, timestamp)
        self.storage.append_history(history)
        self.logger.info(
            "Appended %d records to %s",
            len(history),
            display_path(self.storage.history_path),
        )
        return UpdateResult(len(pairs), timestamp, errors)
