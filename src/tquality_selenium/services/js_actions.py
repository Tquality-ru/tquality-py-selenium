"""JS-действия: driver-scope (`JsActions`) и element-scope (`ElementJsActions`).

`JsActions` работает на уровне driver'а; `ElementJsActions` принимает
callable-резолвер элемента и выполняет действия на нем - элемент
находится заново при каждом вызове, что снимает stale reference.

Оба класса получают driver через `driver_getter`-композицию от
`BrowserService` (см. `BrowserService.js_actions` / `Element.js_actions`)
вместо прямой подвязки к DI-контейнеру.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Iterator

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

from tquality_selenium.services.pseudo_element import PseudoElement
from tquality_selenium.services.style_property import StyleProperty

if TYPE_CHECKING:
    from tquality_core import Logger

    from tquality_selenium.config import SeleniumConfig

__all__ = [
    "ElementJsActions",
    "JsActions",
    "PseudoElement",
]


class JsActions:
    """Низкоуровневые JS-операции на уровне driver'а.

    Driver приходит через `driver_getter` (композиция от `BrowserService`).
    Logger/config резолвятся через DI - они per-test и не зависят от
    конкретного браузера.
    """

    def __init__(self, driver_getter: Callable[[], WebDriver]) -> None:
        self._driver_getter = driver_getter

    @property
    def _driver(self) -> WebDriver:
        return self._driver_getter()

    @property
    def _log(self) -> Logger:
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
    """JS-действия, привязанные к элементу через лениво-вычисляемый резолвер."""

    def __init__(
        self,
        find: Callable[[], WebElement],
        driver_getter: Callable[[], WebDriver],
    ) -> None:
        self._find = find
        self._driver_getter = driver_getter

    @property
    def _driver(self) -> WebDriver:
        return self._driver_getter()

    @property
    def _log(self) -> Logger:
        from tquality_core import Logger

        from tquality_selenium.container import SeleniumServices
        return SeleniumServices.get_service(Logger)

    @property
    def _config(self) -> SeleniumConfig:
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

    def get_computed_style(
        self, style_property: str | StyleProperty,
    ) -> str:
        """Вернуть computed-style значение указанного CSS-свойства.

        Эквивалент `window.getComputedStyle(el).getPropertyValue(name)`.
        Для несуществующего свойства браузер возвращает пустую строку.
        """
        name = str(style_property)
        self._log.info("JS get computed style: %s", name)
        element = self._find()
        # language=js
        script = (
            "return window.getComputedStyle(arguments[0])"
            ".getPropertyValue(arguments[1]);"
        )
        result: Any = self._driver.execute_script(script, element, name)
        return str(result) if result is not None else ""

    def get_computed_styles(self) -> dict[str, str]:
        """Вернуть все computed-style свойства элемента как `dict`.

        Один JS-запрос вместо N - выгоднее `get_computed_style` в цикле,
        когда нужно проверить много свойств одновременно (например, для
        snapshot-сравнений).
        """
        self._log.info("JS get computed styles (all)")
        element = self._find()
        # language=js
        script = """
        var s = window.getComputedStyle(arguments[0]);
        var out = {};
        for (var i = 0; i < s.length; i++) {
            var name = s[i];
            out[name] = s.getPropertyValue(name);
        }
        return out;
        """
        result: Any = self._driver.execute_script(script, element)
        return {str(k): str(v) for k, v in result.items()}

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

    # outline ставится через !important: сайты нередко задают собственный
    # `outline`/`outline-color` (в т.ч. `!important`) на inputs и ссылках, и
    # без приоритета наш red переопределяется и рамка рендерится невидимой.
    # language=js
    _APPLY_HIGHLIGHT_JS: ClassVar[str] = """
    var el = arguments[0];
    el.setAttribute('data-tq-highlight', '1');
    el.__tqOutline = el.style.getPropertyValue('outline');
    el.__tqOutlinePrio = el.style.getPropertyPriority('outline');
    el.__tqOffset = el.style.getPropertyValue('outline-offset');
    el.__tqOffsetPrio = el.style.getPropertyPriority('outline-offset');
    el.style.setProperty('outline', '3px solid red', 'important');
    el.style.setProperty('outline-offset', '-1px', 'important');
    """
    # Снятие идёт document-wide по маркеру - переживает навигацию/перерендер:
    # устаревший элемент просто не находится, а не роняет ошибку.
    # language=js
    _CLEAR_HIGHLIGHT_JS: ClassVar[str] = """
    var marked = document.querySelectorAll('[data-tq-highlight]');
    for (var i = 0; i < marked.length; i++) {
        var el = marked[i];
        el.style.removeProperty('outline');
        el.style.removeProperty('outline-offset');
        if (el.__tqOutline) {
            el.style.setProperty('outline', el.__tqOutline, el.__tqOutlinePrio || '');
        }
        if (el.__tqOffset) {
            el.style.setProperty('outline-offset', el.__tqOffset, el.__tqOffsetPrio || '');
        }
        delete el.__tqOutline; delete el.__tqOutlinePrio;
        delete el.__tqOffset; delete el.__tqOffsetPrio;
        el.removeAttribute('data-tq-highlight');
    }
    """

    def _apply_highlight(self, element: WebElement) -> None:
        try:
            self._driver.execute_script(self._APPLY_HIGHLIGHT_JS, element)
        except Exception as exc:  # noqa: BLE001
            self._log.warning("Не удалось подсветить элемент: %s", exc)

    def _clear_highlights(self) -> None:
        try:
            self._driver.execute_script(self._CLEAR_HIGHLIGHT_JS)
        except Exception as exc:  # noqa: BLE001
            self._log.warning("Не удалось снять highlight: %s", exc)

    @contextmanager
    def highlight(self) -> Iterator[None]:
        """Обвести элемент красной рамкой на время контекста (scoped).

        Рамка ставится через `!important`, чтобы её не переопределяли стили
        сайта, и снимается по выходе из контекста.
        """
        self._apply_highlight(self._find())
        try:
            yield
        finally:
            self._clear_highlights()

    @contextmanager
    def maybe_highlight(self) -> Iterator[None]:
        """Подсветить элемент, если в конфиге `highlight_elements=True`.

        Рамка снимается не в конце текущего действия, а перед СЛЕДУЮЩИМ:
        подсветка «залипает» на последнем затронутом элементе, поэтому её
        видно в паузах между действиями - в частности на screencast-видео.
        Снятие идёт document-wide по маркеру `data-tq-highlight`, поэтому
        переживает навигацию и перерендер.
        """
        if not self._config.highlight_elements:
            yield
            return
        self._clear_highlights()
        self._apply_highlight(self._find())
        yield
