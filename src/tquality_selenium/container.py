"""Composition root: `SeleniumServices`.

Собирает все сервисы фреймворка как DI-контейнер (dependency-injector).
Любой сервис можно заменить или добавить в подклассе - это основной способ
адаптировать фреймворк под конкретный проект.

### Получение сервиса

По типу, а не по имени провайдера - это позволяет переименовывать
провайдеры в подклассах, не ломая потребителей:

```python
from tquality_selenium import SeleniumServices, BrowserService

browser = SeleniumServices.get_service(BrowserService)
```

`get_service` всегда идет в активный composition root (последний
`setup()`), поэтому подклассы с переопределенными провайдерами
работают прозрачно.

### Расширение: новый сервис

```python
from tquality_selenium import SeleniumServices
from dependency_injector import providers

class ProjectServices(SeleniumServices):
    my_service = providers.Singleton(MyService)
```

### Замена: другая реализация

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

from typing import Any, TypeVar

from dependency_injector import containers, providers

from tquality_core import Logger, set_logger_resolver

from tquality_selenium.browser import (
    BrowserService,
    is_browser_started as _is_browser_started,
)
from tquality_selenium.config import SeleniumConfig
from tquality_selenium.screencast_provider import SeleniumScreencastProvider
from tquality_selenium.screenshot_provider import SeleniumScreenshotProvider
from tquality_selenium.services.collection_factory import CollectionFactory
from tquality_selenium.services.element_factory import ElementFactory
from tquality_selenium.services.element_waiter import ElementWaiter
from tquality_selenium.services.js_actions import JsActions
from tquality_selenium.services.waiter import Waiter


def _resolve_driver_from_active() -> Any:
    """Резолвит WebDriver через активный composition root (см. setup())."""
    if _active_services is None:
        raise RuntimeError("SeleniumServices.setup() не вызван")
    return _active_services.browser().driver

T = TypeVar("T")

# Активный composition root. Устанавливается в setup() последнего вызванного
# подкласса. Используется `get_service()` для резолва сервисов элементами/формами
# без явной инъекции.
_active_services: type[SeleniumServices] | None = None


class SeleniumServices(containers.DeclarativeContainer):
    """Composition root для Selenium-фреймворка."""

    config: providers.Singleton[SeleniumConfig] = providers.Singleton(SeleniumConfig)
    browser: providers.ContextLocalSingleton[BrowserService] = (
        providers.ContextLocalSingleton(BrowserService, config=config)
    )
    screenshot_provider: providers.Singleton[SeleniumScreenshotProvider] = (
        providers.Singleton(
            SeleniumScreenshotProvider,
            driver_resolver=_resolve_driver_from_active,
            availability_check=_is_browser_started,
        )
    )
    screencast_provider: providers.Singleton[SeleniumScreencastProvider] = (
        providers.Singleton(
            SeleniumScreencastProvider,
            driver_resolver=_resolve_driver_from_active,
            availability_check=_is_browser_started,
            config=config,
        )
    )
    logger: providers.ContextLocalSingleton[Logger] = (
        providers.ContextLocalSingleton(
            Logger,
            config=config,
            screenshot_provider=screenshot_provider,
            screencast_provider=screencast_provider,
        )
    )
    waiter: providers.ContextLocalSingleton[Waiter] = (
        providers.ContextLocalSingleton(Waiter, config=config)
    )
    element_waiter: providers.ContextLocalSingleton[ElementWaiter] = (
        providers.ContextLocalSingleton(ElementWaiter, waiter=waiter)
    )
    element_factory: providers.Singleton[ElementFactory] = (
        providers.Singleton(ElementFactory)
    )
    js_actions: providers.Singleton[JsActions] = providers.Singleton(JsActions)
    collection_factory: providers.Singleton[CollectionFactory] = (
        providers.Singleton(CollectionFactory)
    )

    @classmethod
    def setup(cls) -> None:
        """Composition root: зарегистрировать контейнер как активный.

        Использует `cls` для `set_logger_resolver`, чтобы подклассы с
        переопределенными провайдерами работали корректно.
        """
        global _active_services
        _active_services = cls
        set_logger_resolver(lambda: cls.logger())

    @classmethod
    def get_service(cls, service_type: type[T]) -> T:
        """Вернуть экземпляр сервиса по типу.

        Ищет в активном composition root (установленном через `setup()`)
        провайдер, производящий `service_type` (или его подкласс). Позволяет
        получать сервисы без привязки к имени провайдера:

        ```python
        browser = SeleniumServices.get_service(BrowserService)
        ```
        """
        active = _active_services if _active_services is not None else cls
        for provider in active.providers.values():
            produces = getattr(provider, "provides", None)
            if produces is service_type or (
                isinstance(produces, type) and issubclass(produces, service_type)
            ):
                result: Any = provider()
                return result  # type: ignore[no-any-return]
        raise LookupError(
            f"В {active.__name__} нет сервиса типа {service_type.__name__}",
        )

    @classmethod
    def is_browser_started(cls) -> bool:
        """True, если в текущем контексте запущен WebDriver.

        Проверяет contextvar, выставляемый `BrowserService` при создании
        и снимаемый при `quit()`.
        """
        return _is_browser_started()


__all__ = ["SeleniumServices"]
