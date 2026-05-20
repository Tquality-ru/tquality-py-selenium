"""Утилиты для работы с локаторами.

`LocatorUtils` собирает stateless-хелперы вокруг локаторов селениума.
Сами XPath-строковые трансформации (`normalize`, `literal`) живут в
`tquality_core.utils.xpath_utils.XPathUtils` - сюда они переэкспортированы
под историческими именами `normalize_xpath`/`xpath_literal`. Здесь же
остаётся `join_xpath`, который зависит от селениум-специфичного `By`.
"""
from __future__ import annotations

from tquality_core.utils.xpath_utils import XPathUtils

from tquality_selenium.elements.by import By


class LocatorUtils:
    """Stateless-хелперы для манипуляции локаторов."""

    @staticmethod
    def normalize_xpath(value: str) -> str:
        """Делает xpath безопасным для конкатенации с родительским локатором.

        Тонкая обёртка над `XPathUtils.normalize` для обратной совместимости.
        """
        return XPathUtils.normalize(value)

    @staticmethod
    def xpath_literal(value: str) -> str:
        """Квотит `value` как XPath-литерал.

        Тонкая обёртка над `XPathUtils.literal` для обратной совместимости.
        """
        return XPathUtils.literal(value)

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
