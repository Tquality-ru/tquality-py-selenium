"""Тесты для pytest-плагина page_source-on-failure."""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from tquality_selenium import page_source_plugin
from tquality_selenium.page_source_plugin import (
    _capture_page_source,
    pytest_runtest_makereport,
)


class _FakeReport:
    def __init__(self, when: str, failed: bool) -> None:
        self.when = when
        self.failed = failed


class _FakeOutcome:
    def __init__(self, report: _FakeReport) -> None:
        self._report = report

    def get_result(self) -> _FakeReport:
        return self._report


def _drive_hook(when: str, failed: bool) -> None:
    """Прокачать generator-хук в его call/yield-фазах."""
    gen = pytest_runtest_makereport(
        item=MagicMock(spec=pytest.Item),
        call=MagicMock(spec=pytest.CallInfo),
    )
    next(gen)
    outcome = _FakeOutcome(_FakeReport(when=when, failed=failed))
    try:
        gen.send(outcome)
    except StopIteration:
        pass


def test_capture_page_source_returns_html_on_success() -> None:
    driver = MagicMock()
    driver.page_source = "<html><body>ok</body></html>"
    body, attachment_type = _capture_page_source(driver)
    assert body == "<html><body>ok</body></html>"
    assert "HTML" in str(attachment_type).upper()


def test_capture_page_source_returns_diagnostic_on_failure() -> None:
    driver = MagicMock()
    type(driver).page_source = property(
        lambda _self: (_ for _ in ()).throw(RuntimeError("session crashed"))
    )
    body, attachment_type = _capture_page_source(driver)
    assert "page_source capture failed" in body
    assert "RuntimeError" in body
    type_str = str(attachment_type).upper()
    assert "TEXT" in type_str or "PLAIN" in type_str


def test_hook_attaches_page_source_on_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """call-фаза, тест упал, конфиг ON, браузер запущен -> attach вызван."""
    driver = MagicMock()
    driver.page_source = "<html>failed-state</html>"

    config = MagicMock()
    config.attach_page_source_on_failure = True

    attach_calls: list[tuple[str, str]] = []

    def fake_attach(body: Any, name: str, attachment_type: Any) -> None:
        attach_calls.append((str(name), str(body)))

    monkeypatch.setattr(page_source_plugin, "_try_get_config", lambda: config)
    monkeypatch.setattr(page_source_plugin, "_try_get_driver", lambda: driver)
    monkeypatch.setattr(
        "tquality_selenium.page_source_plugin.allure.attach", fake_attach,
    )

    _drive_hook(when="call", failed=True)

    assert len(attach_calls) == 1
    name, body = attach_calls[0]
    assert name == "Page source"
    assert "failed-state" in body


def test_hook_skips_when_feature_flag_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = MagicMock()
    config.attach_page_source_on_failure = False

    attach_calls: list[Any] = []
    monkeypatch.setattr(page_source_plugin, "_try_get_config", lambda: config)
    monkeypatch.setattr(
        page_source_plugin, "_try_get_driver", lambda: MagicMock(),
    )
    monkeypatch.setattr(
        "tquality_selenium.page_source_plugin.allure.attach",
        lambda *a, **kw: attach_calls.append((a, kw)),
    )

    _drive_hook(when="call", failed=True)

    assert attach_calls == []


def test_hook_skips_when_browser_not_started(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Тест мог упасть до старта браузера (api/db-only) - вложение пропускаем."""
    config = MagicMock()
    config.attach_page_source_on_failure = True

    attach_calls: list[Any] = []
    monkeypatch.setattr(page_source_plugin, "_try_get_config", lambda: config)
    monkeypatch.setattr(page_source_plugin, "_try_get_driver", lambda: None)
    monkeypatch.setattr(
        "tquality_selenium.page_source_plugin.allure.attach",
        lambda *a, **kw: attach_calls.append((a, kw)),
    )

    _drive_hook(when="call", failed=True)

    assert attach_calls == []


def test_hook_skips_when_test_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    config = MagicMock()
    config.attach_page_source_on_failure = True

    attach_calls: list[Any] = []
    monkeypatch.setattr(page_source_plugin, "_try_get_config", lambda: config)
    monkeypatch.setattr(
        page_source_plugin, "_try_get_driver", lambda: MagicMock(),
    )
    monkeypatch.setattr(
        "tquality_selenium.page_source_plugin.allure.attach",
        lambda *a, **kw: attach_calls.append((a, kw)),
    )

    _drive_hook(when="call", failed=False)

    assert attach_calls == []


def test_hook_attaches_in_any_phase_when_browser_started(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Один runtime-guard - запущен ли браузер. Фаза не важна:
    setup-фейл с уже поднятым драйвером тоже даёт полезный page_source."""
    driver = MagicMock()
    driver.page_source = "<html>any-phase</html>"

    config = MagicMock()
    config.attach_page_source_on_failure = True

    attach_calls: list[Any] = []
    monkeypatch.setattr(page_source_plugin, "_try_get_config", lambda: config)
    monkeypatch.setattr(page_source_plugin, "_try_get_driver", lambda: driver)
    monkeypatch.setattr(
        "tquality_selenium.page_source_plugin.allure.attach",
        lambda *a, **kw: attach_calls.append((a, kw)),
    )

    _drive_hook(when="setup", failed=True)
    _drive_hook(when="call", failed=True)
    _drive_hook(when="teardown", failed=True)

    assert len(attach_calls) == 3


def test_hook_attaches_diagnostic_when_page_source_throws(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """driver.page_source может бросить, если сессия уже мертва."""
    driver = MagicMock()
    type(driver).page_source = property(
        lambda _self: (_ for _ in ()).throw(RuntimeError("renderer gone"))
    )

    config = MagicMock()
    config.attach_page_source_on_failure = True

    attach_calls: list[tuple[str, str]] = []

    def fake_attach(body: Any, name: str, attachment_type: Any) -> None:
        attach_calls.append((str(name), str(body)))

    monkeypatch.setattr(page_source_plugin, "_try_get_config", lambda: config)
    monkeypatch.setattr(page_source_plugin, "_try_get_driver", lambda: driver)
    monkeypatch.setattr(
        "tquality_selenium.page_source_plugin.allure.attach", fake_attach,
    )

    _drive_hook(when="call", failed=True)

    assert len(attach_calls) == 1
    name, body = attach_calls[0]
    assert name == "Page source"
    assert "page_source capture failed" in body
    assert "RuntimeError" in body
