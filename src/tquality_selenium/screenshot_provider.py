"""Провайдер скриншотов для CRITICAL шагов в allure.

Реализует протокол `tquality_core.ScreenshotProvider`. Не создает новый
браузер, если сессии нет - `is_available()` возвращает False и шаг
пропускает скриншот.
"""
from __future__ import annotations

from typing import Callable

from selenium.webdriver.remote.webdriver import WebDriver


class SeleniumScreenshotProvider:
    """Берет драйвер через переданный callable (обычно - DI-контейнер)."""

    def __init__(
        self,
        driver_resolver: Callable[[], WebDriver],
        availability_check: Callable[[], bool],
    ) -> None:
        self._driver_resolver = driver_resolver
        self._is_available = availability_check

    def is_available(self) -> bool:
        return self._is_available()

    def capture(self) -> bytes:
        png: bytes = self._driver_resolver().get_screenshot_as_png()
        return png
