"""Базовый UI-элемент.

Идентифицируется парой `(by, value)`. Сервисы (browser, logger, waiters,
js_actions) резолвятся через активный composition root `SeleniumServices`,
настроенный в `conftest.py` через `YourServices.setup()`.

`element.js_actions` возвращает `ElementJsActions`, привязанный к данному
элементу через ленивый резолвер (`self._find`), что снимает stale reference
между действиями.
"""
from __future__ import annotations

from typing import Any

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.remote.webelement import WebElement

from tquality_selenium.services.js_actions import ElementJsActions


class BaseElement:
    def __init__(self, by: str, value: str, name: str = "") -> None:
        self._by = by
        self._value = value
        self._name = name or f"{self.__class__.__name__}({by}={value!r})"

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
    def _element_waiter(self) -> Any:
        from tquality_selenium.container import SeleniumServices
        from tquality_selenium.services.element_waiter import ElementWaiter
        return SeleniumServices.get_service(ElementWaiter)

    @property
    def js_actions(self) -> ElementJsActions:
        """JS-действия, привязанные к этому элементу. Пример:
        `button.js_actions.click()`, `input.js_actions.scroll_into_view()`.
        Резолвер элемента ленивый - stale reference не возникает."""
        return ElementJsActions(self._find)

    def _find(self) -> WebElement:
        result: WebElement = self._browser.find_element(self._by, self._value)
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
        elements = self._browser.find_elements(self._by, self._value)
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
    ) -> BaseElement:
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
        self.wait_until_invisible(timeout)
        return self

    def wait_for_displayed(self, timeout: float | None = None) -> BaseElement:
        self._element_waiter.until_visible(
            self._by, self._value, self._name, timeout,
        )
        return self

    def wait_until_visible(self, timeout: float | None = None) -> BaseElement:
        self._element_waiter.until_visible(
            self._by, self._value, self._name, timeout,
        )
        return self

    def wait_until_clickable(self, timeout: float | None = None) -> BaseElement:
        self._element_waiter.until_clickable(
            self._by, self._value, self._name, timeout,
        )
        return self

    def wait_until_invisible(self, timeout: float | None = None) -> BaseElement:
        self._element_waiter.until_invisible(
            self._by, self._value, self._name, timeout,
        )
        return self

    def wait_until_not_present(self, timeout: float | None = None) -> BaseElement:
        self._element_waiter.until_not_present(
            self._by, self._value, self._name, timeout,
        )
        return self

    def click(self) -> None:
        self._log.info("Click: %s", self._name)
        self._element_waiter.until_clickable(self._by, self._value, self._name)
        with self.js_actions.maybe_highlight():
            self._find().click()

    def __repr__(self) -> str:
        return self._name
