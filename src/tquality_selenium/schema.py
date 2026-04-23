"""Генерация JSON-схемы для SeleniumConfig.

Используется CLI-командой `tquality-selenium-config schema` для записи
`schema/config.schema.json` в корень репозитория. Отдельная от ядра
потому что `$id` публикуемой схемы указывает на selenium-репозиторий,
а не на ядро.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tquality_selenium.config import SeleniumConfig

SELENIUM_SCHEMA_URL = (
    "https://cdn.jsdelivr.net/gh/Tquality-ru/tquality-py-selenium@master"
    "/schema/config.schema.json"
)


def generate_schema() -> dict[str, Any]:
    """Вернуть JSON-схему SeleniumConfig.

    Включает поля ядра (base_url, default_timeout, log_dir,
    highlight_elements) и Selenium-специфичные (browser, headless,
    page_load_timeout, window_width, window_height).
    """
    schema: dict[str, Any] = SeleniumConfig.model_json_schema()
    schema["$schema"] = "http://json-schema.org/draft-07/schema#"
    schema["$id"] = SELENIUM_SCHEMA_URL
    return schema


def write_schema_file(path: Path) -> None:
    """Записать JSON-схему SeleniumConfig в файл."""
    schema = generate_schema()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(schema, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
