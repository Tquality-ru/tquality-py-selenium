"""JS-действия: driver-scope (`JsActions`) и element-scope (`ElementJsActions`).

`JsActions` работает на уровне driver'а (execute, pseudo-element style).
`ElementJsActions` принимает callable-резолвер элемента и выполняет действия
на нем - элемент находится заново при каждом вызове, что снимает проблему
stale reference.
"""
from __future__ import annotations

import enum
from contextlib import contextmanager
from typing import Any, Callable, Iterator

from selenium.webdriver.remote.webelement import WebElement


class PseudoElement(enum.Enum):
    BEFORE = "::before"
    AFTER = "::after"


class JsActions:
    """Низкоуровневые JS-операции на уровне driver'а."""

    @property
    def _driver(self) -> Any:
        from tquality_selenium.browser import BrowserService
        from tquality_selenium.container import SeleniumServices
        return SeleniumServices.get_service(BrowserService).driver

    @property
    def _log(self) -> Any:
        from tquality_core import Logger
        from tquality_selenium.container import SeleniumServices
        return SeleniumServices.get_service(Logger)

    def execute(self, script: str, *args: Any) -> Any:
        self._log.info("Execute JS: %s", script[:120])
        return self._driver.execute_script(script, *args)

    def get_pseudo_element_style(
        self, selector: str, pseudo: PseudoElement, property_name: str,
    ) -> str | None:
        """Вернуть вычисленный стиль псевдо-элемента или None."""
        # language=js
        script = """
        var el = document.querySelector(arguments[0]);
        if (!el) return null;
        return window.getComputedStyle(el, arguments[1]).getPropertyValue(arguments[2]);
        """
        result: Any = self._driver.execute_script(
            script, selector, pseudo.value, property_name,
        )
        return result if result is None else str(result)


class ElementJsActions:
    """JS-действия, привязанные к элементу через лениво-вычисляемый резолвер.

    Принимает callable, возвращающий `WebElement` при каждом вызове -
    элемент находится заново, что снимает stale reference.
    """

    def __init__(self, find: Callable[[], WebElement]) -> None:
        self._find = find

    @property
    def _driver(self) -> Any:
        from tquality_selenium.browser import BrowserService
        from tquality_selenium.container import SeleniumServices
        return SeleniumServices.get_service(BrowserService).driver

    @property
    def _log(self) -> Any:
        from tquality_core import Logger
        from tquality_selenium.container import SeleniumServices
        return SeleniumServices.get_service(Logger)

    @property
    def _config(self) -> Any:
        from tquality_selenium.config import SeleniumConfig
        from tquality_selenium.container import SeleniumServices
        return SeleniumServices.get_service(SeleniumConfig)

    def click(self) -> None:
        self._log.info("JS click")
        element = self._find()
        with self.maybe_highlight():
            # language=js
            self._driver.execute_script("arguments[0].click();", element)

    def scroll_into_view(self) -> None:
        self._log.info("JS scroll into view")
        element = self._find()
        with self.maybe_highlight():
            # language=js
            script = (
                "arguments[0].scrollIntoView("
                "{behavior: 'instant', block: 'center'});"
            )
            self._driver.execute_script(script, element)

    def set_input_value(self, value: str) -> None:
        self._log.info("JS set input value: %s", value)
        element = self._find()
        with self.maybe_highlight():
            # language=js
            script = """
            var el = arguments[0];
            el.focus();
            el.value = arguments[1];
            el.dispatchEvent(new Event('input', {bubbles: true}));
            el.dispatchEvent(new Event('change', {bubbles: true}));
            """
            self._driver.execute_script(script, element, value)

    def blur(self) -> None:
        self._log.info("JS blur")
        element = self._find()
        with self.maybe_highlight():
            # language=js
            script = """
            arguments[0].dispatchEvent(new Event('blur', {bubbles: true}));
            document.activeElement.blur();
            """
            self._driver.execute_script(script, element)

    @contextmanager
    def highlight(self) -> Iterator[None]:
        """Обвести элемент красной рамкой на время контекста."""
        element = self._find()
        # language=js
        add_script = """
        var el = arguments[0];
        el.__oldOutline = el.style.outline;
        el.__oldOutlineOffset = el.style.outlineOffset;
        el.style.outline = '3px solid red';
        el.style.outlineOffset = '-1px';
        """
        # language=js
        remove_script = """
        var el = arguments[0];
        el.style.outline = el.__oldOutline || '';
        el.style.outlineOffset = el.__oldOutlineOffset || '';
        delete el.__oldOutline;
        delete el.__oldOutlineOffset;
        """
        self._driver.execute_script(add_script, element)
        try:
            yield
        finally:
            try:
                self._driver.execute_script(remove_script, element)
            except Exception as exc:  # noqa: BLE001
                # После действия элемент мог исчезнуть (навигация,
                # перерендер). Не фейлим тест, но не молчим - пусть
                # будет видно в логах.
                self._log.warning(
                    "Не удалось снять highlight (элемент исчез?): %s", exc,
                )

    @contextmanager
    def maybe_highlight(self) -> Iterator[None]:
        """Подсветить элемент, если в конфиге `highlight_elements=True`."""
        if self._config.highlight_elements:
            with self.highlight():
                yield
        else:
            yield
