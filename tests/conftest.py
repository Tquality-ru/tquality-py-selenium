"""Общие фикстуры для тестов `tquality_selenium`."""
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any, Callable
from unittest.mock import MagicMock

import pytest
from tquality_core import PathUtils

from tquality_selenium.services.collection_factory import CollectionFactory


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
    """Собрать `CollectionFactory` с подменёнными `_driver` и `_log`.

    Возвращает фабрику-конструктор: `factory = make_collection_factory([{...}])`.
    `execute_script` отдаст ровно переданные `raw_items`; логгер - no-op.
    """
    def _build(raw_items: list[dict[str, Any]]) -> CollectionFactory:
        driver = MagicMock()
        driver.execute_script.return_value = raw_items
        log = MagicMock()

        class _StubbedFactory(CollectionFactory):
            @property
            def _driver(self) -> Any:
                return driver

            @property
            def _log(self) -> Any:
                return log

        return _StubbedFactory()

    return _build
