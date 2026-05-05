"""Smoke-тесты всех поддерживаемых браузеров.

Для каждого браузера прогоняется минимальная цепочка через публичный API
фреймворка: `SeleniumConfig` → `BrowserService._create_driver` → `open` →
`driver.title` → `quit`. Тем самым тест одновременно:

- healthcheck CI-окружения: на runner'е установлены все нужные браузеры
  и драйверы;
- интеграционный тест фреймворка: `BrowserService` корректно поднимает
  каждую ветку `_create_driver` и корректно останавливает драйвер.

Используется data-URL, чтобы не зависеть от сети.

Каждый smoke маркирован всеми ОС, на которых браузер поддерживается
(см. `OSUtils._BROWSER_OS_SUPPORT`). CI-job выбирает свою подсетку:

- `tests:macos-browsers-healthcheck`: `-m macos` - все 5 браузеров;
- `tests:linux-browsers-healthcheck`: `-m linux` - chrome, firefox,
  edge, undetected (selenium image поставляет всё запечённым);
- `tests:windows-browsers-healthcheck`: `-m windows` - chrome, firefox,
  edge, undetected.

Юнит-тесты `tests:linux` фильтруются через `-m "not macos"` -
любой smoke имеет хотя бы метку `macos` и не попадает в этот job.
"""
from __future__ import annotations

import pytest

from tquality_selenium import BrowserService, BrowserType, SeleniumConfig

_HEALTHCHECK_URL = (
    "data:text/html,<html><head><title>healthcheck</title>"
    "</head><body>ok</body></html>"
)


def _smoke(browser: BrowserType, *, headless: bool = True) -> None:
    """Запустить браузер, открыть тестовую страницу, закрыть."""
    from tquality_selenium.config import BrowserConfig

    block = BrowserConfig(headless=headless)
    # Применяем один и тот же блок к выбранному браузеру - остальные
    # подтягивают дефолты.
    cfg = SeleniumConfig(
        browser=browser,
        **{browser.value.replace("-", "_"): block},  # type: ignore[arg-type]
    )
    service = BrowserService(cfg)
    try:
        service.open(_HEALTHCHECK_URL)
        assert "healthcheck" in service.driver.title
    finally:
        service.quit()


@pytest.mark.macos
@pytest.mark.linux
@pytest.mark.windows
@pytest.mark.chrome
def test_chrome_smoke() -> None:
    _smoke(BrowserType.CHROME)


@pytest.mark.macos
@pytest.mark.linux
@pytest.mark.windows
@pytest.mark.firefox
def test_firefox_smoke() -> None:
    _smoke(BrowserType.FIREFOX)


@pytest.mark.macos
@pytest.mark.linux
@pytest.mark.windows
@pytest.mark.edge
def test_edge_smoke() -> None:
    _smoke(BrowserType.EDGE)


@pytest.mark.macos
@pytest.mark.safari
def test_safari_smoke() -> None:
    # Safari не поддерживает headless; BrowserService игнорирует флаг.
    _smoke(BrowserType.SAFARI, headless=False)


@pytest.mark.macos
@pytest.mark.linux
@pytest.mark.windows
@pytest.mark.undetected
def test_undetected_chrome_smoke() -> None:
    _smoke(BrowserType.UNDETECTED_CHROME)
