# tquality-py-selenium

[![PyPI](https://img.shields.io/pypi/v/tquality-py-selenium)](https://pypi.org/project/tquality-py-selenium/)
[![License](https://img.shields.io/pypi/l/tquality-py-selenium)](https://github.com/Tquality-ru/tquality-py-selenium/blob/master/LICENSE)
[![GitHub](https://img.shields.io/badge/GitHub-Tquality--ru%2Ftquality--py--selenium-blue?logo=github)](https://github.com/Tquality-ru/tquality-py-selenium)

**Языки:** [English](README.md) · **Русский**

Интеграция Selenium на основе [tquality-py-core](https://github.com/Tquality-ru/tquality-py-core).

## Компоненты

- **`SeleniumConfig`** - расширение `BaseConfig` с полем выбора `browser`
  и отдельными вложенными блоками `chrome`, `firefox`, `edge`, `safari`,
  `undetected_chrome` (все блоки сосуществуют) + вложенный блок
  `screencast` для видеозаписи шагов.
- **`BrowserType`** - перечисление: `chrome`, `firefox`, `edge`, `safari`,
  `undetected-chrome`. Доступность для текущей ОС проверяется `OSUtils` при
  запуске браузера (с немедленной остановкой при ошибке).
- **`BaseElement`** и производные `Button`, `Input`, `CheckBox`, `Label`
  с полным набором методов: `click`, `text`, `get_attribute`,
  `wait.until_*` (`element.wait` возвращает per-element
  `ElementWaiter` - можно чейнить:
  `button.wait.until_clickable().click()`), `js_actions` (лениво
  связывается с элементом).
- **`BaseForm`** - базовый класс страницы с `title`, `current_url`,
  `element_factory` (через композиционный корень).
- **`SeleniumServices`** - композиционный корень (контейнер внедрения зависимостей
  на основе `dependency-injector`). Для добавления или замены любой службы
  используется наследование.

## Службы

- **`BrowserService`** - обёртка над WebDriver, параметры берутся из
  `config.active_browser`.
- **`Waiter`** - ожидания на уровне страницы. Ожидания на уровне
  элемента доступны per-element через `element.wait` (возвращает
  `ElementWaiter[Self]`, привязанный к элементу); чейнятся - каждый
  метод возвращает сам элемент.
- **`ElementFactory`** - фабрика элементов.
- **`JsActions`** + **`ElementJsActions`** - действия через JavaScript
  над страницей и элементами.
- **`CollectionFactory`** - фабрика коллекций моделей Pydantic из DOM
  (+ `DomField.css/xpath`).
- **`SeleniumScreenshotProvider`** - снимки экрана для шагов уровня `CRITICAL`.
- **`SeleniumScreencastProvider`** - видеозапись в формате webm (VP9 через
  imageio-ffmpeg) для шагов `WITH_SCREENCAST`.

## Требования

- Python 3.12+
- Установленные браузеры (для тестов с настоящим драйвером).

## Установка

Пакет публикуется в [публичный PyPI](https://pypi.org/project/tquality-py-selenium/).
Это рекомендуемый способ установки для всех потребителей:

```bash
pip install tquality-py-selenium
```

Или в `pyproject.toml`:

```toml
dependencies = [
    "tquality-py-selenium>=0.1.5",
]
```

### Альтернатива: установка из GitHub-зеркала

Если нужна сборка из исходников (например, для проверки коммита,
ещё не вышедшего в релиз), пакет также доступен из публичного
GitHub-зеркала по тегу:

```toml
dependencies = [
    "tquality-py-selenium @ git+https://github.com/Tquality-ru/tquality-py-selenium.git@v0.1.5",
]
```

Прямые git-ссылки требуют `[tool.hatch.metadata] allow-direct-references = true` у потребителя.

## Быстрый старт

```python
# conftest.py
import pytest
from tquality_selenium import SeleniumServices

# config.json5 рядом с тестом подхватывается автоматически: per-test плагин
# ядра нацеливает поиск конфигов на каталог теста. setup() не нужен.


@pytest.fixture(autouse=True)
def browser():
    yield
    if SeleniumServices.is_browser_started():
        SeleniumServices.browser.quit()  # закрыть WebDriver-сессию
    # browser / config / logger / waiter - TestContextSingleton: инстансы
    # сбрасываются под каждый тест бандл-плагином static-di.
```

```python
# pages/login_page.py
from tquality_selenium import BaseForm, By


class LoginPage(BaseForm):
    def __init__(self) -> None:
        self._username = self.element_factory.input(
            By.id("username"), "Имя пользователя",
        )
        self._password = self.element_factory.input(
            By.id("password"), "Пароль",
        )
        self._submit = self.element_factory.button(
            By.id("login-btn"), "Войти",
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

    // Все браузеры заранее настроены, переключение - смена browser выше.
    "chrome": { "headless": true },
    "firefox": { "headless": true },
    "undetected_chrome": { "headless": false },

    "screencast": {
        "fps": 10,
        "frame_interval": 0.1,  // чаще фиксируются короткие состояния интерфейса
    },
}
```

## Расширение через наследование от `SeleniumServices`

Чтобы добавить свои службы, унаследуйтесь от `SeleniumServices` с `@copy`
(чтобы переопределения перевязывали унаследованные зависимости). Область
действия определяется типом поставщика `static-dependency-injector`;
поставщики объявляются типизированными атрибутами и **читаются как значения**
(`Services.api_client`, а не `.api_client()`):

| Область действия     | Поставщик                      | Время жизни                                    |
| -------------------- | ------------------------------ | ---------------------------------------------- |
| **глобальная**       | `Singleton`                    | Один экземпляр на весь процесс pytest.         |
| **уровня теста**     | `TestContextSingleton`         | Новый экземпляр на каждый тест; авто-сброс бандл-плагином. |
| **уровня сессии**    | `ContextLocalSingleton` + сброс в фикстуре `scope="session"` | Один экземпляр на contextvars-контекст, сброс на выходе. |
| **одноразовая**      | `Factory`                      | Свежий экземпляр на каждое обращение.          |

```python
# my_project/services.py
from static_dependency_injector.containers import copy
from static_dependency_injector.static_providers import (
    ContextLocalSingleton,
    Factory,
    Singleton,
    TestContextSingleton,
)
from tquality_selenium import BrowserService, SeleniumServices

from my_project.clients import ApiClient, CurrentUser, SessionData, TempDirFactory


@copy(SeleniumServices)
class ProjectServices(SeleniumServices):
    # Глобальная: один клиент API на процесс.
    api_client: ApiClient = Singleton(ApiClient)

    # Уровня теста: свежее состояние на каждый тест, авто-сброс бандл-плагином.
    current_user: CurrentUser = TestContextSingleton(CurrentUser)

    # Уровня сессии: данные на весь прогон, сброс в session-фикстуре.
    session_data: SessionData = ContextLocalSingleton(SessionData)

    # Одноразовая: каждое обращение - свежий экземпляр.
    temp_dir: TempDirFactory = Factory(TempDirFactory)

    # Замена существующей службы (перевязывается на родительский config через
    # @copy; ссылка на унаследованный провайдер - `.provider.config`):
    # browser: BrowserService = TestContextSingleton(
    #     MyBrowserService, config=SeleniumServices.provider.config,
    # )
```

```python
# conftest.py
import pytest

from my_project.services import ProjectServices


# current_user - TestContextSingleton: авто-сброс под каждый тест, фикстура не нужна.


@pytest.fixture(scope="session", autouse=True)
def _reset_session_scoped_services():
    """ContextLocalSingleton-провайдеры уровня сессии сбрасываются в конце прогона."""
    yield
    ProjectServices.provider.session_data.reset()


@pytest.fixture(autouse=True)
def browser():
    yield
    if ProjectServices.is_browser_started():
        ProjectServices.browser.quit()  # browser - testlocal, инстанс авто-сбрасывается
```

Получить службу по типу, без привязки к имени поставщика - удобно
внутри элементов и форм, которые не видят конкретный подкласс:

```python
from tquality_selenium import SeleniumServices
from my_project.clients import ApiClient

client = SeleniumServices.get_service(ApiClient)
```

`get_service` идёт в активный композиционный корень (тот, что последним
вызвал `setup()`), поэтому подменённые в подклассе поставщики
обрабатываются прозрачно.

## Видеозапись шагов

```python
from tquality_selenium import LogLevel, step


def login():
    with step("Вход в систему", level=LogLevel.WITH_SCREENCAST):
        ...
    # К отчёту allure прикреплён webm с записью всего шага.
```

Захват идёт в фоновом потоке с `contextvars.copy_context()`, чтобы не
открывалась вторая сессия WebDriver. Стратегия захвата кадра:
BiDi → CDP → классический `get_screenshot_as_png` (с предупреждением при
откате на запасной вариант).

## Разработка

См. [CONTRIBUTING.md](CONTRIBUTING.md).

## История версий

См. [CHANGELOG.md](CHANGELOG.md).
