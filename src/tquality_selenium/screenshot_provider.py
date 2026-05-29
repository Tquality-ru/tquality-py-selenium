"""`SeleniumScreenshotProvider` - алиас `tquality_core.WebDriverScreenshotProvider`.

Реализация одна и та же что для appium-WebDriver, что для selenium-WebDriver -
у обоих есть `get_screenshot_as_png()`. Оставлен здесь для удобного
DI-имени и стабильного пути импорта из `tquality_selenium`.
"""
from __future__ import annotations

from tquality_core import WebDriverScreenshotProvider

SeleniumScreenshotProvider = WebDriverScreenshotProvider

__all__ = ["SeleniumScreenshotProvider"]
