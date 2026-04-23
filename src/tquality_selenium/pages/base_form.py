"""BaseForm для Selenium - расширенная версия с element_factory, title, url."""
from __future__ import annotations

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from tquality_selenium.elements.base_element import BaseElement
    from tquality_selenium.services.element_factory import ElementFactory


class BaseForm:
    """Page-object. Наследуйтесь; в `__init__` создавайте элементы через
    `self.element_factory`, затем вызывайте `super().__init__(unique_element=...)`.

    Тесты обращаются к бизнес-методам формы, а не к элементам напрямую.
    """

    def __init__(self, unique_element: BaseElement, name: str = "") -> None:
        self._unique_element = unique_element
        self._name = name or self.__class__.__name__

    @property
    def _browser(self) -> Any:
        from tquality_selenium.browser import BrowserService
        from tquality_selenium.container import SeleniumServices
        return SeleniumServices.get_service(BrowserService)

    @property
    def element_factory(self) -> ElementFactory:
        from tquality_selenium.container import SeleniumServices
        from tquality_selenium.services.element_factory import (
            ElementFactory as _EF,
        )
        return SeleniumServices.get_service(_EF)

    @property
    def name(self) -> str:
        return self._name

    @property
    def title(self) -> str:
        title: str = self._browser.driver.title
        return title

    @property
    def current_url(self) -> str:
        url: str = self._browser.driver.current_url
        return url

    @property
    def unique_element(self) -> BaseElement:
        return self._unique_element

    @property
    def is_displayed(self) -> bool:
        return self._unique_element.is_displayed

    def wait_for_displayed(self, timeout: float | None = None) -> BaseForm:
        self._unique_element.wait_for_displayed(timeout)
        return self
