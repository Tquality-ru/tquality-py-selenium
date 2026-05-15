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

from typing import Any, Self

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.remote.webelement import WebElement

from tquality_selenium.elements.by import By
from tquality_selenium.services.element_waiter import ElementWaiter
from tquality_selenium.services.js_actions import ElementJsActions


class BaseElement:
    def __init__(self, by: By, name: str = "") -> None:
        self._by = by
        self._name = name or f"{self.__class__.__name__}({by.by_kind.value}={by.value!r})"

    @property
    def by(self) -> By:
        return self._by

    @property
    def name(self) -> str:
        return self._name

    @property
    def _browser(self) -> Any:
        from tquality_selenium.browser import BrowserService
        from tquality_selenium.container import SeleniumServices
        return SeleniumServices.get_service(BrowserService)

    @property
    def _log(self) -> Any:
        from tquality_core import Logger
        from tquality_selenium.container import SeleniumServices
        return SeleniumServices.get_service(Logger)

    @property
    def wait(self) -> ElementWaiter[Self]:
        """Ожидания, привязанные к этому элементу. Каждый метод возвращает
        сам элемент - удобно чейнить:
        `button.wait.until_clickable().click()`."""
        from tquality_selenium.container import SeleniumServices
        from tquality_selenium.services.waiter import Waiter
        return ElementWaiter(SeleniumServices.get_service(Waiter), self)

    @property
    def js_actions(self) -> ElementJsActions:
        """JS-действия, привязанные к этому элементу. Пример:
        `button.js_actions.click()`, `input.js_actions.scroll_into_view()`.
        Резолвер элемента ленивый - stale reference не возникает."""
        return ElementJsActions(self._find)

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

    def get_attribute(self, attr: str) -> str | None:
        value = self._find().get_attribute(attr)
        return value if value is None else str(value)

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
        self.wait.until_invisible(timeout)
        return self

    def click(self) -> None:
        self._log.info("Click: %s", self._name)
        self.wait.until_clickable()
        with self.js_actions.maybe_highlight():
            self._find().click()

    def __repr__(self) -> str:
        return self._name
