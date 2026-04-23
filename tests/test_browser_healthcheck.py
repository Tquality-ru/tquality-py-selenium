"""Smoke-тесты всех поддерживаемых браузеров.

Для каждого браузера прогоняется минимальная цепочка через публичный API
фреймворка: `SeleniumConfig` → `BrowserService._create_driver` → `open` →
`driver.title` → `quit`. Тем самым тест одновременно:

- healthcheck CI-окружения: на runner'е установлены все нужные браузеры
  и драйверы;
- интеграционный тест фреймворка: `BrowserService` корректно поднимает
  каждую ветку `_create_driver` и корректно останавливает драйвер.

Используется data-URL, чтобы не зависеть от сети.

Все тесты маркированы `macos`, потому что macOS-runner - единственная
платформа, где доступны все пять браузеров (Chrome, Firefox, Edge, Safari,
undetected-chrome). На linux-runner эти тесты отфильтровываются.
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
    cfg = SeleniumConfig(browser=browser, headless=headless)
    service = BrowserService(cfg)
    try:
        service.open(_HEALTHCHECK_URL)
        assert "healthcheck" in service.driver.title
    finally:
        service.quit()


@pytest.mark.macos
@pytest.mark.chrome
def test_chrome_smoke() -> None:
    _smoke(BrowserType.CHROME)


@pytest.mark.macos
@pytest.mark.firefox
def test_firefox_smoke() -> None:
    _smoke(BrowserType.FIREFOX)


@pytest.mark.macos
@pytest.mark.edge
def test_edge_smoke() -> None:
    _smoke(BrowserType.EDGE)


@pytest.mark.macos
@pytest.mark.safari
def test_safari_smoke() -> None:
    # Safari не поддерживает headless; BrowserService игнорирует флаг.
    _smoke(BrowserType.SAFARI, headless=False)


@pytest.mark.macos
@pytest.mark.undetected
def test_undetected_chrome_smoke() -> None:
    _smoke(BrowserType.UNDETECTED_CHROME)
