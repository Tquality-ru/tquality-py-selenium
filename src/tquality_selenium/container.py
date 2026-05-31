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
from selenium.webdriver.remote.webdriver import WebDriver

from tquality_core import Logger, set_logger_resolver
from tquality_core.per_test_files import (
    cwd as _per_test_cwd,
    register_per_test_rebuilder,
)

from tquality_selenium.browser import BrowserService
from tquality_selenium.config import SeleniumConfig
from tquality_selenium.screencast_provider import SeleniumScreencastProvider
from tquality_selenium.screenshot_provider import SeleniumScreenshotProvider
from tquality_selenium.services.collection_factory import CollectionFactory
from tquality_selenium.services.context_manager import ContextManager
from tquality_selenium.services.driver_waiter import DriverWaiter
from tquality_selenium.services.element_factory import ElementFactory
from tquality_selenium.services.waiter import Waiter


from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
)


def _resolve_driver_from_active() -> WebDriver:
    """Резолвит WebDriver через активный composition root.
    Fallback на `SeleniumServices` класс - даёт работать `.override()`
    в тестах без полной инициализации composition root'а."""
    active = _resolve_active() or SeleniumServices
    return active.browser().driver


def _resolve_logger_from_active() -> Logger:
    """Резолвит активный Logger - fallback на `SeleniumServices` класс."""
    active = _resolve_active() or SeleniumServices
    return active.logger()

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
            availability_check=BrowserService.is_started,
        )
    )
    screencast_provider: providers.Singleton[SeleniumScreencastProvider] = (
        providers.Singleton(
            SeleniumScreencastProvider,
            driver_resolver=_resolve_driver_from_active,
            availability_check=BrowserService.is_started,
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
        providers.ContextLocalSingleton(
            Waiter,
            config=config,
            logger_resolver=_resolve_logger_from_active,
            ignored_exceptions=(
                NoSuchElementException,
                StaleElementReferenceException,
            ),
            default_raise_cls=TimeoutException,
        )
    )
    driver_waiter: providers.ContextLocalSingleton[DriverWaiter] = (
        providers.ContextLocalSingleton(
            DriverWaiter,
            waiter=waiter,
            driver_resolver=_resolve_driver_from_active,
        )
    )
    element_factory: providers.Singleton[ElementFactory] = (
        providers.Singleton(ElementFactory)
    )
    collection_factory: providers.Singleton[CollectionFactory] = (
        providers.Singleton(CollectionFactory)
    )
    context_manager: providers.Singleton[ContextManager] = (
        providers.Singleton(ContextManager)
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
        register_per_test_rebuilder(cls._rebuild_configs_for_test)

    @classmethod
    def _rebuild_configs_for_test(cls, test_dir: Path) -> Any:
        """Перестроить `config` под директорию теста.

        `BaseConfig` уже умеет цепочку `config.json5` от CWD к корню
        workspace - chdir'ив в `test_dir`, мы получаем
        `tests/<suite>/config.json5` поверх корневого. Возвращает
        teardown-колбэк, сбрасывающий override.
        """
        with _per_test_cwd(test_dir):
            new_config = SeleniumConfig()
        cls.config.override(new_config)

        def _teardown() -> None:
            cls.config.reset_override()

        return _teardown

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
        return BrowserService.is_started()


__all__ = ["SeleniumServices"]
