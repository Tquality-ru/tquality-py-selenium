"""Утилиты для работы с ОС и проверки поддержки браузеров.

`OSUtils` объединяет проверки текущей платформы и карту поддержки
браузеров разными ОС. Используется `BrowserService` для fail-fast
проверки при запуске.
"""
from __future__ import annotations

import sys

from tquality_selenium.config import BrowserType


class OSUtils:
    """Утилиты определения ОС и проверки поддержки браузеров."""

    # Карта: браузер -> множество платформ, где он официально поддерживается.
    _BROWSER_OS_SUPPORT: dict[BrowserType, set[str]] = {
        BrowserType.CHROME: {"linux", "darwin", "win32"},
        BrowserType.FIREFOX: {"linux", "darwin", "win32"},
        BrowserType.EDGE: {"darwin", "win32"},
        BrowserType.SAFARI: {"darwin"},
        BrowserType.UNDETECTED_CHROME: {"linux", "darwin", "win32"},
    }

    @staticmethod
    def is_macos() -> bool:
        return sys.platform == "darwin"

    @staticmethod
    def is_windows() -> bool:
        return sys.platform == "win32"

    @staticmethod
    def is_linux() -> bool:
        return sys.platform == "linux"

    @classmethod
    def is_browser_supported_on_current_os(cls, browser: BrowserType) -> bool:
        """Проверить, поддерживается ли браузер в текущей ОС."""
        return sys.platform in cls._BROWSER_OS_SUPPORT[browser]
