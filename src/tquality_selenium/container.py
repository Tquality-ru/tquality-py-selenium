"""DI-контейнер Selenium-интеграции.

Регистрирует SeleniumConfig, Logger (из ядра), BrowserService. Функция
`wire_core_integrations()` связывает ядро с этим контейнером: после ее
вызова `step()` из ядра использует Logger из контейнера, а CRITICAL шаги
делают скриншоты через активный WebDriver.
"""
from __future__ import annotations

from dependency_injector import containers, providers
from selenium.webdriver.remote.webdriver import WebDriver

from tquality_core import (
    Logger,
    set_logger_resolver,
    set_screenshot_provider,
)

from tquality_selenium.browser import BrowserService, is_browser_started
from tquality_selenium.config import SeleniumConfig
from tquality_selenium.screenshot_provider import SeleniumScreenshotProvider


class Container(containers.DeclarativeContainer):
    """Базовый контейнер. Наследуйте для добавления своих сервисов."""

    config: providers.Singleton[SeleniumConfig] = providers.Singleton(SeleniumConfig)
    logger: providers.ContextLocalSingleton[Logger] = (
        providers.ContextLocalSingleton(Logger, config=config)
    )
    browser: providers.ContextLocalSingleton[BrowserService] = (
        providers.ContextLocalSingleton(BrowserService, config=config)
    )


def wire_core_integrations(container: type[Container] = Container) -> None:
    """Связать сервисы контейнера с резолверами ядра.

    Вызывайте один раз при старте тестовой сессии (в conftest.py)
    как composition root. Проект, который наследует `Container`, должен
    передать свой подкласс, иначе резолверы ядра будут указывать на
    пустые провайдеры базового контейнера.

    ```python
    # conftest.py
    from framework import Container
    from tquality_selenium import wire_core_integrations

    wire_core_integrations(Container)
    ```
    """
    set_logger_resolver(lambda: container.logger())
    set_screenshot_provider(
        SeleniumScreenshotProvider(
            driver_resolver=lambda: container.browser().driver,
            availability_check=is_browser_started,
        )
    )
