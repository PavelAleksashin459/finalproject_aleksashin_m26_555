import shlex
from constants import USERS_DATA, USER_ID, PORTFOLIOS_DATA, USER_NAME, PASSWORD, WALLETS, BASE, CURRENCY, AMOUNT

from utils import register_user, open_json, save_json, login, show_portfolio, buy


def is_username_taken(users: list, username: str) -> bool:
    "Проверяет есть ли пользователь в списке"
    return any(user["username"] == username for user in users)

def validate_registration(users: list, username: str, password: str) -> str | None:
    "Ошибки при регистрации"
    if is_username_taken(users, username):
        return f"Имя пользователя '{username}' уже занято"
    if len(password) < 4:
        return "Пароль должен быть не короче 4 символов"
    if not username.strip():
        return "Имя пользователя не может быть пустым"
    return None


def parse_options(args: list) -> dict:
    """Превращает ['--username', 'alice', '--password', '1234'] в словарь."""
    options = {}
    for i in range(0, len(args), 2):
        key = args[i]
        if not key.startswith("--") or i + 1 >= len(args):
            raise ValueError(f"Некорректный аргумент: {key}")
        options[key[2:]] = args[i + 1]
    return options

def run() -> None:
    current_user = None
    while True:
        command_raw = input(">>>Введите команду: ").strip()
        try:
            args = shlex.split(command_raw)
            if not args:
                continue
            command, options = args[0], parse_options(args[1:])

            if command == "exit":
                break
            elif command == "register":
                users = open_json(USERS_DATA)
                error = validate_registration(users, options[USER_NAME], options[PASSWORD])
                if error:
                    print(error)
                    continue

                new_user = register_user(options[USER_NAME], options[PASSWORD])
                save_json(USERS_DATA, users + [new_user])
                portfolios = open_json(PORTFOLIOS_DATA)
                new_portfolio = [{USER_ID: new_user[USER_ID], WALLETS: {}}]
                save_json(PORTFOLIOS_DATA, portfolios + new_portfolio)
                print(
                    f"Пользователь '{options[USER_NAME]}' зарегистрирован (id={new_user[USER_ID]}). "
                    f"Войдите: login --username {options[USER_NAME]} --password **** "
                )
            elif command == 'login':
                user = login(options[USER_NAME], options[PASSWORD])
                if user is not None:
                    current_user = user
            elif command == 'show-portfolio':
                if current_user is None:
                    print("Сначала выполните login")
                    continue
                print(show_portfolio(current_user, options.get(BASE, "USD")))
            elif command == "buy":
                if current_user is None:
                    print("Сначала выполните login")
                    continue
                print(buy(current_user, options[CURRENCY], options[AMOUNT]))
            else:
                print(f"Неизвестная команда: {command}")
        except KeyError as e:
            print(f"Не указан обязательный аргумент --{e.args[0]}")
        except ValueError as e:
            print(e)
            

if __name__ == "__main__":
    run()