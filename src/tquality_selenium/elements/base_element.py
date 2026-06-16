"""Базовый UI-элемент.

Идентифицируется локатором `By` (NamedTuple `(by_kind, value)`). Сервисы
(browser, logger, waiters, js_actions) резолвятся через активный composition
root `SeleniumServices`, настроенный в `conftest.py` через `YourServices.setup()`.

`element.js_actions` возвращает `ElementJsActions`, привязанный к данному
элементу через ленивый резолвер (`self._find`), что снимает stale reference
между действиями. `element.wait` - аналогично, ожидания, привязанные к этому
элементу: `element.wait.until_visible()`, `element.wait.until_clickable()`...
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.remote.webelement import WebElement
from tquality_core import ElementState, StatePredicate, StateSpec

from tquality_selenium.elements.by import By
from tquality_selenium.elements.geometry import (
    ElementLocation,
    ElementRect,
    ElementSize,
)
from tquality_selenium.services.bidi_actions import BiDiElementActions
from tquality_selenium.services.element_waiter import ElementWaiter
from tquality_selenium.services.js_actions import ElementJsActions

if TYPE_CHECKING:
    from tquality_core import Logger

    from tquality_selenium.browser import BrowserService
    from tquality_selenium.elements.shadow_root_proxy import ShadowRootProxy


class BaseElement:
    def __init__(
        self,
        by: By,
        name: str = "",
        state: StateSpec = ElementState.DISPLAYED,
    ) -> None:
        self._by = by
        self._name = name or f"{self.__class__.__name__}({by.by_kind.value}={by.value!r})"
        self._state: StateSpec = state

    @property
    def by(self) -> By:
        return self._by

    @property
    def name(self) -> str:
        return self._name

    @property
    def state(self) -> StateSpec:
        return self._state

    def _await_state(self, timeout: float | None = None) -> None:
        """Ждать выполнения предусловия `self._state` перед взаимодействием.
        Поднимает `TimeoutException`, если состояние не достигнуто."""
        state = self._state
        if state is ElementState.EXISTS_IN_ANY_STATE:
            return
        if state is ElementState.CLICKABLE:
            self.wait.until_clickable(timeout, raise_on_timeout=True)
            return
        if state is ElementState.DISPLAYED:
            self.wait.until_visible(timeout, raise_on_timeout=True)
            return
        if callable(state):
            predicate: StatePredicate = state
            self.wait.until(
                predicate, timeout=timeout, raise_on_timeout=True,
                message=f"{self._name} to meet custom state",
            )
            return
        raise TypeError(f"Unsupported state spec: {state!r}")

    @property
    def _browser(self) -> BrowserService:
        from tquality_selenium.browser import BrowserService
        from tquality_selenium.container import SeleniumServices
        return SeleniumServices.get_service(BrowserService)

    @property
    def _log(self) -> Logger:
        from tquality_core import Logger

        from tquality_selenium.container import SeleniumServices
        return SeleniumServices.get_service(Logger)

    @property
    def wait(self) -> ElementWaiter[Self]:
        """Ожидания, привязанные к этому элементу. Каждый метод возвращает
        `bool` (см. `ElementWaiter`)."""
        from tquality_selenium.container import SeleniumServices
        from tquality_selenium.services.driver_waiter import DriverWaiter
        return ElementWaiter(SeleniumServices.get_service(DriverWaiter), self)

    @property
    def js_actions(self) -> ElementJsActions:
        """JS-действия, привязанные к этому элементу. Пример:
        `button.js_actions.click()`, `input.js_actions.scroll_into_view()`.
        Driver приходит через `driver_getter` от `_browser` (композиция,
        не container-lookup); резолвер элемента ленивый - stale-reference
        не возникает."""
        return ElementJsActions(
            self._find, driver_getter=lambda: self._browser.driver,
        )

    @property
    def bidi_actions(self) -> BiDiElementActions:
        """BiDi-действия, привязанные к этому элементу. Пример:
        `button.bidi_actions.capture_screenshot()`."""
        return BiDiElementActions(
            self._find, driver_getter=lambda: self._browser.driver,
        )

    def _find(self) -> WebElement:
        result: WebElement = self._browser.find_element(*self._by)
        return result

    @property
    def text(self) -> str:
        return self._find().text

    @property
    def is_displayed(self) -> bool:
        try:
            return self._find().is_displayed()
        except NoSuchElementException:
            return False

    @property
    def is_present(self) -> bool:
        elements = self._browser.find_elements(*self._by)
        return len(elements) > 0

    @property
    def is_enabled(self) -> bool:
        return self._find().is_enabled()

    @property
    def rect(self) -> ElementRect:
        """Bounding box элемента (x, y, width, height) во вьюпорте."""
        r = self._find().rect
        return ElementRect(
            x=r["x"], y=r["y"], width=r["width"], height=r["height"],
        )

    @property
    def size(self) -> ElementSize:
        """Ширина и высота элемента в CSS-пикселях."""
        s = self._find().size
        return ElementSize(width=s["width"], height=s["height"])

    @property
    def location(self) -> ElementLocation:
        """Верхний левый угол элемента во вьюпорте."""
        loc = self._find().location
        return ElementLocation(x=loc["x"], y=loc["y"])

    def get_attribute(self, attr: str) -> str | None:
        value = self._find().get_attribute(attr)
        return value if value is None else str(value)

    def get_dom_attribute(self, attr: str) -> str | None:
        """Сырое HTML-атрибут без fallback'а в DOM-property.

        В отличие от `get_attribute`, который при отсутствии HTML-атрибута
        проваливается в одноимённое JS-property (`.value`, `.checked`, ...),
        этот геттер возвращает строго `getAttribute()` - удобно, когда
        нужно отличить «атрибут есть в HTML» от «property есть в DOM».
        """
        value = self._find().get_dom_attribute(attr)
        return value if value is None else str(value)

    def get_property(self, name: str) -> Any:
        """DOM-property элемента (`.value` у input, `.checked` у checkbox, и т.д.).

        Возвращает «как есть»: строки, числа, bool, объекты - зависит от
        конкретной property.
        """
        return self._find().get_property(name)

    def value_of_css_property(self, name: str) -> str:
        """Computed-style значение CSS-свойства. Пустая строка если свойства нет.

        Альтернатива `element.js_actions.get_computed_style(...)`; этот
        вариант идёт через классический WebDriver-протокол, без JS-инъекций.
        """
        return self._find().value_of_css_property(name)

    @property
    def tag_name(self) -> str:
        """HTML-тег элемента в lower-case (`div` / `button` / `input` / ...)."""
        return self._find().tag_name

    @property
    def is_selected(self) -> bool:
        """`True` для отмеченных checkbox / radio / option в `<select>`."""
        return self._find().is_selected()

    @property
    def aria_role(self) -> str:
        """ARIA-role элемента: явный `[role]` или computed по тегу."""
        return self._find().aria_role

    @property
    def accessible_name(self) -> str:
        """Accessible name - то, как screen-reader озвучит элемент."""
        return self._find().accessible_name

    @property
    def shadow_root(self) -> ShadowRootProxy:
        """Lazy-прокси к Shadow DOM этого элемента-хоста.

        Возвращает `ShadowRootProxy`, у которого typed getter'ы
        (`get_button` / `get_input` / `get_label` / `get_checkbox` +
        generic `get_element[E]`) строят `BaseElement`-инстансы со
        shadow-aware `_find`. Цепочки `host.shadow_root.get_X(...)
        .shadow_root.get_Y(...)` стэкаются - каждый шаг резолвится при
        обращении, stale-reference исключён.
        """
        from tquality_selenium.elements.shadow_root_proxy import ShadowRootProxy
        return ShadowRootProxy(parent_find=self._find)

    def screenshot(self) -> bytes:
        """Скриншот элемента (PNG) через классический WebDriver-протокол.

        Для BiDi-варианта (не блокируется во время навигации) -
        `element.bidi_actions.capture_screenshot()`. Запись в файл -
        `Path("x.png").write_bytes(element.screenshot())`.
        """
        return self._find().screenshot_as_png

    def dismiss_if_visible(
        self,
        close_with: BaseElement | None = None,
        timeout: float | None = None,
    ) -> Self:
        """No-op если элемент не виден; иначе кликнуть и дождаться исчезновения.

        Удобно для опциональных баннеров (cookie-попап, city-popup), которые
        могут быть показаны или нет на момент захода на страницу.
        `close_with` - если кнопка закрытия не совпадает с самим элементом
        (например, баннер - это один узел, а закрывающий крестик - другой).
        """
        if not self.is_displayed:
            return self
        clicker = close_with if close_with is not None else self
        clicker.click()
        self.wait.until_invisible(timeout, raise_on_timeout=True)
        return self

    def click(self) -> None:
        self._log.info("Click: %s", self._name)
        self._await_state()
        with self.js_actions.maybe_highlight():
            self._find().click()

    def __repr__(self) -> str:
        return self._name
