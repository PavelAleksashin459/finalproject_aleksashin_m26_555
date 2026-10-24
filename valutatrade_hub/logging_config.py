import logging
import sys
from logging.handlers import RotatingFileHandler

from valutatrade_hub.infra.settings import SettingsLoader

ACTIONS_LOGGER = "valutatrade.actions"
PARSER_LOGGER = "valutatrade.parser"


def _file_handler(file_name: str) -> RotatingFileHandler:
    """Файловый обработчик в log_dir с ротацией и форматом из настроек."""
    settings = SettingsLoader()
    log_dir = settings.get("log_dir")
    log_dir.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        log_dir / file_name,
        maxBytes=settings.get("log_max_bytes"),
        backupCount=settings.get("log_backup_count"),
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter(settings.get("log_format"), settings.get("log_datefmt"))
    )
    return handler


def setup_logging(level: str | None = None) -> logging.Logger:
    """Настраивает логгер операций: строковый формат, ротация по размеру.

    Уровень берётся из настроек (INFO), для отладки можно передать "DEBUG".
    """
    settings = SettingsLoader()
    logger = logging.getLogger(ACTIONS_LOGGER)
    logger.setLevel(level or settings.get("log_level"))
    if logger.handlers:
        return logger
    logger.addHandler(_file_handler(settings.get("log_file")))
    logger.propagate = False
    return logger


def setup_parser_logging(level: str | None = None) -> logging.Logger:
    """Логгер парсера: подробности в parser.log, краткий ход работы в консоль."""
    settings = SettingsLoader()
    logger = logging.getLogger(PARSER_LOGGER)
    logger.setLevel(level or settings.get("log_level"))
    if logger.handlers:
        return logger
    logger.addHandler(_file_handler(settings.get("parser_log_file")))
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logger.addHandler(console)
    logger.propagate = False
    return logger
