"""CLI-команды tquality-py-selenium.

Точка входа: `tquality-selenium-config`. Доступные подкоманды:

- `init` - сгенерировать config.json5 в корне проекта со значениями по умолчанию
  SeleniumConfig (включая поля, унаследованные от BaseConfig)
- `schema` - сгенерировать/обновить schema/config.schema.json (для мейнтейнеров)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from tquality_core.config import CONFIG_FILENAME

from tquality_selenium.config import SeleniumConfig
from tquality_selenium.schema import SELENIUM_SCHEMA_URL, write_schema_file


def _find_project_root() -> Path:
    """Найти корень проекта: поднимаемся до pyproject.toml."""
    current = Path.cwd().resolve()
    for parent in (current, *current.parents):
        if (parent / "pyproject.toml").exists():
            return parent
    return current


def _default_config_dict() -> dict[str, Any]:
    """Значения по умолчанию SeleniumConfig со ссылкой на схему."""
    cfg = SeleniumConfig()
    data: dict[str, Any] = {"$schema": SELENIUM_SCHEMA_URL}
    data.update(cfg.model_dump(mode="json"))
    return data


def cmd_init(args: argparse.Namespace) -> int:
    """Сгенерировать config.json5 со значениями по умолчанию."""
    target_dir = Path(args.path).resolve() if args.path else _find_project_root()
    target_file = target_dir / CONFIG_FILENAME

    if target_file.exists() and not args.force:
        print(
            f"Файл уже существует: {target_file}. "
            f"Используйте --force для перезаписи.",
            file=sys.stderr,
        )
        return 1

    target_file.write_text(
        json.dumps(_default_config_dict(), indent=4, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Создан {target_file}")
    return 0


def cmd_schema(args: argparse.Namespace) -> int:
    """Сгенерировать schema/config.schema.json."""
    target_dir = Path(args.path).resolve() if args.path else _find_project_root()
    target_file = target_dir / "schema" / "config.schema.json"

    write_schema_file(target_file)
    print(f"Схема записана в {target_file}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tquality-selenium-config",
        description="Утилиты работы с конфигурацией tquality-py-selenium",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_init = subparsers.add_parser(
        "init",
        help="Сгенерировать config.json5 со значениями по умолчанию",
    )
    p_init.add_argument(
        "--path",
        help="Каталог, в котором создать config.json5 (по умолчанию - корень проекта)",
    )
    p_init.add_argument(
        "--force",
        action="store_true",
        help="Перезаписать существующий config.json5",
    )
    p_init.set_defaults(func=cmd_init)

    p_schema = subparsers.add_parser(
        "schema",
        help="Сгенерировать schema/config.schema.json (для мейнтейнеров)",
    )
    p_schema.add_argument(
        "--path",
        help="Корень репозитория (по умолчанию - текущий проект)",
    )
    p_schema.set_defaults(func=cmd_schema)

    args = parser.parse_args(argv)
    result: int = args.func(args)
    return result


if __name__ == "__main__":
    sys.exit(main())
