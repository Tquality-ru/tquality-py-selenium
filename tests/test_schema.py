"""Тесты генерации JSON-схемы SeleniumConfig."""
from __future__ import annotations

import json
from pathlib import Path

from tquality_selenium.schema import generate_schema


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
