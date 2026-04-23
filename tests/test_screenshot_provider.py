"""Тесты провайдера скриншотов."""
from __future__ import annotations

from typing import cast
from unittest.mock import MagicMock

from selenium.webdriver.remote.webdriver import WebDriver

from tquality_selenium import SeleniumScreenshotProvider


def test_returns_false_when_unavailable() -> None:
    driver = cast(WebDriver, MagicMock(spec=WebDriver))
    provider = SeleniumScreenshotProvider(
        driver_resolver=lambda: driver,
        availability_check=lambda: False,
    )
    assert provider.is_available() is False


def test_returns_png_bytes_when_available() -> None:
    driver = MagicMock(spec=WebDriver)
    driver.get_screenshot_as_png.return_value = b"\x89PNG\r\n\x1a\n"
    provider = SeleniumScreenshotProvider(
        driver_resolver=lambda: cast(WebDriver, driver),
        availability_check=lambda: True,
    )
    assert provider.is_available() is True
    assert provider.capture() == b"\x89PNG\r\n\x1a\n"
