"""Smoke-тесты всех поддерживаемых браузеров.

Каждый случай прогоняет минимальную цепочку через публичный API:
`SeleniumConfig` → `BrowserService._create_driver` → `open` →
`driver.title` → `quit`. Закрывает сразу две дыры:

- healthcheck CI: на целевом node установлены нужные браузеры и драйверы;
- интеграционный тест фреймворка: `BrowserService` корректно поднимает
  каждую ветку `_create_driver`.

Используется data-URL, чтобы не зависеть от сети.

Маркеры `chrome` / `firefox` / `edge` / `safari` / `undetected` плюс
`macos` / `linux` / `windows` крепятся на каждый pytest.param; CI-job
выбирает подсетку через `-m`.
"""
from __future__ import annotations

import pytest

from tquality_selenium import BrowserService, BrowserType, Capabilities, SeleniumConfig
from tquality_selenium.browser import BrowserNotSupportedError
from tquality_selenium.config import BrowserConfig


@pytest.mark.parametrize(
    ("browser", "headless", "capabilities"),
    [
        pytest.param(
            BrowserType.CHROME, True,
            Capabilities(platform_name="mac", browser_version="stable"),
            id="chrome-mac",
            marks=[pytest.mark.chrome, pytest.mark.macos],
        ),
        pytest.param(
            BrowserType.CHROME, True,
            Capabilities(platform_name="linux", browser_version="stable"),
            id="chrome-linux",
            marks=[pytest.mark.chrome, pytest.mark.linux],
        ),
        pytest.param(
            BrowserType.CHROME, True,
            Capabilities(platform_name="windows", browser_version="stable"),
            id="chrome-windows",
            marks=[pytest.mark.chrome, pytest.mark.windows],
        ),
        pytest.param(
            BrowserType.FIREFOX, True, Capabilities(platform_name="mac"),
            id="firefox-mac",
            marks=[pytest.mark.firefox, pytest.mark.macos],
        ),
        pytest.param(
            BrowserType.FIREFOX, True, Capabilities(platform_name="linux"),
            id="firefox-linux",
            marks=[pytest.mark.firefox, pytest.mark.linux],
        ),
        pytest.param(
            BrowserType.FIREFOX, True, Capabilities(platform_name="windows"),
            id="firefox-windows",
            marks=[pytest.mark.firefox, pytest.mark.windows],
        ),
        pytest.param(
            BrowserType.EDGE, True, Capabilities(platform_name="mac"),
            id="edge-mac",
            marks=[pytest.mark.edge, pytest.mark.macos],
        ),
        pytest.param(
            BrowserType.EDGE, True, Capabilities(platform_name="linux"),
            id="edge-linux",
            marks=[pytest.mark.edge, pytest.mark.linux],
        ),
        pytest.param(
            BrowserType.EDGE, True, Capabilities(platform_name="windows"),
            id="edge-windows",
            marks=[pytest.mark.edge, pytest.mark.windows],
        ),
        pytest.param(
            BrowserType.SAFARI, False, Capabilities(platform_name="mac"),
            id="safari-mac",
            marks=[pytest.mark.safari, pytest.mark.macos],
        ),
        pytest.param(
            BrowserType.UNDETECTED_CHROME, True,
            Capabilities(platform_name="windows", browser_version="undetected"),
            id="undetected-windows",
            marks=[pytest.mark.undetected, pytest.mark.windows],
        ),
    ],
)
def test_browsers_smoke(
    browser: BrowserType,
    headless: bool,
    capabilities: Capabilities,
    page_url: str,
) -> None:
    block = BrowserConfig(headless=headless)
    cfg = SeleniumConfig(
        browser=browser,
        capabilities=capabilities,
        **{browser.value.replace("-", "_"): block},  # type: ignore[arg-type]  # ty:ignore[invalid-argument-type]
    )
    try:
        service = BrowserService(cfg)
    except BrowserNotSupportedError as exc:
        # Локальный прогон: браузер несовместим с текущей ОС. На remote/grid
        # этот guard не срабатывает (там ОС определяется нодой), и кейс запускается.
        pytest.skip(str(exc))
    try:
        service.open(page_url)
        assert "healthcheck" in service.driver.title
    finally:
        service.quit()
