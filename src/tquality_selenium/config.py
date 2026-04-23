"""Конфигурация для Selenium-интеграции.

Расширяет `BaseConfig` из `tquality-py-core` полями, специфичными для
веб-драйверов: тип браузера, headless-режим, размер окна, таймаут загрузки
страницы.

### Совместимость с ОС

- Chrome, Firefox - кроссплатформенные.
- Edge - Windows и macOS (на Linux официально не поддерживается, хотя
  технически запускается, если Edge установлен вручную).
- Safari - только macOS.
- undetected-chrome - там, где установлен Chrome.

Проверка доступности браузера в текущей ОС выполняется при создании
`BrowserService`, а не при валидации конфига. Если браузер недоступен -
тест упадет с понятной ошибкой вместо загадочного селениумного traceback.
"""
from __future__ import annotations

import sys
from enum import Enum

from tquality_core import BaseConfig


class BrowserType(str, Enum):
    """Поддерживаемые типы браузеров."""

    CHROME = "chrome"
    FIREFOX = "firefox"
    EDGE = "edge"
    SAFARI = "safari"
    UNDETECTED_CHROME = "undetected-chrome"


def _is_macos() -> bool:
    return sys.platform == "darwin"


def _is_windows() -> bool:
    return sys.platform == "win32"


# Карта: браузер -> множество платформ, где он официально поддерживается.
# Используется BrowserService для fail-fast проверки при запуске.
_BROWSER_OS_SUPPORT: dict[BrowserType, set[str]] = {
    BrowserType.CHROME: {"linux", "darwin", "win32"},
    BrowserType.FIREFOX: {"linux", "darwin", "win32"},
    BrowserType.EDGE: {"darwin", "win32"},
    BrowserType.SAFARI: {"darwin"},
    BrowserType.UNDETECTED_CHROME: {"linux", "darwin", "win32"},
}


def is_browser_supported_on_current_os(browser: BrowserType) -> bool:
    """Проверить, поддерживается ли браузер в текущей ОС."""
    return sys.platform in _BROWSER_OS_SUPPORT[browser]


class SeleniumConfig(BaseConfig):
    """Конфигурация для Selenium-тестов.

    Порядок разрешения настроек наследуется от `BaseConfig`: аргументы
    конструктора > env vars > .env > цепочка `config.json` от cwd до корня
    workspace > значения по умолчанию.
    """

    browser: BrowserType = BrowserType.CHROME
    headless: bool = True
    page_load_timeout: float = 30.0
    window_width: int = 1920
    window_height: int = 1080
