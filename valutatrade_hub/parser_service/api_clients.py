from abc import ABC, abstractmethod

import requests

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service.config import ParserConfig

EXCHANGERATE_ERRORS = {
    "invalid-key": "неверный API-ключ",
    "inactive-account": "аккаунт не активирован",
    "quota-reached": "исчерпан лимит запросов",
    "unsupported-code": "неподдерживаемая базовая валюта",
    "malformed-request": "некорректный запрос",
}


class BaseApiClient(ABC):
    """Общий интерфейс клиентов: курсы в формате {"BTC_USD": 59337.21, ...}."""

    name = "API"

    def __init__(self, config: ParserConfig | None = None):
        self.config = config or ParserConfig()

    @abstractmethod
    def fetch_rates(self) -> dict[str, float]:
        """Возвращает курсы валют к базовой валюте."""

    def _get_json(self, url: str, params: dict | None = None) -> dict:
        """GET-запрос; любые сбои сети и HTTP превращаются в ApiRequestError."""
        try:
            response = requests.get(
                url, params=params, timeout=self.config.REQUEST_TIMEOUT
            )
        except requests.exceptions.Timeout:
            raise ApiRequestError(f"{self.name}: превышено время ожидания") from None
        except requests.exceptions.ConnectionError:
            raise ApiRequestError(f"{self.name}: сервис недоступен") from None
        except requests.exceptions.RequestException as e:
            raise ApiRequestError(
                f"{self.name}: ошибка запроса ({type(e).__name__})"
            ) from None

        reason = self._error_reason(response)
        if reason:
            raise ApiRequestError(f"{self.name}: {reason}")
        if response.status_code == 429:
            raise ApiRequestError(f"{self.name}: исчерпан лимит запросов")
        if response.status_code in (401, 403):
            raise ApiRequestError(f"{self.name}: доступ запрещён, проверьте API-ключ")
        if response.status_code != 200:
            raise ApiRequestError(f"{self.name}: HTTP {response.status_code}")
        try:
            return response.json()
        except ValueError:
            raise ApiRequestError(f"{self.name}: ответ не в формате JSON") from None

    def _error_reason(self, response: requests.Response) -> str | None:
        """Причина ошибки из тела ответа, если сервис её сообщает."""
        return None


class CoinGeckoClient(BaseApiClient):
    """Курсы криптовалют с CoinGecko."""

    name = "CoinGecko"

    def fetch_rates(self) -> dict[str, float]:
        base = self.config.BASE_CURRENCY
        id_map = self.config.CRYPTO_ID_MAP
        params = {
            "ids": ",".join(id_map.values()),
            "vs_currencies": base.lower(),
        }
        data = self._get_json(self.config.COINGECKO_URL, params)

        rates = {}
        for code, coin_id in id_map.items():
            price = data.get(coin_id, {}).get(base.lower())
            if price is not None:
                rates[f"{code}_{base}"] = float(price)
        if not rates:
            raise ApiRequestError(f"{self.name}: в ответе нет курсов")
        return rates


class ExchangeRateApiClient(BaseApiClient):
    """Курсы фиатных валют с ExchangeRate-API."""

    name = "ExchangeRate-API"

    def fetch_rates(self) -> dict[str, float]:
        api_key = self.config.EXCHANGERATE_API_KEY
        if not api_key:
            raise ApiRequestError(f"{self.name}: не задан EXCHANGERATE_API_KEY")
        base = self.config.BASE_CURRENCY
        url = f"{self.config.EXCHANGERATE_API_URL}/{api_key}/latest/{base}"
        data = self._get_json(url)

        # API отдаёт «1 USD = x EUR», а нужен курс EUR→USD, поэтому 1 / x
        api_rates = data.get("conversion_rates") or data.get("rates") or {}
        rates = {}
        for code in self.config.FIAT_CURRENCIES:
            value = api_rates.get(code)
            if value:
                rates[f"{code}_{base}"] = 1 / float(value)
        if not rates:
            raise ApiRequestError(f"{self.name}: в ответе нет курсов")
        return rates

    def _error_reason(self, response: requests.Response) -> str | None:
        """ExchangeRate-API сообщает ошибку полем error-type, иногда при HTTP 200."""
        try:
            data = response.json()
        except ValueError:
            return None
        if not isinstance(data, dict) or data.get("result") != "error":
            return None
        error_type = data.get("error-type", "unknown")
        return EXCHANGERATE_ERRORS.get(error_type, error_type)
