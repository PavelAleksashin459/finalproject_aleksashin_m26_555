import tomllib
from pathlib import Path
from typing import Any

PACKAGE_PARENT = Path(__file__).resolve().parent.parent.parent


def has_app_config(directory: Path) -> bool:
    """True, если в каталоге лежит pyproject.toml с разделом [tool.valutatrade]."""
    pyproject = directory / "pyproject.toml"
    if not pyproject.is_file():
        return False
    try:
        with open(pyproject, "rb") as file:
            return "valutatrade" in tomllib.load(file).get("tool", {})
    except (OSError, tomllib.TOMLDecodeError):
        return False


def find_project_root() -> Path:
    """Корень проекта: текущий каталог или его родитель с конфигом приложения.

    Если запуск идёт не из проекта (например, после uv tool install), берётся
    каталог рядом с пакетом, а если и там нет конфига — текущий каталог.
    """
    cwd = Path.cwd()
    for directory in (cwd, *cwd.parents):
        if has_app_config(directory):
            return directory
    return PACKAGE_PARENT if has_app_config(PACKAGE_PARENT) else cwd


PROJECT_ROOT = find_project_root()
PYPROJECT_PATH = PROJECT_ROOT / "pyproject.toml"

DEFAULTS: dict[str, Any] = {
    "data_dir": "data",
    "users_file": "users.json",
    "portfolios_file": "portfolios.json",
    "rates_file": "rates.json",
    "rates_ttl_seconds": 300,
    "default_base_currency": "USD",
    "log_dir": "logs",
    "log_file": "actions.log",
    "parser_log_file": "parser.log",
    "log_level": "INFO",
    "log_format": "%(levelname)s %(asctime)s %(message)s",
    "log_datefmt": "%Y-%m-%dT%H:%M:%S",
    "log_max_bytes": 1_000_000,
    "log_backup_count": 5,
}

PATH_KEYS = ("data_dir", "log_dir")


class SettingsLoader:
    """Единственный источник конфигурации приложения.

    Singleton сделан через __new__: это короче и понятнее метакласса,
    а для одного класса возможности метакласса не нужны.
    """

    _instance: "SettingsLoader | None" = None

    def __new__(cls) -> "SettingsLoader":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._config = {}
            cls._instance.reload()
        return cls._instance

    def reload(self) -> None:
        """Перечитывает [tool.valutatrade] из pyproject.toml поверх DEFAULTS."""
        config = dict(DEFAULTS)
        if PYPROJECT_PATH.exists():
            with open(PYPROJECT_PATH, "rb") as file:
                pyproject = tomllib.load(file)
            config.update(pyproject.get("tool", {}).get("valutatrade", {}))
        for key in PATH_KEYS:
            config[key] = PROJECT_ROOT / config[key]
        self._config = config

    def get(self, key: str, default: Any = None) -> Any:
        """Значение настройки или default, если ключа нет."""
        return self._config.get(key, default)
