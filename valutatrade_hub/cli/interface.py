import shlex

from prettytable import PrettyTable

from valutatrade_hub.core.constants import (
    AMOUNT,
    BASE,
    CURRENCY,
    FROM,
    PASSWORD,
    SOURCE,
    TO,
    TOP,
    USER_NAME,
)
from valutatrade_hub.core.currencies import supported_codes
from valutatrade_hub.core.exceptions import (
    ApiRequestError,
    CurrencyNotFoundError,
    InsufficientFundsError,
)
from valutatrade_hub.core.usecases import (
    buy,
    format_rate_report,
    login,
    register,
    sell,
    show_portfolio,
    show_rates,
)
from valutatrade_hub.infra.settings import SettingsLoader
from valutatrade_hub.logging_config import setup_logging
from valutatrade_hub.parser_service.updater import RatesUpdater, display_path

settings = SettingsLoader()

REQUIRED_OPTIONS = {
    "register": (USER_NAME, PASSWORD),
    "login": (USER_NAME, PASSWORD),
    "buy": (CURRENCY, AMOUNT),
    "sell": (CURRENCY, AMOUNT),
    "get-rate": (FROM, TO),
}
LOGIN_REQUIRED = {"show-portfolio", "buy", "sell"}

COMMANDS_HELP = (
    ("register --username <str> --password <str>", "Регистрация"),
    ("login --username <str> --password <str>", "Вход"),
    ("show-portfolio [--base <str>]", "Портфель в базовой валюте"),
    ("buy --currency <str> --amount <float>", "Купить валюту"),
    ("sell --currency <str> --amount <float>", "Продать валюту"),
    ("get-rate --from <str> --to <str>", "Курс между двумя валютами"),
    ("update-rates [--source coingecko|exchangerate]", "Обновить курсы"),
    ("show-rates [--currency <str>] [--top <int>] [--base <str>]", "Курсы из кеша"),
    ("help", "Справка"),
    ("exit", "Выход"),
)


def help_table() -> str:
    """Таблица доступных команд."""
    table = PrettyTable(["Команда", "Описание"])
    table.align = "l"
    table.add_rows(COMMANDS_HELP)
    return table.get_string()


def parse_options(args: list) -> dict:
    """Превращает ['--username', 'alice', '--password', '1234'] в словарь."""
    options = {}
    for i in range(0, len(args), 2):
        key = args[i]
        if not key.startswith("--") or i + 1 >= len(args):
            raise ValueError(f"Некорректный аргумент: {key}")
        options[key[2:]] = args[i + 1]
    return options


def check_required(command: str, options: dict) -> None:
    """Бросает ValueError, если у команды не хватает обязательных аргументов."""
    missing = [key for key in REQUIRED_OPTIONS.get(command, ()) if key not in options]
    if missing:
        flags = ", ".join(f"--{key}" for key in missing)
        raise ValueError(f"Не указан обязательный аргумент: {flags}")


def currency_not_found_message(error: CurrencyNotFoundError) -> str:
    """Сообщение о неизвестной валюте со списком поддерживаемых."""
    return (
        f"{error}. Поддерживаемые валюты: {', '.join(supported_codes())}. "
        "Проверить курс: get-rate --from USD --to BTC"
    )


def api_error_message(error: ApiRequestError) -> str:
    """Сообщение о сбое внешнего API с советом повторить позже."""
    return f"{error}. Повторите попытку позже или проверьте подключение к сети"


def insufficient_funds_message(error: InsufficientFundsError) -> str:
    """Сообщение о нехватке средств с подсказкой проверить баланс."""
    return f"{error}. Проверьте баланс: show-portfolio"


def update_rates(source: str | None = None) -> str:
    """Запускает RatesUpdater и возвращает итоговое сообщение для пользователя."""
    log_path = display_path(settings.get("log_dir") / settings.get("parser_log_file"))
    try:
        result = RatesUpdater().run_update(source)
    except ApiRequestError as e:
        return f"Update failed: {e.reason}. Check {log_path} for details."
    if result.errors:
        return (
            f"Update completed with errors. Total rates updated: {result.total}. "
            f"Check {log_path} for details."
        )
    return (
        f"Update successful. Total rates updated: {result.total}. "
        f"Last refresh: {result.last_refresh}"
    )


def run() -> None:
    """Цикл чтения и выполнения команд."""
    setup_logging()
    print("ValutaTrade Hub. Введите 'help', чтобы увидеть список команд.")
    current_user = None
    while True:
        command_raw = input(">>>Введите команду: ").strip()
        try:
            args = shlex.split(command_raw)
            if not args:
                continue
            command, options = args[0], parse_options(args[1:])
            check_required(command, options)
            if command in LOGIN_REQUIRED and current_user is None:
                print("Сначала выполните login")
                continue

            if command == "exit":
                break
            elif command == "help":
                print(help_table())
            elif command == "register":
                print(register(options[USER_NAME], options[PASSWORD]))
            elif command == "login":
                current_user = login(options[USER_NAME], options[PASSWORD])
                print(f"Вы вошли как '{current_user.username}'")
            elif command == "show-portfolio":
                base = options.get(BASE, settings.get("default_base_currency"))
                print(show_portfolio(current_user, base))
            elif command == "buy":
                print(buy(current_user, options[CURRENCY], options[AMOUNT]))
            elif command == "sell":
                print(sell(current_user, options[CURRENCY], options[AMOUNT]))
            elif command == "get-rate":
                print(format_rate_report(options[FROM], options[TO]))
            elif command == "show-rates":
                print(
                    show_rates(
                        options.get(CURRENCY), options.get(TOP), options.get(BASE)
                    )
                )
            elif command == "update-rates":
                print(update_rates(options.get(SOURCE)))
            else:
                print(f"Неизвестная команда: {command}")
        except InsufficientFundsError as e:
            print(insufficient_funds_message(e))
        except CurrencyNotFoundError as e:
            print(currency_not_found_message(e))
        except ApiRequestError as e:
            print(api_error_message(e))
        except ValueError as e:
            print(e)


def main() -> None:
    """Точка входа в приложение."""
    run()


if __name__ == "__main__":
    main()
