# tquality-py-selenium

[![PyPI](https://img.shields.io/pypi/v/tquality-py-selenium)](https://pypi.org/project/tquality-py-selenium/)
[![License](https://img.shields.io/pypi/l/tquality-py-selenium)](https://github.com/Tquality-ru/tquality-py-selenium/blob/master/LICENSE)
[![GitHub](https://img.shields.io/badge/GitHub-Tquality--ru%2Ftquality--py--selenium-blue?logo=github)](https://github.com/Tquality-ru/tquality-py-selenium)

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

# config.json5 next to each test is picked up automatically: a per-test core
# plugin points config resolution at the test's directory. No setup() needed.


@pytest.fixture(autouse=True)
def browser():
    yield
    if SeleniumServices.is_browser_started():
        SeleniumServices.browser.quit()  # close the WebDriver session
    # browser / config / logger / waiter are TestContextSingleton -
    # instances are auto-reset per test by the bundled static-di plugin.
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

To add custom services, subclass `SeleniumServices` with `@copy` (so overrides
rewire inherited dependents). The scope is defined by the
`static-dependency-injector` provider type; providers are declared as typed
attributes and **read as values** (`Services.api_client`, not `.api_client()`):

| Scope         | Provider                                                       | Lifetime                                                       |
|---------------|----------------------------------------------------------------|----------------------------------------------------------------|
| **global**    | `Singleton`                                                    | One instance per pytest process.                               |
| **test**      | `TestContextSingleton`                                         | A new instance per test; auto-reset by the bundled plugin.     |
| **session**   | `ContextLocalSingleton` + reset in a `scope="session"` fixture | One instance per contextvars context, reset on exit.           |
| **transient** | `Factory`                                                      | A fresh instance on every access.                              |

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
    # Global: one API client per process.
    api_client: ApiClient = Singleton(ApiClient)

    # Test: fresh state per test, auto-reset by the bundled static-di plugin.
    current_user: CurrentUser = TestContextSingleton(CurrentUser)

    # Session: data shared across a run, reset in a session fixture.
    session_data: SessionData = ContextLocalSingleton(SessionData)

    # Transient: a fresh instance on every access.
    temp_dir: TempDirFactory = Factory(TempDirFactory)

    # Replacing an existing service (rewired onto the parent's config by @copy;
    # reference the inherited provider via `.provider.config`):
    # browser: BrowserService = TestContextSingleton(
    #     MyBrowserService, config=SeleniumServices.provider.config,
    # )
```

```python
# conftest.py
import pytest

from my_project.services import ProjectServices


# current_user is TestContextSingleton - auto-reset per test, no fixture needed.


@pytest.fixture(scope="session", autouse=True)
def _reset_session_scoped_services():
    """Session-scoped ContextLocalSingleton providers reset at the end of the run."""
    yield
    ProjectServices.provider.session_data.reset()


@pytest.fixture(autouse=True)
def browser():
    yield
    if ProjectServices.is_browser_started():
        ProjectServices.browser.quit()  # browser is testlocal - instance auto-reset per test
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