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

import contextvars
import inspect
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, TypeVar

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
from tquality_selenium.services.js_actions import JsActions
from tquality_selenium.services.waiter import Waiter


def _resolve_driver_from_active() -> Any:
    """Резолвит WebDriver через активный composition root (см. setup())."""
    active = _resolve_active()
    if active is None:
        raise RuntimeError("SeleniumServices.setup() не вызван")
    return active.browser().driver

T = TypeVar("T")

# Активный composition root - двухуровневая модель:
# 1) `_default_services` - process-wide default, ставится `setup()`. Виден из
#    любого треда; нужен для текущего паттерна "один setup() в conftest.py".
# 2) `_active_services_ctx` - context-local override, ставится
#    `override_active(...)`. Изолирован per-context (тред/asyncio task), не
#    мешает другим контекстам. ContextVar-ы НЕ наследуются дочерними тредами
#    автоматически: для проброса используйте `contextvars.copy_context()`.
_default_services: type[SeleniumServices] | None = None
_active_services_ctx: contextvars.ContextVar[type[SeleniumServices] | None] = (
    contextvars.ContextVar("_active_services_ctx", default=None)
)


def _resolve_active() -> type[SeleniumServices] | None:
    """ContextVar override → process-wide default → None."""
    return _active_services_ctx.get() or _default_services


@contextmanager
def _cwd(path: Path) -> Iterator[None]:
    """Временно перейти в `path`; по выходу из контекста - обратно."""
    previous = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


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
    element_factory: providers.Singleton[ElementFactory] = (
        providers.Singleton(ElementFactory)
    )
    js_actions: providers.Singleton[JsActions] = providers.Singleton(JsActions)
    collection_factory: providers.Singleton[CollectionFactory] = (
        providers.Singleton(CollectionFactory)
    )

    @classmethod
    def setup(cls, config_dir: Path | str | None = None) -> None:
        """Composition root: зарегистрировать контейнер как активный.

        ``config_dir`` - стартовая директория поиска ``config.json5``.
        Если не задана, берется директория вызывающего файла (обычно
        `conftest.py` проекта). Это устраняет зависимость от CWD pytest:
        тест можно запускать из корня репо, а конфиги проекта окажутся
        подхвачены правильно.

        Использует `cls.logger` / `cls.browser`, чтобы подклассы с
        переопределенными провайдерами работали корректно.
        """
        if config_dir is None:
            caller_file = inspect.stack()[1].filename
            config_dir = Path(caller_file).resolve().parent
        else:
            config_dir = Path(config_dir).resolve()

        # Кешируем singleton с правильно разрешенным config.json.
        # pydantic-settings ходит от os.getcwd(), поэтому временно
        # подменяем его - именно для момента первой инициализации.
        with _cwd(config_dir):
            cls.config()

        global _default_services
        _default_services = cls
        set_logger_resolver(lambda: cls.logger())

    @classmethod
    @contextmanager
    def override_active(cls) -> Iterator[None]:
        """Временно сделать `cls` активным контейнером в текущем контексте.

        Изолировано per-context (тред/asyncio task) через ContextVar - не
        мешает default'у, выставленному `setup()`, и не виден другим
        контекстам. Дочерние треды НЕ наследуют override автоматически:
        пробрасывайте через `contextvars.copy_context().run(...)`.

        ```python
        with ProjectServices.override_active():
            run_scenario()  # `get_service` идет в ProjectServices
        # снаружи - снова default из setup()
        ```
        """
        token = _active_services_ctx.set(cls)
        try:
            yield
        finally:
            _active_services_ctx.reset(token)

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
        active = _resolve_active() or cls
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
