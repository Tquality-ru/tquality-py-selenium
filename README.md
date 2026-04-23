# tquality-py-selenium

Selenium-интеграция поверх [tquality-py-core](https://git.tquality.ru/frameworks/python/tquality-py-core).

Реализует:

- **SeleniumConfig** - расширение `BaseConfig` с полями `browser`, `headless`,
  `window_width/height`, `page_load_timeout`.
- **BrowserType** - enum (`chrome`, `firefox`, `undetected-chrome`).
- **BrowserService** - управляемый DI сервис с WebDriver внутри.
- **BaseElement** - конкретная реализация `tquality_core.BaseElement` через
  Selenium. От нее наследуются Button, Label, Input, CheckBox.
- **SeleniumScreenshotProvider** - подключает CRITICAL шаги ядра к WebDriver.
- **Container** - DI-контейнер (`dependency-injector`), готовый к расширению.

## Требования

- Python 3.12+

## Установка

Пока репозиторий публикуется только как git-зависимость:

```toml
[project]
dependencies = [
    "tquality-py-selenium @ git+https://git.tquality.ru/frameworks/python/tquality-py-selenium.git@master",
]
```

После публикации на PyPI установка будет через `uv pip install tquality-py-selenium`.

## Быстрый старт

```python
# conftest.py
import pytest
from tquality_selenium import Container, wire_core_integrations

wire_core_integrations()


@pytest.fixture(autouse=True)
def browser():
    Container.browser()
    yield
    Container.browser().quit()
    Container.browser.reset()
    Container.logger.reset()
```

```python
# pages/login_page.py
from selenium.webdriver.common.by import By
from tquality_selenium import BaseForm, Button, Container, Input


class LoginPage(BaseForm):
    def __init__(self) -> None:
        resolver = lambda: Container.browser()
        self._username = Input(
            By.ID, "username", "Логин",
            browser_resolver=resolver,
        )
        self._password = Input(
            By.ID, "password", "Пароль",
            browser_resolver=resolver,
        )
        self._submit = Button(
            By.ID, "login-btn", "Войти",
            browser_resolver=resolver,
        )
        super().__init__(unique_element=self._username, name="Страница входа")

    def login(self, username: str, password: str) -> None:
        self._username.type_text(username)
        self._password.type_text(password)
        self._submit.click()
```

## Разработка

См. [CONTRIBUTING.md](CONTRIBUTING.md).

## CI/CD

GitLab CI запускает две проверки на каждом MR и на master:

- **mypy** - strict-режим проверки типов
- **tests** - запуск pytest с JUnit-отчетом

При публикации git-тега вида `vX.Y.Z` джоб `mirror-to-github` зеркалирует
репозиторий в https://github.com/Tquality-ru/tquality-py-selenium.
