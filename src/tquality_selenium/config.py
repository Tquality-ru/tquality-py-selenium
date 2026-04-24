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

from pydantic import Field

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

    browser: BrowserType = Field(
        default=BrowserType.CHROME,
        description=(
            "Тип запускаемого браузера. Доступность зависит от ОС: Safari - "
            "только macOS; Edge - macOS/Windows; остальные кроссплатформенны. "
            "undetected-chrome использует undetected-chromedriver."
        ),
    )
    headless: bool = Field(
        default=True,
        description=(
            "Запускать браузер в headless-режиме (без UI). Safari игнорирует "
            "флаг - не поддерживает headless."
        ),
    )
    page_load_timeout: float = Field(
        default=30.0,
        description=(
            "Таймаут ожидания полной загрузки страницы при навигации (сек). "
            "Должен быть не меньше 1 - иначе нереалистично для любой страницы."
        ),
        ge=1.0,
    )
    window_width: int = Field(
        default=1920,
        description=(
            "Ширина окна браузера в пикселях. Диапазон от минимального "
            "отображаемого размера (320) до 8K (7680)."
        ),
        ge=320,
        le=7680,
    )
    window_height: int = Field(
        default=1080,
        description=(
            "Высота окна браузера в пикселях. Диапазон от минимального "
            "отображаемого размера (240) до 8K (4320)."
        ),
        ge=240,
        le=4320,
    )
