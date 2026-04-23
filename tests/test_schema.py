"""Тесты генерации JSON-схемы SeleniumConfig."""
from __future__ import annotations

import json
from pathlib import Path

from tquality_selenium.schema import SELENIUM_SCHEMA_URL, generate_schema

_CORE_FIELDS = {"base_url", "default_timeout", "log_dir", "highlight_elements"}
_SELENIUM_FIELDS = {
    "browser", "headless", "page_load_timeout", "window_width", "window_height",
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
