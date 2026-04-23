"""Тесты проверки поддержки браузера на текущей ОС."""
from __future__ import annotations

from pathlib import Path

import pytest

from tquality_selenium import BrowserType, SeleniumConfig
from tquality_selenium.browser import (
    BrowserNotSupportedError,
    BrowserService,
)
from tquality_selenium.config import is_browser_supported_on_current_os


def test_chrome_supported_everywhere() -> None:
    assert is_browser_supported_on_current_os(BrowserType.CHROME) is True


def test_firefox_supported_everywhere() -> None:
    assert is_browser_supported_on_current_os(BrowserType.FIREFOX) is True


def test_undetected_chrome_supported_everywhere() -> None:
    assert is_browser_supported_on_current_os(BrowserType.UNDETECTED_CHROME) is True


def test_all_browser_types_covered_in_os_map() -> None:
    """Каждое значение BrowserType должно быть в карте поддержки ОС."""
    from tquality_selenium.config import _BROWSER_OS_SUPPORT
    for browser in BrowserType:
        assert browser in _BROWSER_OS_SUPPORT, (
            f"{browser.value} отсутствует в _BROWSER_OS_SUPPORT"
        )


def test_safari_only_on_macos(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.platform", "linux")
    assert is_browser_supported_on_current_os(BrowserType.SAFARI) is False
    monkeypatch.setattr("sys.platform", "darwin")
    assert is_browser_supported_on_current_os(BrowserType.SAFARI) is True


def test_edge_on_mac_and_windows_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.platform", "linux")
    assert is_browser_supported_on_current_os(BrowserType.EDGE) is False
    monkeypatch.setattr("sys.platform", "darwin")
    assert is_browser_supported_on_current_os(BrowserType.EDGE) is True
    monkeypatch.setattr("sys.platform", "win32")
    assert is_browser_supported_on_current_os(BrowserType.EDGE) is True


def test_browser_service_raises_on_unsupported_os(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.platform", "linux")
    cfg = SeleniumConfig(browser=BrowserType.SAFARI)

    with pytest.raises(BrowserNotSupportedError) as exc_info:
        BrowserService(cfg)

    assert "safari" in str(exc_info.value).lower()
    assert "linux" in str(exc_info.value)
