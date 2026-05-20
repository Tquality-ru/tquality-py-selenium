"""Утилиты ОС и проверки поддержки браузеров.

Платформенные проверки (`is_macos`, `is_windows`, `is_linux`) живут в
`tquality_core.utils.os_utils.OSUtils` - сюда переэкспортированы под
теми же именами. Карта поддержки браузеров остаётся здесь, так как
зависит от селениум-специфичного `BrowserType`.
"""
from __future__ import annotations

from tquality_core.utils.os_utils import OSUtils as _CoreOSUtils

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

    is_macos = staticmethod(_CoreOSUtils.is_macos)
    is_windows = staticmethod(_CoreOSUtils.is_windows)
    is_linux = staticmethod(_CoreOSUtils.is_linux)

    @classmethod
    def is_browser_supported_on_current_os(
        cls, browser: BrowserType, platform: str | None = None,
    ) -> bool:
        """Проверить, поддерживается ли браузер на ОС.

        `platform` - явное значение в духе `sys.platform` (`"linux"`,
        `"darwin"`, `"win32"`). По умолчанию текущая платформа. Параметр
        введен для тред-безопасности тестов: мутировать `sys.platform`
        через `monkeypatch.setattr` нельзя - модуль `sys` шарится между
        тредами.
        """
        target = platform if platform is not None else _CoreOSUtils.current_platform()
        return target in cls._BROWSER_OS_SUPPORT[browser]
