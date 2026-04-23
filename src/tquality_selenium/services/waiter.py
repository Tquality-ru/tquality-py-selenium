"""Универсальный explicit-waiter поверх `WebDriverWait`."""
from __future__ import annotations

from typing import Any, Callable, TYPE_CHECKING

from selenium.webdriver.support.ui import WebDriverWait

if TYPE_CHECKING:
    from tquality_selenium.config import SeleniumConfig


class Waiter:
    """Обертка над `WebDriverWait` с логированием.

    Используется через контейнер: `Services.waiter().until(condition)`.
    """

    def __init__(self, config: SeleniumConfig) -> None:
        self._config = config

    @property
    def _driver(self) -> Any:
        from tquality_core import Logger  # noqa: F401 - for symmetry
        from tquality_selenium.browser import BrowserService
        from tquality_selenium.container import SeleniumServices
        return SeleniumServices.get_service(BrowserService).driver

    @property
    def _log(self) -> Any:
        from tquality_core import Logger
        from tquality_selenium.container import SeleniumServices
        return SeleniumServices.get_service(Logger)

    def until(
        self,
        condition: Callable[[Any], Any],
        message: str = "",
        timeout: float | None = None,
    ) -> Any:
        t = timeout if timeout is not None else self._config.default_timeout
        self._log.info("Waiting (%.1fs): %s", t, message)
        result = WebDriverWait(self._driver, t).until(condition, message)
        self._log.info("Wait satisfied: %s", message)
        return result
