from abc import ABC, abstractmethod

from valutatrade_hub.core.exceptions import CurrencyNotFoundError


class Currency(ABC):
    """Абстрактная валюта: общее имя, код и строка для отображения."""

    def __init__(self, name: str, code: str):
        self.name = name
        self.code = code

    @property
    def name(self) -> str:
        """Человекочитаемое имя валюты."""
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Имя валюты не может быть пустым")
        self._name = value.strip()

    @property
    def code(self) -> str:
        """ISO-код или тикер в верхнем регистре."""
        return self._code

    @code.setter
    def code(self, value: str) -> None:
        if not isinstance(value, str):
            raise ValueError("Код валюты должен быть строкой")
        code = value.strip().upper()
        if not (2 <= len(code) <= 5) or " " in code:
            raise ValueError(
                f"Код валюты '{value}' должен быть из 2–5 символов без пробелов"
            )
        self._code = code

    @abstractmethod
    def get_display_info(self) -> str:
        """Строковое представление для UI и логов."""


class FiatCurrency(Currency):
    """Фиатная валюта, выпускаемая государством или валютной зоной."""

    def __init__(self, name: str, code: str, issuing_country: str):
        super().__init__(name, code)
        if not isinstance(issuing_country, str) or not issuing_country.strip():
            raise ValueError("Страна эмиссии не может быть пустой")
        self.issuing_country = issuing_country.strip()

    def get_display_info(self) -> str:
        return f"[FIAT] {self.code} — {self.name} (Issuing: {self.issuing_country})"


class CryptoCurrency(Currency):
    """Криптовалюта с алгоритмом консенсуса и рыночной капитализацией."""

    def __init__(self, name: str, code: str, algorithm: str, market_cap: float):
        super().__init__(name, code)
        if not isinstance(algorithm, str) or not algorithm.strip():
            raise ValueError("Алгоритм не может быть пустым")
        if isinstance(market_cap, bool) or not isinstance(market_cap, (int, float)):
            raise ValueError("Капитализация должна быть числом")
        if market_cap < 0:
            raise ValueError("Капитализация не может быть отрицательной")
        self.algorithm = algorithm.strip()
        self.market_cap = float(market_cap)

    def get_display_info(self) -> str:
        mcap = f"{self.market_cap:.2e}".replace("e+", "e")
        return (
            f"[CRYPTO] {self.code} — {self.name} "
            f"(Algo: {self.algorithm}, MCAP: {mcap})"
        )


_CURRENCIES: dict[str, Currency] = {
    currency.code: currency
    for currency in (
        FiatCurrency("US Dollar", "USD", "United States"),
        FiatCurrency("Euro", "EUR", "Eurozone"),
        FiatCurrency("Russian Ruble", "RUB", "Russia"),
        FiatCurrency("British Pound", "GBP", "United Kingdom"),
        CryptoCurrency("Bitcoin", "BTC", "SHA-256", 1.12e12),
        CryptoCurrency("Ethereum", "ETH", "Ethash", 4.5e11),
        CryptoCurrency("Solana", "SOL", "Proof of History", 5.0e10),
    )
}


def supported_codes() -> list[str]:
    """Коды всех валют из реестра."""
    return sorted(_CURRENCIES)


def get_currency(code: str) -> Currency:
    """Возвращает валюту по коду или бросает CurrencyNotFoundError."""
    normalized = code.strip().upper() if isinstance(code, str) else code
    if normalized not in _CURRENCIES:
        raise CurrencyNotFoundError(normalized)
    return _CURRENCIES[normalized]
