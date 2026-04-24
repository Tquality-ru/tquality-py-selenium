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

Проверка доступности браузера в текущей ОС выполняется через `OSUtils`
при создании `BrowserService`, а не при валидации конфига. Если браузер
недоступен - тест упадет с понятной ошибкой вместо загадочного
селениумного traceback.
"""
from __future__ import annotations

from enum import Enum

from tquality_core import BaseConfig


class BrowserType(str, Enum):
    """Поддерживаемые типы браузеров."""

    CHROME = "chrome"
    FIREFOX = "firefox"
    EDGE = "edge"
    SAFARI = "safari"
    UNDETECTED_CHROME = "undetected-chrome"


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

    # Screencast (LogLevel.WITH_SCREENCAST).
    screencast_fps: int = 10
    screencast_frame_interval: float = 0.2
    screencast_max_width: int = 1280
    screencast_max_duration: float = 120.0
