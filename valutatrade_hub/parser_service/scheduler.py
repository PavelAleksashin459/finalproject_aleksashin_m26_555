import time

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.infra.settings import SettingsLoader
from valutatrade_hub.parser_service.updater import RatesUpdater


def run_scheduler(
    interval_seconds: int | None = None, iterations: int | None = None
) -> None:
    """Периодически обновляет курсы; по умолчанию раз в TTL кеша.

    iterations ограничивает число запусков.
    """
    interval = interval_seconds or SettingsLoader().get("rates_ttl_seconds")
    updater = RatesUpdater()
    done = 0
    while iterations is None or done < iterations:
        try:
            updater.run_update()
        except ApiRequestError as e:
            updater.logger.error("Scheduled update failed: %s", e.reason)
        done += 1
        if iterations is None or done < iterations:
            time.sleep(interval)


if __name__ == "__main__":
    try:
        run_scheduler()
    except KeyboardInterrupt:
        pass
