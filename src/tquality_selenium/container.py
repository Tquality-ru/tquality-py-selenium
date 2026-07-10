"""Composition root: `SeleniumServices`.

Собирает все сервисы фреймворка как статический DI-контейнер
(`static_dependency_injector`, поверх ядрового `CoreServicesABC`). Любой сервис
можно заменить или добавить в подклассе - это основной способ адаптировать
фреймворк под конкретный проект.

### Получение сервиса

По типу, а не по имени провайдера - это позволяет переименовывать провайдеры
в подклассах, не ломая потребителей:

```python
from tquality_selenium import SeleniumServices, BrowserService

browser = SeleniumServices.get_service(BrowserService)
```

`get_service` резолвит из того контейнера, на котором вызван. Подкласс с
переопределёнными провайдерами (`@copy`) резолвит СВОИ переопределения через
наследование - отдельного реестра «активного» контейнера не требуется.

### Расширение / замена

```python
from tquality_selenium import SeleniumServices
from static_dependency_injector.containers import copy
from static_dependency_injector.static_providers import Singleton, TestContextSingleton

@copy(SeleniumServices)
class ProjectServices(SeleniumServices):
    my_service: MyService = Singleton(MyService)                       # новый
    browser: BrowserService = TestContextSingleton(MyBrowserService, config=SeleniumServices.provider.config)  # замена
```

`@copy` перевязывает унаследованные зависимости на переопределённые слоты
(напр. `driver`/`logger`/`waiter` начинают смотреть на новый `browser`/`config`),
поэтому `ProjectServices` самосогласован: `ProjectServices.get_service(...)` и
`ProjectServices.<провайдер>` резолвят именно проектные реализации.

### Composition root в conftest.py

`config.json5` рядом с тестом подхватывается автоматически (per-test плагин
ядра смещает поиск конфигов на директорию теста) - отдельного `setup()` не
требуется:

```python
from my_project.services import ProjectServices


@pytest.fixture(autouse=True)
def browser():
    ProjectServices.browser
    yield
    ProjectServices.browser.quit()
```
"""

from __future__ import annotations

import operator
from pathlib import Path
from typing import Any, TypeVar

from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.remote.webdriver import WebDriver
from static_dependency_injector.containers import copy
from static_dependency_injector.static_providers import (
    Callable,
    Delegate,
    Singleton,
    TestContextSingleton,
)
from tquality_core import Logger
from tquality_core.di import CoreServices
from typing_extensions import deprecated

from tquality_selenium.browser import BrowserService
from tquality_selenium.config import SeleniumConfig
from tquality_selenium.screencast_provider import SeleniumScreencastProvider
from tquality_selenium.screenshot_provider import SeleniumScreenshotProvider
from tquality_selenium.services.collection_factory import CollectionFactory
from tquality_selenium.services.context_manager import ContextManager
from tquality_selenium.services.driver_waiter import DriverWaiter
from tquality_selenium.services.element_factory import ElementFactory
from tquality_selenium.services.waiter import Waiter

T = TypeVar("T")


@copy(CoreServices)
class SeleniumServices(CoreServices):
    """Composition root для Selenium-фреймворка.

    Наследует ядровый `CoreServices` (спайн `config` → `logger` → `waiter` +
    авто-регистрацию активного Logger-источника для standalone-`step`) и
    переопределяет только selenium-дельты: `config` → `SeleniumConfig`, `logger`
    с screenshot/screencast-провайдерами, `waiter` с selenium-исключениями.
    `@copy` перевязывает унаследованные зависимости на переопределённые слоты.
    Driver-bound сервисы (`browser`, `driver`, провайдеры, `driver_waiter`,
    фабрики) - добавлены здесь.
    """

    # testlocal: пересобирается под каждый тест. Per-test плагин ядра смещает
    # `config_search_dir` на директорию теста, а бандл-плагин static-di сбрасывает
    # testlocal-провайдеры после теста - поэтому `SeleniumConfig()` резолвится под
    # правильный `config.json5` сам, без ручного rebuild/override.
    config: SeleniumConfig = TestContextSingleton(SeleniumConfig)
    # testlocal: браузер живёт ровно один тест (переиспользования сессии между
    # тестами не бывает). Бандл-плагин static-di дропает инстанс после теста -
    # ручной reset в фикстуре не нужен, достаточно `.quit()` закрыть сессию.
    browser: BrowserService = TestContextSingleton(BrowserService, config=config)
    # WebDriver текущего `browser`, резолвится лениво на каждый доступ (свежая
    # сессия). Driver-провайдеры ниже берут его через `Delegate(driver)` - так
    # `@copy` перевязывает их на `browser` подкласса, а `availability_check`
    # гарантирует, что доступ к `.driver` идёт только при запущенной сессии.
    driver: WebDriver = Callable(operator.attrgetter("driver"), browser)
    screenshot_provider: SeleniumScreenshotProvider = Singleton(
        SeleniumScreenshotProvider,
        driver_resolver=Delegate(driver),
        availability_check=BrowserService.is_started,
    )
    screencast_provider: SeleniumScreencastProvider = Singleton(
        SeleniumScreencastProvider,
        driver_resolver=Delegate(driver),
        availability_check=BrowserService.is_started,
        config=config,
    )
    # testlocal, как в core: свежий per-test Logger, подхватывает per-test `config`.
    logger: Logger = TestContextSingleton(
        Logger,
        config=config,
        screenshot_provider=screenshot_provider,
        screencast_provider=screencast_provider,
    )
    waiter: Waiter = TestContextSingleton(
        Waiter,
        config=config,
        logger_resolver=Delegate(logger),
        ignored_exceptions=(NoSuchElementException, StaleElementReferenceException),
        default_raise_cls=TimeoutException,
    )
    # testlocal: держит per-test `waiter` (значение) + driver-резолвер, поэтому
    # пересобирается под каждый тест вместе с waiter/browser.
    driver_waiter: DriverWaiter = TestContextSingleton(
        DriverWaiter,
        waiter=waiter,
        driver_resolver=Delegate(driver),
    )
    element_factory: ElementFactory = Singleton(ElementFactory)
    # Инъекция резолверов (не значений) через `Delegate`: driver/logger/waiter -
    # testlocal, поэтому фабрика/менеджер берут актуальный per-test экземпляр, а
    # `@copy` перевязывает инъекции на слоты подкласса (следуют за leaf-контейнером).
    collection_factory: CollectionFactory = Singleton(
        CollectionFactory,
        driver_resolver=Delegate(driver),
        logger_resolver=Delegate(logger),
    )
    context_manager: ContextManager = Singleton(
        ContextManager,
        driver_resolver=Delegate(driver),
        logger_resolver=Delegate(logger),
        waiter_resolver=Delegate(waiter),
    )

    @classmethod
    @deprecated(
        "setup() больше не нужен и ничего не делает: per-test плагин ядра "
        "смещает config-dir на директорию теста, а config - testlocal "
        "(резолвится лениво под каждый тест). Уберите вызов."
    )
    def setup(cls, config_dir: Path | str | None = None) -> None:
        """No-op (deprecated), оставлен для обратной совместимости.

        Раньше задавал базовую директорию поиска `config.json5`. Теперь это
        делает per-test плагин ядра (смещает `config_search_dir` на директорию
        каждого теста), а `config` - testlocal и резолвится лениво под тест -
        поэтому регистрировать базовую директорию не нужно.
        """

    @classmethod
    def get_service(cls, service_type: type[T]) -> T:
        """Вернуть экземпляр сервиса по типу из контейнера `cls`.

        Ищет провайдер, производящий `service_type` (или его подкласс). Подкласс
        (`@copy`) резолвит свои переопределения - `ProjectServices.get_service(...)`:

        ```python
        browser = SeleniumServices.get_service(BrowserService)
        ```
        """
        for provider in cls.providers.values():
            produces = getattr(provider, "provides", None)
            if produces is service_type or (isinstance(produces, type) and issubclass(produces, service_type)):
                result: Any = provider()
                return result  # type: ignore[no-any-return]
        raise LookupError(
            f"В {cls.__name__} нет сервиса типа {service_type.__name__}",
        )

    @classmethod
    def is_browser_started(cls) -> bool:
        """True, если в текущем контексте запущен WebDriver."""
        return BrowserService.is_started()


__all__ = ["SeleniumServices"]
