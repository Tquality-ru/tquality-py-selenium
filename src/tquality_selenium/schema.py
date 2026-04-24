"""Генерация JSON-схемы для SeleniumConfig.

`SELENIUM_SCHEMA_URL` вычисляется по установленной версии пакета:

- Релизная версия (например, `0.1.3`) → `@v0.1.3` - пин на тег.
- Dev/editable сборка (версия содержит `+g...` или `.dev`) → `@master`.

`tquality-selenium-config init`, выполненный на релизной установке,
запекает в config.json5 ссылку на конкретный тег. В dev-окружении -
ссылка на master.
"""
from __future__ import annotations

import importlib.metadata
import json
from pathlib import Path
from typing import Any

from tquality_selenium.config import SeleniumConfig

_REPO_BASE = "https://cdn.jsdelivr.net/gh/Tquality-ru/tquality-py-selenium"
_SCHEMA_PATH = "schema/config.schema.json"
_PACKAGE_NAME = "tquality-py-selenium"


def _resolve_ref() -> str:
    """Вернуть git-ref для URL схемы.

    Чистый релиз ("0.1.3") → "v0.1.3". Dev ("0.1.3+g...", "0.0+g...",
    "0.1.3.dev1") → "master". Пакет не установлен → "master".
    """
    try:
        version = importlib.metadata.version(_PACKAGE_NAME)
    except importlib.metadata.PackageNotFoundError:
        return "master"
    if "+" in version or ".dev" in version:
        return "master"
    return f"v{version}"


SELENIUM_SCHEMA_URL = f"{_REPO_BASE}@{_resolve_ref()}/{_SCHEMA_PATH}"


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
