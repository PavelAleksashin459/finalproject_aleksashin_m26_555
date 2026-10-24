# ValutaTrade Hub

Консольная платформа для торговли валютами. Пользователь регистрируется, ведёт
портфель фиатных и криптовалют, покупает и продаёт их по актуальным курсам.
Курсы загружает Parser Service из CoinGecko (криптовалюты) и ExchangeRate-API
(фиат) и хранит в локальном кеше.

## Структура

```
finalproject_aleksashin_m26_555/
├── data/
│   ├── users.json            # пользователи (хеш пароля с солью)
│   ├── portfolios.json       # кошельки пользователей
│   ├── rates.json            # кеш актуальных курсов
│   └── exchange_rates.json   # история всех загруженных курсов
├── valutatrade_hub/
│   ├── core/
│   │   ├── models.py         # User, Wallet, Portfolio
│   │   ├── currencies.py     # Currency, FiatCurrency, CryptoCurrency, реестр
│   │   ├── exceptions.py     # доменные исключения
│   │   ├── usecases.py       # бизнес-операции: register, buy, sell, get_rate...
│   │   ├── utils.py          # JSON-хранилище, разбор аргументов, форматирование
│   │   └── constants.py      # имена файлов и полей
│   ├── infra/
│   │   └── settings.py       # SettingsLoader (Singleton)
│   ├── parser_service/
│   │   ├── config.py         # ParserConfig: ключ, URL, валюты, таймаут, пути
│   │   ├── api_clients.py    # BaseApiClient, CoinGeckoClient, ExchangeRateApiClient
│   │   ├── updater.py        # RatesUpdater: опрос источников и запись
│   │   ├── storage.py        # атомарная запись rates.json и истории
│   │   └── scheduler.py      # периодическое обновление
│   ├── cli/
│   │   └── interface.py      # командный интерфейс
│   ├── decorators.py         # @log_action
│   └── logging_config.py     # логи с ротацией
├── Makefile
└── pyproject.toml
```

## Установка и запуск

Нужны Python 3.12+ и [uv].

```bash
make install     # uv sync
make project     # uv run project
```

Остальные цели Makefile: `make lint` (ruff), `make build`, `make publish`
(dry-run), `make package-install`.

## Команды

| Команда | Описание |
|---|---|
| `register --username <str> --password <str>` | регистрация |
| `login --username <str> --password <str>` | вход |
| `show-portfolio [--base <str>]` | портфель в базовой валюте (USD по умолчанию) |
| `buy --currency <str> --amount <float>` | покупка, кошелёк создаётся автоматически |
| `sell --currency <str> --amount <float>` | продажа |
| `get-rate --from <str> --to <str>` | курс между двумя валютами |
| `update-rates [--source coingecko\|exchangerate]` | загрузить свежие курсы |
| `show-rates [--currency <str>] [--top <int>] [--base <str>]` | курсы из кеша |
| `help`, `exit` | справка и выход |

Поддерживаемые валюты: USD, EUR, GBP, RUB, BTC, ETH, SOL.

Пример сессии:

```
>>>Введите команду: register --username alice --password 1234
Пользователь 'alice' зарегистрирован (id=1). Войдите: login --username alice --password ****
>>>Введите команду: login --username alice --password 1234
Вы вошли как 'alice'
>>>Введите команду: buy --currency BTC --amount 0.05
Покупка выполнена: 0.0500 BTC по курсу 59337.21 USD/BTC
Изменения в портфеле:
- BTC: было 0.0000 → стало 0.0500
Оценочная стоимость покупки: 2,966.86 USD
>>>Введите команду: sell --currency BTC --amount 1
Недостаточно средств: доступно 0.0500 BTC, требуется 1.0000 BTC. Проверьте баланс: show-portfolio
>>>Введите команду: get-rate --from USD --to BTC
Курс USD→BTC: 0.00001685 (обновлено: 2025-10-09 10:29:42)
Обратный курс BTC→USD: 59337.21
>>>Введите команду: show-rates --top 2
Rates from cache (updated at 2025-10-10T15:30:00):
- BTC_USD: 59337.21
- ETH_USD: 3720.00
```

## Кеш курсов и TTL

Курсы хранятся в `data/rates.json` в виде пар к USD:

```json
{
  "BTC_USD": {"rate": 59337.21, "updated_at": "2025-10-09T10:29:42", "source": "CoinGecko"},
  "source": "ParserService",
  "last_refresh": "2025-10-09T10:35:00"
}
```

Курс считается свежим `rates_ttl_seconds` секунд (по умолчанию 300). Если
`get-rate`, `buy`, `sell` или `show-portfolio` встречают устаревший курс, они
сами запускают обновление. Если обновить не удалось, команда сообщает об ошибке
и предлагает повторить позже. Любой курс между двумя валютами считается через USD.

`show-rates` показывает кеш как есть, без обновления.

## Parser Service

1. Получите бесплатный ключ на [exchangerate-api.com](https://www.exchangerate-api.com/).
   Для CoinGecko ключ не нужен.
2. Скопируйте `.env.example` в `.env` в корне проекта и впишите ключ:

   ```
   EXCHANGERATE_API_KEY=ваш_ключ
   ```

   Файл `.env` в git не попадает (он в `.gitignore`).
3. Обновите курсы командой `update-rates` или запустите периодическое
   обновление в отдельном терминале:

   ```bash
   uv run python -m valutatrade_hub.parser_service.scheduler
   ```

Каждое обновление записывает пары в `rates.json` (атомарно, через временный
файл) и дописывает записи в историю `exchange_rates.json`. Если один источник
недоступен, данные второго всё равно сохраняются.

## Настройки и логи

Настройки лежат в `pyproject.toml` в разделе `[tool.valutatrade]`: пути к
данным, TTL кеша, базовая валюта, формат и ротация логов.

- `logs/actions.log` — операции `REGISTER`, `LOGIN`, `BUY`, `SELL` с результатом;
- `logs/parser.log` — ход обновления курсов.

## Демо
(https://asciinema.org/a/FO8ViOcTWPa4D6J3)

