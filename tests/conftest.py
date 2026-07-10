"""Общие фикстуры для тестов `tquality_selenium`."""

from __future__ import annotations

import urllib.parse
from collections.abc import Iterator
from pathlib import Path
from typing import Any, Callable
from unittest.mock import MagicMock

import pytest
from tquality_core import PathUtils

from tquality_selenium.services.collection_factory import CollectionFactory


@pytest.fixture
def page_url() -> str:
    """data: URL объединённой тест-страницы `tests/resources/page.html`.

    Одна страница с элементами с уникальными id, под все тесты, которым нужны
    конкретные условия на странице (file-dialog `#file-upload-trigger` /
    `#file-upload-result`, computed-CSS `#styled-box`, title-smoke `healthcheck`).
    Открывается через `service.open(page_url)` - data: URL работает и на remote-ноде.
    """
    root = PathUtils.find_project_root(Path(__file__))
    assert root is not None, "project root (pyproject.toml) не найден"
    html = (root / "tests" / "resources" / "page.html").read_text(encoding="utf-8")
    return "data:text/html," + urllib.parse.quote(html)


@pytest.fixture
def search_dir() -> Iterator[Callable[[Path], None]]:
    """Параллельно-безопасно нацеливает разрешение конфигов на директорию
    (через `ContextVar`), в отличие от глобального `monkeypatch`/`chdir`."""
    resets: list[Callable[[], None]] = []

    def _set(path: Path) -> None:
        resets.append(PathUtils.use_config_search_dir(path))

    yield _set
    for reset in reversed(resets):
        reset()


@pytest.fixture
def make_collection_factory() -> Callable[[list[dict[str, Any]]], CollectionFactory]:
    """Собрать `CollectionFactory` с подменёнными driver/logger.

    Возвращает фабрику-конструктор: `factory = make_collection_factory([{...}])`.
    `execute_script` отдаст ровно переданные `raw_items`; логгер - no-op.
    Резолверы внедряются напрямую (фабрика их принимает в конструкторе) -
    подменять через subclass больше не нужно.
    """

    def _build(raw_items: list[dict[str, Any]]) -> CollectionFactory:
        driver = MagicMock()
        driver.execute_script.return_value = raw_items
        log = MagicMock()
        return CollectionFactory(driver_resolver=lambda: driver, logger_resolver=lambda: log)

    return _build
