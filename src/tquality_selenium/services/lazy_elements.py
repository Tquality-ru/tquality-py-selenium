"""`LazyElements` для selenium - тонкий wrapper над core-`LazyElements`,
прокидывающий browser-resolver из `SeleniumServices`.

Сам алгоритм snapshot-кэширования и live-резолва в `tquality_core`;
здесь только инициализация browser-сервиса через активный composition root.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from tquality_core import LazyElements as _CoreLazyElements

from tquality_selenium.elements.by import By
from tquality_selenium.elements.element import Element

if TYPE_CHECKING:
    from tquality_selenium.browser import BrowserService


class LazyElements[E: Element](_CoreLazyElements[E]):
    def __init__(
        self,
        element_cls: type[E],
        by: By,
        name_prefix: str = "",
    ) -> None:
        super().__init__(
            element_cls,
            by,
            name_prefix,
            driver_resolver=self._resolve_browser,
        )

    @staticmethod
    def _resolve_browser() -> BrowserService:
        from tquality_selenium.browser import BrowserService
        from tquality_selenium.container import SeleniumServices
        return SeleniumServices.get_service(BrowserService)


__all__ = ["LazyElements"]
