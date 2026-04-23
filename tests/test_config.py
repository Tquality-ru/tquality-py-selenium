"""Тесты для SeleniumConfig."""
from __future__ import annotations

from pathlib import Path

import pytest

from tquality_selenium import BrowserType, SeleniumConfig


def test_defaults(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    cfg = SeleniumConfig()
    assert cfg.browser is BrowserType.CHROME
    assert cfg.headless is True
    assert cfg.page_load_timeout == 30.0
    assert cfg.window_width == 1920
    assert cfg.window_height == 1080
    # Поля из ядра доступны
    assert cfg.base_url == "http://localhost"
    assert cfg.default_timeout == 10.0


def test_constructor_overrides(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    cfg = SeleniumConfig(
        browser=BrowserType.UNDETECTED_CHROME,
        headless=False,
        window_width=1280,
    )
    assert cfg.browser is BrowserType.UNDETECTED_CHROME
    assert cfg.headless is False
    assert cfg.window_width == 1280


def test_browser_from_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TEST_BROWSER", "firefox")
    cfg = SeleniumConfig()
    assert cfg.browser is BrowserType.FIREFOX
