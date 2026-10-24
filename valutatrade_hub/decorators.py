import inspect
import logging
from functools import wraps

from valutatrade_hub.logging_config import ACTIONS_LOGGER

logger = logging.getLogger(ACTIONS_LOGGER)


def _format_amount(amount) -> str:
    try:
        return f"{float(amount):.4f}"
    except (TypeError, ValueError):
        return repr(amount)


def _wallet_balance(user, currency: str) -> float:
    # импорт внутри функции: usecases сам импортирует этот модуль
    from valutatrade_hub.core.usecases import load_portfolio

    wallets = load_portfolio(user).wallets
    return wallets[currency].balance if currency in wallets else 0.0


def _rate_part(currency: str) -> str | None:
    from valutatrade_hub.core.usecases import BASE_CURRENCY, cached_usd_rate

    rate = cached_usd_rate(currency)
    return f"rate={rate:.2f} base='{BASE_CURRENCY}'" if rate is not None else None


def log_action(action: str, verbose: bool = False):
    """Пишет в лог операцию (BUY/SELL/REGISTER/LOGIN) и её результат.

    Исключения не глотает: фиксирует их в логе и пробрасывает дальше.
    При verbose=True добавляет баланс кошелька «было→стало».
    """

    def decorator(func):
        signature = inspect.signature(func)

        @wraps(func)
        def wrapper(*args, **kwargs):
            params = signature.bind(*args, **kwargs).arguments
            user = params.get("user")
            username = user.username if user is not None else params.get("username")
            currency = params.get("currency")
            currency = currency.strip().upper() if isinstance(currency, str) else None

            parts = [action, f"user='{username}'"]
            if currency:
                parts.append(f"currency='{currency}'")
                parts.append(f"amount={_format_amount(params.get('amount'))}")

            def write(*result_parts: str) -> None:
                rate = _rate_part(currency) if currency else None
                rate_parts = [rate] if rate else []
                logger.info(" ".join([*parts, *rate_parts, *result_parts]))

            track_wallet = verbose and user is not None and currency
            before = _wallet_balance(user, currency) if track_wallet else None
            try:
                result = func(*args, **kwargs)
            except Exception as e:
                write(
                    "result=ERROR",
                    f"error_type={type(e).__name__}",
                    f'error_message="{e}"',
                )
                raise

            result_parts = ["result=OK"]
            if track_wallet:
                after = _wallet_balance(user, currency)
                result_parts.append(f"wallet={before:.4f}→{after:.4f}")
            write(*result_parts)
            return result

        return wrapper

    return decorator
