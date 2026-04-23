from __future__ import annotations

from selenium.webdriver.common.keys import Keys

from tquality_selenium.elements.base_element import BaseElement


class Input(BaseElement):
    """Текстовое поле ввода."""

    @property
    def value(self) -> str:
        """Текущее значение (атрибут `value`)."""
        return self.get_attribute("value") or ""

    def clear(self) -> None:
        self._log.info("Clear: %s", self._name)
        with self.js_actions.maybe_highlight():
            self._find().clear()

    def type_text(self, text: str) -> None:
        """Заменить содержимое поля на `text`.

        Использует Ctrl+A для выделения - защищает от stale element, если
        между поиском и вводом DOM перерендерится.
        """
        self._log.info("Type into %s: %s", self._name, text)
        self._element_waiter.until_visible(self._by, self._value, self._name)
        self._find().send_keys(Keys.CONTROL, "a", Keys.NULL, text)

    def append_text(self, text: str) -> None:
        self._log.info("Append to %s: %s", self._name, text)
        self.wait_until_visible()
        self._find().send_keys(text)
