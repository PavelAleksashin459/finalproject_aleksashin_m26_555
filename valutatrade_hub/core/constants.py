from valutatrade_hub.infra.settings import SettingsLoader

_settings = SettingsLoader()

# Курсы: файл кеша, аргументы команд и поля записей rates.json
RATES_DATA = _settings.get("rates_file")
FROM = "from"
TO = "to"
RATE = "rate"
UPDATED_AT = "updated_at"
SOURCE = "source"
TOP = "top"

# Портфели: файл, поля portfolios.json и аргументы команд
PORTFOLIOS_DATA = _settings.get("portfolios_file")
WALLETS = "wallets"
BASE = "base"
BALANCE = "balance"
CURRENCY = "currency"
AMOUNT = "amount"

# Пользователи: файл и поля users.json
USERS_DATA = _settings.get("users_file")
USER_ID = "user_id"
USER_NAME = "username"
HASHED_PASSWORD = "hashed_password"
PASSWORD = "password"
SALT = "salt"
REGISTRATION_DATE = "registration_date"
