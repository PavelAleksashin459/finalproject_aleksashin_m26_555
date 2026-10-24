import json
import os
import tempfile
from pathlib import Path

from valutatrade_hub.parser_service.config import ParserConfig


def read_json(path: Path, default):
    """Содержимое json-файла или default, если файла нет или он повреждён."""
    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def write_json_atomic(path: Path, data) -> None:
    """Пишет во временный файл рядом и подменяет им исходный (tmp → rename)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=2, ensure_ascii=False)
        os.replace(tmp_path, path)
    except BaseException:
        Path(tmp_path).unlink(missing_ok=True)
        raise


class RatesStorage:
    """Кеш актуальных курсов rates.json и история измерений exchange_rates.json."""

    def __init__(self, path: Path | None = None, history_path: Path | None = None):
        config = ParserConfig()
        self.path = Path(path) if path else config.RATES_FILE_PATH
        self.history_path = (
            Path(history_path) if history_path else config.HISTORY_FILE_PATH
        )

    def load(self) -> dict:
        """Текущий кеш; пустой словарь, если файла нет или он повреждён."""
        data = read_json(self.path, {})
        return data if isinstance(data, dict) else {}

    def save(self, pairs: dict[str, dict], last_refresh: str) -> None:
        """Добавляет свежие пары к кешу и подменяет файл целиком."""
        data = self.load()
        data.update(pairs)
        data["source"] = "ParserService"
        data["last_refresh"] = last_refresh
        write_json_atomic(self.path, data)

    def load_history(self) -> list[dict]:
        """Все записи истории курсов."""
        data = read_json(self.history_path, [])
        if isinstance(data, dict):
            return [data]
        return data if isinstance(data, list) else []

    def append_history(self, records: list[dict]) -> None:
        """Дописывает записи в историю, пропуская уже сохранённые id."""
        history = self.load_history()
        known_ids = {record.get("id") for record in history}
        history.extend(record for record in records if record["id"] not in known_ids)
        write_json_atomic(self.history_path, history)
