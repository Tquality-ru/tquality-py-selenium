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
from tquality_selenium.config import BrowserConfig

_HEALTHCHECK_URL = (
    "data:text/html,<html><head><title>healthcheck</title>"
    "</head><body>ok</body></html>"
)

@pytest.mark.parametrize(
    ("browser", "headless", "capabilities"),
    [
        pytest.param(
            BrowserType.CHROME, True,
            Capabilities(platformName="mac", browserVersion="stable"),
            id="chrome-mac",
            marks=[pytest.mark.chrome, pytest.mark.macos],
        ),
        pytest.param(
            BrowserType.CHROME, True,
            Capabilities(platformName="linux", browserVersion="stable"),
            id="chrome-linux",
            marks=[pytest.mark.chrome, pytest.mark.linux],
        ),
        pytest.param(
            BrowserType.CHROME, True,
            Capabilities(platformName="windows", browserVersion="stable"),
            id="chrome-windows",
            marks=[pytest.mark.chrome, pytest.mark.windows],
        ),
        pytest.param(
            BrowserType.FIREFOX, True, Capabilities(platformName="mac"),
            id="firefox-mac",
            marks=[pytest.mark.firefox, pytest.mark.macos],
        ),
        pytest.param(
            BrowserType.FIREFOX, True, Capabilities(platformName="linux"),
            id="firefox-linux",
            marks=[pytest.mark.firefox, pytest.mark.linux],
        ),
        pytest.param(
            BrowserType.FIREFOX, True, Capabilities(platformName="windows"),
            id="firefox-windows",
            marks=[pytest.mark.firefox, pytest.mark.windows],
        ),
        pytest.param(
            BrowserType.EDGE, True, Capabilities(platformName="mac"),
            id="edge-mac",
            marks=[pytest.mark.edge, pytest.mark.macos],
        ),
        pytest.param(
            BrowserType.EDGE, True, Capabilities(platformName="linux"),
            id="edge-linux",
            marks=[pytest.mark.edge, pytest.mark.linux],
        ),
        pytest.param(
            BrowserType.EDGE, True, Capabilities(platformName="windows"),
            id="edge-windows",
            marks=[pytest.mark.edge, pytest.mark.windows],
        ),
        pytest.param(
            BrowserType.SAFARI, False, Capabilities(platformName="mac"),
            id="safari-mac",
            marks=[pytest.mark.safari, pytest.mark.macos],
        ),
        pytest.param(
            BrowserType.UNDETECTED_CHROME, True,
            Capabilities(platformName="windows", browserVersion="undetected"),
            id="undetected-windows",
            marks=[pytest.mark.undetected, pytest.mark.windows],
        ),
    ],
)
def test_browsers_smoke(
    browser: BrowserType,
    headless: bool,
    capabilities: Capabilities,
) -> None:
    block = BrowserConfig(headless=headless)
    cfg = SeleniumConfig(
        browser=browser,
        capabilities=capabilities,
        **{browser.value.replace("-", "_"): block},  # type: ignore[arg-type]
    )
    service = BrowserService(cfg)
    try:
        service.open(_HEALTHCHECK_URL)
        assert "healthcheck" in service.driver.title
    finally:
        service.quit()
