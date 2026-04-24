"""Тесты для SeleniumConfig."""
from __future__ import annotations

from pathlib import Path

import pytest

from tquality_selenium import BrowserType, SeleniumConfig
from tquality_selenium.config import BrowserConfig, ScreencastConfig


def test_defaults(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    cfg = SeleniumConfig()
    assert cfg.browser is BrowserType.CHROME
    # Поля из ядра
    assert cfg.base_url == "http://localhost"
    assert cfg.default_timeout == 10.0
    # Каждый per-browser блок присутствует с дефолтами
    for blk in (
        cfg.chrome, cfg.firefox, cfg.edge, cfg.safari, cfg.undetected_chrome,
    ):
        assert isinstance(blk, BrowserConfig)
        assert blk.headless is True
        assert blk.window_width == 1920
        assert blk.window_height == 1080
        assert blk.page_load_timeout == 30.0
    assert isinstance(cfg.screencast, ScreencastConfig)
    assert cfg.screencast.fps == 10


def test_active_browser_follows_selection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    cfg = SeleniumConfig(
        browser=BrowserType.UNDETECTED_CHROME,
        undetected_chrome=BrowserConfig(headless=False, window_width=1280),
    )
    assert cfg.browser is BrowserType.UNDETECTED_CHROME
    assert cfg.active_browser is cfg.undetected_chrome
    assert cfg.active_browser.headless is False
    assert cfg.active_browser.window_width == 1280


def test_all_browser_blocks_live_side_by_side(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Настройки всех браузеров должны сосуществовать - переключение
    выбора браузера не должно требовать переписывания остальных блоков."""
    monkeypatch.chdir(tmp_path)
    cfg = SeleniumConfig(
        browser=BrowserType.CHROME,
        chrome=BrowserConfig(headless=True),
        firefox=BrowserConfig(headless=False, window_width=1024),
        undetected_chrome=BrowserConfig(headless=False),
    )
    assert cfg.active_browser is cfg.chrome
    # Меняем только выбор браузера - остальные блоки сохраняются
    cfg2 = cfg.model_copy(update={"browser": BrowserType.FIREFOX})
    assert cfg2.active_browser is cfg2.firefox
    assert cfg2.firefox.headless is False
    assert cfg2.firefox.window_width == 1024


def test_browser_from_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TEST_BROWSER", "firefox")
    cfg = SeleniumConfig()
    assert cfg.browser is BrowserType.FIREFOX
