"""CLI-команды tquality-py-selenium.

Точка входа: `tquality-selenium-config`. Доступные подкоманды:

- `init` - сгенерировать config.json5 в корне проекта со значениями по умолчанию
  SeleniumConfig (включая поля, унаследованные от BaseConfig)
- `schema` - сгенерировать/обновить schema/config.schema.json (для мейнтейнеров)

Реализация делегирована в `tquality_core.cli.build_cli` - все argparse-плита
живёт в ядре, здесь только привязка к `SeleniumConfig` и `SELENIUM_SCHEMA_URL`.
"""
from __future__ import annotations

import sys

from tquality_core.cli import build_cli

from tquality_selenium.config import SeleniumConfig
from tquality_selenium.schema import SELENIUM_SCHEMA_URL

main = build_cli(
    prog="tquality-selenium-config",
    description="Утилиты работы с конфигурацией tquality-py-selenium",
    config_cls=SeleniumConfig,
    schema_url=SELENIUM_SCHEMA_URL,
)


if __name__ == "__main__":
    sys.exit(main(None))
