# tquality-py-selenium

**Languages:** **English** · [Русский](README.ru.md)

Selenium integration built on top of [tquality-py-core](https://github.com/Tquality-ru/tquality-py-core).

## Components

- **`SeleniumConfig`** — extension of `BaseConfig` with a `browser` selector
  field and separate nested blocks `chrome`, `firefox`, `edge`, `safari`,
  `undetected_chrome` (all blocks coexist), plus a nested `screencast`
  block for step video recording.
- **`BrowserType`** — enum: `chrome`, `firefox`, `edge`, `safari`,
  `undetected-chrome`. Per-OS availability is checked by `OSUtils` at
  browser startup (with an immediate failure on mismatch).
- **`BaseElement`** and the typed subclasses `Button`, `Input`, `CheckBox`,
  `Label` with a full surface: `click`, `text`, `get_attribute`,
  `wait.until_*` (`element.wait` returns a per-element `ElementWaiter` —
  `button.wait.until_clickable().click()`), `js_actions` (lazily bound
  to the element).
- **`BaseForm`** — page base class with `title`, `current_url`,
  `element_factory` (resolved via the composition root).
- **`SeleniumServices`** — composition root (a `dependency-injector`
  container). Subclass it to add or replace any service.

## Services

- **`BrowserService`** — `WebDriver` wrapper; parameters are taken from
  `config.active_browser`.
- **`Waiter`** — explicit waits at the page level. Element-level
  waits are exposed per-element via `element.wait` (returns a
  per-element `ElementWaiter[Self]`); chainable methods return the
  bound element.
- **`ElementFactory`** — element factory.
- **`JsActions`** + **`ElementJsActions`** — JavaScript actions on the
  page and on individual elements.
- **`CollectionFactory`** — Pydantic-model collection factory backed by
  the DOM (+ `DomField.css/xpath`).
- **`SeleniumScreenshotProvider`** — screenshots for steps at the
  `CRITICAL` log level.
- **`SeleniumScreencastProvider`** — webm video recording (VP9 via
  imageio-ffmpeg) for steps at `WITH_SCREENCAST`.

## Requirements

- Python 3.12+
- Installed browsers (for tests against a real driver).

## Installation

The package is published to [public PyPI](https://pypi.org/project/tquality-py-selenium/).
This is the recommended installation path for all consumers:

```bash
pip install tquality-py-selenium
```

Or in `pyproject.toml`:

```toml
dependencies = [
    "tquality-py-selenium>=0.1.5",
]
```

### Alternative: install from the GitHub mirror

For a source build (e.g., to verify a commit that has not yet been
released), the package is also available by git tag from the public
GitHub mirror:

```toml
dependencies = [
    "tquality-py-selenium @ git+https://github.com/Tquality-ru/tquality-py-selenium.git@v0.1.5",
]
```

Direct git references require `[tool.hatch.metadata] allow-direct-references = true` on the consumer's side.

## Quick start

```python
# conftest.py
import pytest
from tquality_selenium import SeleniumServices

# Composition root. config_dir defaults to the directory of this file,
# so config.json5 next to conftest.py is picked up regardless of the
# current working directory.
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
from tquality_selenium import BaseForm, By


class LoginPage(BaseForm):
    def __init__(self) -> None:
        self._username = self.element_factory.input(
            By.id("username"), "Username",
        )
        self._password = self.element_factory.input(
            By.id("password"), "Password",
        )
        self._submit = self.element_factory.button(
            By.id("login-btn"), "Sign in",
        )
        super().__init__(unique_element=self._username, name="Login page")

    def login(self, username: str, password: str) -> None:
        self._username.type_text(username)
        self._password.type_text(password)
        self._submit.click()
```

```jsonc
// config.json5 — next to conftest.py
{
    "$schema": "https://cdn.jsdelivr.net/gh/Tquality-ru/tquality-py-selenium@v0.1.4/schema/config.schema.json",

    "base_url": "https://example.com",
    "browser": "chrome",
    "highlight_elements": true,  // red outline during interactions

    // All browsers are pre-configured — switching is a single line above.
    "chrome": { "headless": true },
    "firefox": { "headless": true },
    "undetected_chrome": { "headless": false },

    "screencast": {
        "fps": 10,
        "frame_interval": 0.1,  // captures short UI states more often
    },
}
```

## Extending via subclasses of `SeleniumServices`

To add custom services, subclass `SeleniumServices`. The scope is
defined by the `dependency-injector` provider type (and where it is
reset in fixtures):

| Scope            | Provider                                                                | Lifetime                                                       |
| ---------------- | ----------------------------------------------------------------------- | -------------------------------------------------------------- |
| **global**       | `providers.Singleton`                                                   | One instance per pytest process.                               |
| **session**      | `providers.ContextLocalSingleton` + reset in a `scope="session"` fixture | One instance per session, reset on exit.                       |
| **test**         | `providers.ContextLocalSingleton` + reset in an `autouse=True` fixture   | A new instance per test.                                       |
| **transient**    | `providers.Factory`                                                     | A fresh instance on every `services.my_service()` call.        |

```python
# my_project/services.py
from dependency_injector import providers
from tquality_selenium import SeleniumServices

from my_project.clients import ApiClient, CurrentUser, TempDirFactory


class ProjectServices(SeleniumServices):
    # Global: one API client per process.
    api_client = providers.Singleton(ApiClient)

    # Session: data shared across all tests of a single run.
    session_data = providers.ContextLocalSingleton(SessionData)

    # Test: fresh state per test.
    current_user = providers.ContextLocalSingleton(CurrentUser)

    # Transient: a fresh instance on every access.
    temp_dir = providers.Factory(TempDirFactory)

    # Replacing an existing service (referencing the parent's config):
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
    """Test-scoped ContextLocalSingleton instances are reset after each test."""
    yield
    ProjectServices.current_user.reset()


@pytest.fixture(scope="session", autouse=True)
def _reset_session_scoped_services():
    """Session-scoped ContextLocalSingleton instances are reset at the end of the pytest session."""
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

Resolving a service by type, without referencing the provider name —
useful inside elements and forms that don't see the concrete subclass:

```python
from tquality_selenium import SeleniumServices
from my_project.clients import ApiClient

client = SeleniumServices.get_service(ApiClient)
```

`get_service` goes to the active composition root (the one whose
`setup()` was called last), so providers replaced in a subclass are
resolved transparently.

## Step video recording

```python
from tquality_selenium import LogLevel, step


def login():
    with step("Sign in", level=LogLevel.WITH_SCREENCAST):
        ...
    # An attached webm of the whole step is added to the allure report.
```

Capture runs in a background thread with `contextvars.copy_context()`
so a second WebDriver session is not opened. The frame-capture
strategy is BiDi → CDP → classic `get_screenshot_as_png` (with a
warning on fallback).

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Version history

See [CHANGELOG.md](CHANGELOG.md).