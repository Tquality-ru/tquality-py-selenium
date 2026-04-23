"""Базовый элемент Selenium-реализации.

Реализует абстрактный интерфейс `tquality_core.BaseElement` через Selenium.
От него наследуются конкретные элементы: Button, Label, Input, CheckBox.

Каждая операция ленивая: элемент ищется заново перед каждым действием, что
защищает от stale element references при перерендеринге DOM.
"""
from __future__ import annotations

from typing import Callable

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from tquality_core import BaseElement as CoreBaseElement
from tquality_core import Locator

from tquality_selenium.browser import BrowserService


class BaseElement(CoreBaseElement):
    """Selenium-элемент, найденный по `Locator(by, value)`."""

    def __init__(
        self,
        locator: Locator,
        name: str = "",
        *,
        browser_resolver: Callable[[], BrowserService],
        default_timeout: float = 10.0,
    ) -> None:
        super().__init__(locator, name)
        self._browser_resolver = browser_resolver
        self._default_timeout = default_timeout

    @property
    def _browser(self) -> BrowserService:
        return self._browser_resolver()

    def _find(self) -> WebElement:
        return self._browser.find_element(self._locator.by, self._locator.value)

    def _timeout(self, timeout: float | None) -> float:
        return timeout if timeout is not None else self._default_timeout

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
        elements = self._browser.find_elements(self._locator.by, self._locator.value)
        return len(elements) > 0

    @property
    def is_enabled(self) -> bool:
        return self._find().is_enabled()

    def get_attribute(self, attr: str) -> str | None:
        value = self._find().get_attribute(attr)
        return value if value is None else str(value)

    def click(self) -> None:
        self.wait_until_clickable()
        self._find().click()

    def wait_for_displayed(self, timeout: float | None = None) -> BaseElement:
        return self.wait_until_visible(timeout)

    def wait_until_visible(self, timeout: float | None = None) -> BaseElement:
        WebDriverWait(self._browser.driver, self._timeout(timeout)).until(
            EC.visibility_of_element_located(self._locator),
        )
        return self

    def wait_until_clickable(self, timeout: float | None = None) -> BaseElement:
        WebDriverWait(self._browser.driver, self._timeout(timeout)).until(
            EC.element_to_be_clickable(self._locator),
        )
        return self

    def wait_until_invisible(self, timeout: float | None = None) -> BaseElement:
        WebDriverWait(self._browser.driver, self._timeout(timeout)).until(
            EC.invisibility_of_element_located(self._locator),
        )
        return self

    def wait_until_not_present(self, timeout: float | None = None) -> BaseElement:
        by, value = self._locator
        WebDriverWait(self._browser.driver, self._timeout(timeout)).until(
            lambda d: not d.find_elements(by, value),
            f"{self._name} должен исчезнуть из DOM",
        )
        return self
