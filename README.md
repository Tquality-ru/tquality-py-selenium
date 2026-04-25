# tquality-py-selenium

Selenium-интеграция поверх [tquality-py-core](https://github.com/Tquality-ru/tquality-py-core).

## Что входит

- **`SeleniumConfig`** - расширение `BaseConfig` с полем-выбором `browser`
  и отдельными под-блоками `chrome`, `firefox`, `edge`, `safari`,
  `undetected_chrome` (все блоки живут одновременно) + под-блок
  `screencast` для видеозаписи шагов.
- **`BrowserType`** - enum: `chrome`, `firefox`, `edge`, `safari`,
  `undetected-chrome`. Доступность по ОС проверяется `OSUtils` при
  старте браузера (fail-fast).
- **`BrowserService`** - обёртка над WebDriver, параметры берутся из
  `config.active_browser`.
- **`BaseElement`** и производные `Button`, `Input`, `CheckBox`, `Label`
  с полным API: `click`, `text`, `get_attribute`, `wait_until_*`,
  `js_actions` (лениво резолвится к элементу).
- **`BaseForm`** - базовый page-object с `title`, `current_url`,
  `element_factory` (через composition root).
- **Сервисы**: `Waiter`, `ElementWaiter`, `ElementFactory`, `JsActions`
  + `ElementJsActions`, `CollectionFactory` (фабрика коллекций
  Pydantic-моделей из DOM) + `DomField.css/xpath`.
- **`SeleniumScreenshotProvider`** - скриншоты для `CRITICAL` шагов.
- **`SeleniumScreencastProvider`** - webm-видеозапись (VP9 через
  imageio-ffmpeg) для шагов `WITH_SCREENCAST`.
- **`SeleniumServices`** - composition root (DI-контейнер на базе
  `dependency-injector`). Наследуйтесь, чтобы добавить или заменить
  любой сервис.

## Требования

- Python 3.12+
- Установленные браузеры (для тестов с реальным драйвером).

## Установка

Пакет пока не на публичном PyPI. Ставится из публичного GitHub-зеркала
по git-тегу:

```toml
[project]
dependencies = [
    "tquality-py-selenium @ git+https://github.com/Tquality-ru/tquality-py-selenium.git@v0.1.4",
]

# hatch требует явного разрешения direct-references для git-URL.
[tool.hatch.metadata]
allow-direct-references = true
```

## Быстрый старт

```python
# conftest.py
import pytest
from tquality_selenium import SeleniumServices

# Composition root. config_dir по умолчанию - директория этого файла,
# так что config.json5 рядом с conftest.py подхватится независимо от cwd.
SeleniumServices.setup()


@pytest.fixture(autouse=True)
def browser():
    SeleniumServices.browser()
    yield
    SeleniumServices.browser().quit()
    SeleniumServices.browser.reset()
    SeleniumServices.logger.reset()
```

```python
# pages/login_page.py
from selenium.webdriver.common.by import By
from tquality_selenium import BaseForm


class LoginPage(BaseForm):
    def __init__(self) -> None:
        self._username = self.element_factory.input(
            By.ID, "username", "Логин",
        )
        self._password = self.element_factory.input(
            By.ID, "password", "Пароль",
        )
        self._submit = self.element_factory.button(
            By.ID, "login-btn", "Войти",
        )
        super().__init__(unique_element=self._username, name="Страница входа")

    def login(self, username: str, password: str) -> None:
        self._username.type_text(username)
        self._password.type_text(password)
        self._submit.click()
```

```jsonc
// config.json5 - рядом с conftest.py
{
    "$schema": "https://cdn.jsdelivr.net/gh/Tquality-ru/tquality-py-selenium@v0.1.4/schema/config.schema.json",

    "base_url": "https://example.com",
    "browser": "chrome",
    "highlight_elements": true,  // красная рамка на время взаимодействия

    // Все браузеры заранее сконфигурированы, переключение - смена browser выше.
    "chrome": { "headless": true },
    "firefox": { "headless": true },
    "undetected_chrome": { "headless": false },

    "screencast": {
        "fps": 10,
        "frame_interval": 0.1,  // чаще ловим короткие состояния UI
    },
}
```

## Расширение через подкласс `SeleniumServices`

Наследуйтесь и добавляйте свои сервисы. Scope определяется типом
провайдера `dependency-injector` (+ где сбрасывается в фикстурах):

| Scope             | Провайдер                      | Lifetime                                       |
| ----------------- | ------------------------------ | ---------------------------------------------- |
| **global**        | `providers.Singleton`          | Один экземпляр на весь процесс pytest.         |
| **session-scoped**| `providers.ContextLocalSingleton` + reset в `scope="session"` фикстуре | Один экземпляр на сессию, сбрасывается на выходе. |
| **test-scoped**   | `providers.ContextLocalSingleton` + reset в `autouse=True` фикстуре    | Новый экземпляр на каждый тест. |
| **transient**     | `providers.Factory`            | Новый экземпляр на каждый вызов `services.my_service()`. |

```python
# my_project/services.py
from dependency_injector import providers
from tquality_selenium import SeleniumServices

from my_project.clients import ApiClient, CurrentUser, TempDirFactory


class ProjectServices(SeleniumServices):
    # Global: один API-клиент на процесс.
    api_client = providers.Singleton(ApiClient)

    # Session-scoped: данные, общие для всех тестов одного прогона.
    session_data = providers.ContextLocalSingleton(SessionData)

    # Test-scoped: новое состояние на каждый тест.
    current_user = providers.ContextLocalSingleton(CurrentUser)

    # Transient: каждое обращение - свежий экземпляр.
    temp_dir = providers.Factory(TempDirFactory)

    # Существующий сервис - заменить (ссылаемся на родительский config):
    # browser = providers.ContextLocalSingleton(
    #     MyBrowserService, config=SeleniumServices.config,
    # )
```

```python
# conftest.py
import pytest

from my_project.services import ProjectServices

ProjectServices.setup()


@pytest.fixture(autouse=True)
def _reset_test_scoped_services():
    """Test-scoped ContextLocalSingleton'ы сбрасываются после каждого теста."""
    yield
    ProjectServices.current_user.reset()


@pytest.fixture(scope="session", autouse=True)
def _reset_session_scoped_services():
    """Session-scoped сбрасываются в конце сессии pytest."""
    yield
    ProjectServices.session_data.reset()


@pytest.fixture(autouse=True)
def browser():
    ProjectServices.browser()
    yield
    ProjectServices.browser().quit()
    ProjectServices.browser.reset()
    ProjectServices.logger.reset()
```

Достать сервис по типу, без привязки к имени провайдера - удобно
внутри элементов/форм, которые не видят конкретный подкласс:

```python
from tquality_selenium import SeleniumServices
from my_project.clients import ApiClient

client = SeleniumServices.get_service(ApiClient)
```

`get_service` идёт в активный composition root (тот, что последним
вызвал `setup()`), поэтому подменённые в подклассе провайдеры
обрабатываются прозрачно.

## Screencast шагов

```python
from tquality_selenium import LogLevel, step


def login():
    with step("Вход в систему", level=LogLevel.WITH_SCREENCAST):
        ...
    # К allure-отчёту прикреплён webm с записью всего шага.
```

Захват идёт в фоновом потоке с `contextvars.copy_context()`, чтобы не
открывалась вторая сессия WebDriver. Стратегия захвата кадра:
BiDi → CDP → классический `get_screenshot_as_png` (с warning на фолбеке).

## Разработка

См. [CONTRIBUTING.md](CONTRIBUTING.md).

## CI/CD

GitLab CI на каждом MR и на master:

- **`mypy`** - strict-режим.
- **`tests:linux`** - pytest без реальных браузеров.
- **`tests:macos`** - healthcheck 5 браузеров на macos-runner.

На git-теге `vX.Y.Z`:

- **`publish`** - сборка (версия из тега через `hatch-vcs`) и
  публикация в GitLab Package Registry.
- **`mirror-to-github`** - master и сам тег уходят в
  https://github.com/Tquality-ru/tquality-py-selenium.

История версий - в [CHANGELOG.md](CHANGELOG.md).
