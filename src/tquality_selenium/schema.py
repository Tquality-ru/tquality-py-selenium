"""Генерация JSON-схемы для SeleniumConfig.

URL `SELENIUM_SCHEMA_URL` и сама запись схемы делегированы в
`tquality_core.schema`. Здесь только конфигурация: какой пакет,
какой репозиторий, какой класс конфига.
"""
from __future__ import annotations

import importlib.metadata  # noqa: F401  # re-exported for tests that monkeypatch
from pathlib import Path
from typing import Any

from tquality_core.schema import (
    build_schema_url,
    generate_schema as _core_generate_schema,
    resolve_ref,
    write_schema_file as _core_write_schema_file,
)

from tquality_selenium.config import SeleniumConfig

_PACKAGE_NAME = "tquality-py-selenium"
_REPO_OWNER = "Tquality-ru"
_REPO_NAME = "tquality-py-selenium"


def _resolve_ref() -> str:
    """Backwards-compat shim для тестов; делегирует в `core.resolve_ref`."""
    return resolve_ref(_PACKAGE_NAME)


SELENIUM_SCHEMA_URL = build_schema_url(
    package_name=_PACKAGE_NAME,
    repo_owner=_REPO_OWNER,
    repo_name=_REPO_NAME,
)


def generate_schema() -> dict[str, Any]:
    """Вернуть JSON-схему SeleniumConfig (с `$id = SELENIUM_SCHEMA_URL`)."""
    return _core_generate_schema(SeleniumConfig, schema_url=SELENIUM_SCHEMA_URL)


def write_schema_file(path: Path) -> None:
    """Записать JSON-схему SeleniumConfig в файл."""
    _core_write_schema_file(path, SeleniumConfig, schema_url=SELENIUM_SCHEMA_URL)
