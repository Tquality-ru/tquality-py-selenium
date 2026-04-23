"""Input - текстовое поле с очисткой и вводом."""
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
        """Очистить содержимое поля."""
        self._find().clear()

    def type_text(self, text: str) -> None:
        """Заменить содержимое поля на `text`.

        Использует `Ctrl+A` для выделения - защищает от stale element, если
        `clear()` вызовет перерендер DOM между поиском и вводом.
        """
        self.wait_until_visible()
        self._find().send_keys(Keys.CONTROL, "a", Keys.NULL, text)

    def append_text(self, text: str) -> None:
        """Добавить `text` в конец текущего значения."""
        self.wait_until_visible()
        self._find().send_keys(text)
