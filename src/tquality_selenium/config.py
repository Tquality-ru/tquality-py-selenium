"""Конфигурация для Selenium-интеграции.

Расширяет `BaseConfig` из `tquality-py-core` блоками, сгруппированными
по смыслу:

- `browser` - выбор активного браузера (один из enum `BrowserType`).
- `chrome`, `firefox`, `edge`, `safari`, `undetected_chrome` - per-browser
  настройки. Все живут одновременно, поэтому можно подготовить валидный
  конфиг для каждого браузера и переключаться одной строкой `browser: ...`.
- `screencast` - параметры webm-записи для шагов уровня WITH_SCREENCAST.

Активный блок достается через `config.active_browser` -
`BrowserService` читает оттуда headless/размер окна/таймаут навигации.

### Совместимость браузера и ОС

- Chrome, Firefox, undetected-chrome - кроссплатформенные.
- Edge - Windows и macOS.
- Safari - только macOS (headless не поддерживается, флаг игнорируется).
"""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from tquality_core import BaseConfig


class Capabilities(BaseModel):
    """W3C-capabilities для Remote-сессии. Известные поля задокументированы;
    произвольные ключи разрешены через `extra="allow"` - сохраняются в дампе
    и применяются как `set_capability(key, value)` без потерь.
    """

    model_config = ConfigDict(extra="allow")

    platformName: str | None = Field(
        default=None,
        description=(
            "Целевая ОС: `mac` / `linux` / `windows` / `android` / `ios`. "
            "Selenium Grid использует её для роутинга в node с подходящим "
            "stereotype. None - оставить на усмотрение Grid."
        ),
    )
    browserVersion: str | None = Field(
        default=None,
        description=(
            "Версия или CfT-канал: `149.0.7827.54` / `stable` / `beta` / "
            "`dev`. Канальные значения заставляют Selenium Manager на Node "
            "скачать соответствующую копию браузера. None - системная версия."
        ),
    )


class BrowserType(str, Enum):
    """Поддерживаемые типы браузеров."""

    CHROME = "chrome"
    FIREFOX = "firefox"
    EDGE = "edge"
    SAFARI = "safari"
    UNDETECTED_CHROME = "undetected-chrome"


class BrowserConfig(BaseModel):
    """Настройки одной браузерной реализации.

    Одна и та же структура для всех браузеров; Safari игнорирует
    `headless` (в нем этот режим не поддерживается).
    """

    headless: bool = True
    window_width: int = Field(default=1920, ge=320, le=7680)
    window_height: int = Field(default=1080, ge=240, le=4320)
    page_load_timeout: float = Field(default=30.0, ge=1.0)


class ScreencastConfig(BaseModel):
    """Параметры видеозаписи шагов уровня WITH_SCREENCAST."""

    fps: int = Field(default=10, ge=1, le=60)
    frame_interval: float = Field(default=0.2, ge=0.05, le=2.0)
    max_width: int = Field(default=1280, ge=320, le=3840)
    max_duration: float = Field(default=120.0, ge=1.0, le=600.0)


class SeleniumConfig(BaseConfig):
    """Конфигурация для Selenium-тестов.

    Структурирована по логическим блокам: per-browser и feature-specific.
    Это даёт возможность заранее описать все браузеры в одном конфиге
    и переключаться между ними только через поле `browser`, без
    переписывания остальной секции.
    """

    browser: BrowserType = Field(
        default=BrowserType.CHROME,
        description=(
            "Тип запускаемого браузера. Доступность зависит от ОС: Safari - "
            "только macOS; Edge - macOS/Windows; остальные кроссплатформенны. "
            "undetected-chrome использует undetected-chromedriver."
        ),
    )

    chrome: BrowserConfig = Field(default_factory=BrowserConfig)
    firefox: BrowserConfig = Field(default_factory=BrowserConfig)
    edge: BrowserConfig = Field(default_factory=BrowserConfig)
    safari: BrowserConfig = Field(default_factory=BrowserConfig)
    undetected_chrome: BrowserConfig = Field(default_factory=BrowserConfig)

    screencast: ScreencastConfig = Field(default_factory=ScreencastConfig)

    attach_page_source_on_failure: bool = Field(
        default=True,
        description=(
            "Прикреплять текущий driver.page_source к allure-отчёту "
            "при падении теста (HTML-вложение). Включено по умолчанию: "
            "diff между ожидаемым и фактическим DOM почти всегда нужен "
            "для расследования. Если сессия мертва, прикрепляется "
            "диагностический комментарий вместо HTML."
        ),
    )

    bidi: bool = Field(
        default=True,
        description=(
            "Запрашивать у драйвера WebSocket-URL и поднимать BiDi-сессию. "
            "Спектр возможностей: https://www.selenium.dev/documentation/webdriver/bidi/. "
            "Отключите только если браузер или окружение не поддерживают "
            "BiDi (например, Safari <18.4 / macOS <15.4 - там сессия не "
            "поднимется при запросе webSocketUrl)."
        ),
    )

    remote_url: str | None = Field(
        default=None,
        description=(
            "URL Selenium Grid Hub для запуска браузера через Remote "
            "WebDriver (например, http://hub.example:4444). Если None - "
            "запускается локальный браузер. Тип браузера и headless-флаг "
            "берутся из соответствующих секций конфига."
        ),
    )

    capabilities: Capabilities = Field(
        default_factory=Capabilities,
        description=(
            "W3C-capabilities для Remote-сессии. Известные поля - в "
            "`Capabilities`; произвольные ключи разрешены и проходят как "
            "есть. Применяются через `options.set_capability(...)` перед "
            "`webdriver.Remote(...)`. При локальном запуске игнорируются."
        ),
    )

    @property
    def active_browser(self) -> BrowserConfig:
        """Конфиг того браузера, что выбран в `self.browser`."""
        attr = self.browser.value.replace("-", "_")
        result: BrowserConfig = getattr(self, attr)
        return result
