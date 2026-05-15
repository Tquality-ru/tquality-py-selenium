"""Утилиты для работы с локаторами.

`LocatorUtils` собирает stateless-хелперы для нормализации xpath-строк и
композиции нескольких `By` в один локатор. Конвертация одного `By` -
на самом `By.to_xpath()`, который, в свою очередь, использует
`LocatorUtils.normalize_xpath` для XPATH-стратегии.
"""
from __future__ import annotations

from tquality_selenium.elements.by import By


class LocatorUtils:
    """Stateless-хелперы для манипуляции локаторов."""

    @staticmethod
    def normalize_xpath(value: str) -> str:
        """Делает xpath безопасным для конкатенации с родительским локатором.

        `.` → `""` (self - join-нейтральный, в `parent + .` даёт самого
        parent'а; selenium-у такой результат standalone не скормишь, но в
        практике `.` в качестве отдельного локатора и не нужен), `./foo` →
        `/foo`, `.//foo` → `//foo`, `foo` → `/foo`. Уже абсолютные
        (`/foo`, `//foo`) - без изменений.
        """
        if value == ".":
            return ""
        if value.startswith(".//"):
            return value[1:]
        if value.startswith("./"):
            return value[1:]
        if not value.startswith("/"):
            return "/" + value
        return value

    @staticmethod
    def xpath_literal(value: str) -> str:
        """Квотит `value` как XPath-литерал, корректно обрабатывая
        встроенные кавычки.

        XPath не имеет escape для кавычек, поэтому:
        - нет `'` → оборачиваем в `'…'`;
        - иначе нет `"` → оборачиваем в `"…"`;
        - иначе бьём по `'` и склеиваем через `concat('a', "'", 'b', ...)`.
        """
        if "'" not in value:
            return f"'{value}'"
        if '"' not in value:
            return f'"{value}"'
        parts = (f"'{p}'" for p in value.split("'"))
        return "concat(" + ", \"'\", ".join(parts) + ")"

    @staticmethod
    def join_xpath(*bys: By) -> By:
        """Объединяет несколько `By` в один XPATH-локатор: каждый через
        `to_xpath()` (XPATH-стратегия уже нормализована), результаты
        склеиваются. Используется для дочерних локаторов:

        ```python
        LocatorUtils.join_xpath(parent.by, child.by)
        ```
        """
        return By.xpath("".join(b.to_xpath() for b in bys))
