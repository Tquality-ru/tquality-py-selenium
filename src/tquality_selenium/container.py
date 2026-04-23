"""Composition root: `SeleniumServices`.

Класс собирает все сервисы фреймворка как DI-контейнер (dependency-injector).
Чтобы расширить или заменить любой сервис - наследуйтесь и переопределите
нужный провайдер. Метод `setup()` связывает резолверы ядра с этим контейнером
и должен вызываться один раз на старте тестовой сессии (обычно в conftest.py).

### Пример: добавить свой сервис

```python
from tquality_selenium import SeleniumServices
from dependency_injector import providers

from my_project.element_factory import ElementFactory

class ProjectServices(SeleniumServices):
    element_factory = providers.Singleton(ElementFactory)
```

### Пример: заменить BrowserService

```python
class ProjectServices(SeleniumServices):
    browser = providers.ContextLocalSingleton(
        MyBrowserService, config=SeleniumServices.config,
    )
```

### Composition root в conftest.py

```python
from my_project.services import ProjectServices

ProjectServices.setup()


@pytest.fixture(autouse=True)
def browser():
    ProjectServices.browser()
    yield
    ProjectServices.browser().quit()
    ProjectServices.browser.reset()
    ProjectServices.logger.reset()
```
"""
from __future__ import annotations

from dependency_injector import containers, providers

from tquality_core import (
    Logger,
    set_logger_resolver,
    set_screenshot_provider,
)

from tquality_selenium.browser import BrowserService, is_browser_started
from tquality_selenium.config import SeleniumConfig
from tquality_selenium.screenshot_provider import SeleniumScreenshotProvider


class SeleniumServices(containers.DeclarativeContainer):
    """Composition root для Selenium-фреймворка.

    Наследуйте, чтобы добавить или заменить сервисы. Вызывайте
    `setup()` один раз в conftest.py.
    """

    config: providers.Singleton[SeleniumConfig] = providers.Singleton(SeleniumConfig)
    logger: providers.ContextLocalSingleton[Logger] = (
        providers.ContextLocalSingleton(Logger, config=config)
    )
    browser: providers.ContextLocalSingleton[BrowserService] = (
        providers.ContextLocalSingleton(BrowserService, config=config)
    )

    @classmethod
    def setup(cls) -> None:
        """Связать резолверы ядра с этим классом сервисов.

        Использует `cls.logger` и `cls.browser`, чтобы подклассы с
        переопределенными провайдерами работали корректно.
        """
        set_logger_resolver(lambda: cls.logger())
        set_screenshot_provider(
            SeleniumScreenshotProvider(
                driver_resolver=lambda: cls.browser().driver,
                availability_check=is_browser_started,
            )
        )


__all__ = ["SeleniumServices"]
