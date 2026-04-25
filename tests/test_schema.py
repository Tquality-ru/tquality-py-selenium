"""Тесты генерации JSON-схемы SeleniumConfig."""
from __future__ import annotations

import json
from pathlib import Path

from tquality_selenium.schema import SELENIUM_SCHEMA_URL, generate_schema

_CORE_FIELDS = {"base_url", "default_timeout", "log_dir", "highlight_elements"}
_SELENIUM_FIELDS = {
    "browser",
    "chrome", "firefox", "edge", "safari", "undetected_chrome",
    "screencast",
    "attach_page_source_on_failure",
}


def test_schema_includes_core_and_selenium_fields() -> None:
    """Схема SeleniumConfig должна содержать все поля ядра и все Selenium-специфичные."""
    schema = generate_schema()

    assert schema["$schema"] == "http://json-schema.org/draft-07/schema#"
    assert schema["$id"] == SELENIUM_SCHEMA_URL
    assert set(schema["properties"].keys()) == _CORE_FIELDS | _SELENIUM_FIELDS


def test_schema_browser_enum_lists_all_supported_values() -> None:
    """Enum browser должен перечислять все поддерживаемые браузеры."""
    schema = generate_schema()
    browser_enum = schema["$defs"]["BrowserType"]["enum"]
    assert set(browser_enum) == {
        "chrome", "firefox", "edge", "safari", "undetected-chrome",
    }


def test_schema_url_resolves_to_master_on_dev_install() -> None:
    """Dev-версия (с '+g...' или '.dev') резолвится в @master."""
    import tquality_selenium.schema as schema_mod
    from tquality_selenium.schema import _resolve_ref

    def _stub(_name: str) -> str:
        return "0.1.3+gabc123"

    original = schema_mod.importlib.metadata.version  # type: ignore[attr-defined]
    schema_mod.importlib.metadata.version = _stub  # type: ignore[attr-defined]
    try:
        assert _resolve_ref() == "master"
    finally:
        schema_mod.importlib.metadata.version = original  # type: ignore[attr-defined]


def test_schema_url_resolves_to_version_on_release_install() -> None:
    """Чистая релизная версия резолвится в @vX.Y.Z."""
    import tquality_selenium.schema as schema_mod
    from tquality_selenium.schema import _resolve_ref

    def _stub(_name: str) -> str:
        return "0.1.3"

    original = schema_mod.importlib.metadata.version  # type: ignore[attr-defined]
    schema_mod.importlib.metadata.version = _stub  # type: ignore[attr-defined]
    try:
        assert _resolve_ref() == "v0.1.3"
    finally:
        schema_mod.importlib.metadata.version = original  # type: ignore[attr-defined]


def test_committed_schema_matches_selenium_config() -> None:
    """Коммиченная схема должна совпадать со схемой, генерируемой из SeleniumConfig.

    Если тест упал - запустите `tquality-selenium-config schema` и закоммитьте
    обновленный schema/config.schema.json.
    """
    repo_root = Path(__file__).resolve().parent.parent
    committed = json.loads(
        (repo_root / "schema" / "config.schema.json").read_text(encoding="utf-8")
    )
    current = generate_schema()

    assert committed == current, (
        "Коммиченная схема устарела. Запустите `tquality-selenium-config schema`."
    )
