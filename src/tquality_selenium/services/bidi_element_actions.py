"""BiDi-действия element-scope (`BiDiElementActions`).

Привязаны к элементу через лениво-вычисляемый резолвер `find` и сам
`BaseElement` (для `click()`); driver приходит через `driver_getter`-композицию
от `BrowserService` (см. `Element.bidi_actions`), а не из DI-контейнера.
"""
from __future__ import annotations

import base64
from pathlib import Path
from typing import TYPE_CHECKING, Callable

from selenium.webdriver.common.bidi.browsing_context import (
    BoxClipRectangle,
    BrowsingContext,
)
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

from tquality_selenium.services.bidi_browser_actions import BiDiBrowserActions

if TYPE_CHECKING:
    from tquality_core import BaseElement, Logger


class BiDiElementActions:
    """BiDi-действия, привязанные к элементу через лениво-вычисляемый резолвер."""

    def __init__(
        self,
        find: Callable[[], WebElement],
        driver_getter: Callable[[], WebDriver],
        element: BaseElement,
    ) -> None:
        self._find = find
        self._driver_getter = driver_getter
        self._element = element

    @property
    def _driver(self) -> WebDriver:
        return self._driver_getter()

    @property
    def _log(self) -> Logger:
        from tquality_core import step

        return step.resolve()

    def capture_screenshot(self) -> bytes:
        """Screenshot, обрезанный по bounding-box этого элемента."""
        self._log.info("BiDi: capture element screenshot")
        rect = self._find().rect
        clip = BoxClipRectangle(
            x=rect["x"], y=rect["y"],
            width=rect["width"], height=rect["height"],
        )
        b64 = self.browsing_context.capture_screenshot(
            self._driver.current_window_handle, clip=clip,
        )
        return base64.b64decode(b64)

    def submit_to_file_dialogue(self, path: str | Path, *, timeout: float = 5.0) -> None:
        """Загрузить `path` через BiDi file-dialog, кликнув по этому элементу.

        Element-scope обёртка над `browser.bidi.intercept_file_dialog`: вешает
        перехватчик file-dialog, кликает по элементу (открывает диалог) и снимает
        перехватчик.

        ```python
        avatar_input.bidi_actions.submit_to_file_dialogue(avatar_path)
        ```
        """
        with BiDiBrowserActions(self._driver_getter).intercept_file_dialog([path], timeout=timeout):
            self._element.click()

    @property
    def browsing_context(self) -> BrowsingContext:
        """Shortcut к BiDi `browsing_context`-модулю драйвера."""
        return self._driver.browsing_context


__all__ = ["BiDiElementActions"]
