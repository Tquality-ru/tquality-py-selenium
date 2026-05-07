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
        BrowserType.EDGE: {"linux", "darwin", "win32"},
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
    def is_browser_supported_on_current_os(
        cls, browser: BrowserType, platform: str | None = None,
    ) -> bool:
        """Проверить, поддерживается ли браузер на ОС.

        `platform` - явное значение в духе `sys.platform` (`"linux"`,
        `"darwin"`, `"win32"`). По умолчанию `sys.platform`. Параметр
        введен для тред-безопасности тестов: мутировать `sys.platform`
        через `monkeypatch.setattr` нельзя - модуль `sys` шарится между
        тредами.
        """
        target = platform if platform is not None else sys.platform
        return target in cls._BROWSER_OS_SUPPORT[browser]
