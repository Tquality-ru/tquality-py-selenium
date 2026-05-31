"""BaseForm для Selenium - расширенная версия с element_factory, title, url."""
from __future__ import annotations

from tquality_selenium.browser import BrowserService
from tquality_selenium.container import SeleniumServices
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
    def _browser(self) -> BrowserService:
        return SeleniumServices.get_service(BrowserService)

    @property
    def element_factory(self) -> ElementFactory:
        return SeleniumServices.get_service(ElementFactory)

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

    def wait_for_displayed(
        self,
        timeout: float | None = None,
        *,
        poll_interval: float | None = None,
        raise_on_timeout: bool | type[BaseException] = False,
        message: str = "",
    ) -> bool:
        """Ждать появления `unique_element`. Сигнатура и дефолты совпадают
        с `element.wait.until_present(...)`: возвращает `bool` (не сам
        `BaseForm`), таймаут не кидает по умолчанию - используйте
        `raise_on_timeout=True` для жёсткого падения."""
        return self._unique_element.wait.until_present(
            timeout,
            poll_interval=poll_interval,
            raise_on_timeout=raise_on_timeout,
            message=message or f"{self._name} to be displayed",
        )
