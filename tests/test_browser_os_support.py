"""Тесты проверки поддержки браузера на текущей ОС.

Тред-безопасность: тесты НЕ мутируют `sys.platform` (модуль `sys` шарится
между тредами). Вместо этого используют явный параметр `platform=` в
`OSUtils.is_browser_supported_on_current_os`.
"""
from __future__ import annotations

import sys

import pytest

from tquality_selenium import BrowserType, SeleniumConfig
from tquality_selenium.browser import (
    BrowserNotSupportedError,
    BrowserService,
)
from tquality_selenium.utils.os_utils import OSUtils


def test_chrome_supported_everywhere() -> None:
    assert OSUtils.is_browser_supported_on_current_os(BrowserType.CHROME) is True


def test_firefox_supported_everywhere() -> None:
    assert OSUtils.is_browser_supported_on_current_os(BrowserType.FIREFOX) is True


def test_undetected_chrome_supported_everywhere() -> None:
    assert OSUtils.is_browser_supported_on_current_os(BrowserType.UNDETECTED_CHROME) is True


def test_all_browser_types_covered_in_os_map() -> None:
    """Каждое значение BrowserType должно быть в карте поддержки ОС."""
    for browser in BrowserType:
        assert browser in OSUtils._BROWSER_OS_SUPPORT, (
            f"{browser.value} отсутствует в OSUtils._BROWSER_OS_SUPPORT"
        )


def test_safari_only_on_macos() -> None:
    assert OSUtils.is_browser_supported_on_current_os(
        BrowserType.SAFARI, platform="linux",
    ) is False
    assert OSUtils.is_browser_supported_on_current_os(
        BrowserType.SAFARI, platform="win32",
    ) is False
    assert OSUtils.is_browser_supported_on_current_os(
        BrowserType.SAFARI, platform="darwin",
    ) is True


def test_edge_supported_on_all_platforms() -> None:
    # Microsoft теперь публикует Edge для Linux наравне с macOS/Windows.
    for platform in ("linux", "darwin", "win32"):
        assert OSUtils.is_browser_supported_on_current_os(
            BrowserType.EDGE, platform=platform,
        ) is True


def test_browser_service_raises_on_unsupported_os() -> None:
    """BrowserService падает на не-macOS, если запросили Safari.

    Используем естественную реальность раннера: на Linux/Windows Safari
    действительно не поддерживается, не нужно подменять `sys.platform`.
    На macOS тест неприменим (Safari там валиден) - skip.
    """
    if sys.platform == "darwin":
        pytest.skip("Safari поддерживается на macOS; нечего проверять")

    cfg = SeleniumConfig(browser=BrowserType.SAFARI)
    with pytest.raises(BrowserNotSupportedError) as exc_info:
        BrowserService(cfg)

    assert "safari" in str(exc_info.value).lower()
    assert sys.platform in str(exc_info.value)
