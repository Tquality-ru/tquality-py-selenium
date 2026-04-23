"""CheckBox - чекбокс с проверкой и установкой состояния."""
from __future__ import annotations

from tquality_selenium.elements.base_element import BaseElement


class CheckBox(BaseElement):
    """Чекбокс."""

    @property
    def is_checked(self) -> bool:
        """True, если чекбокс отмечен."""
        return self._find().is_selected()

    def check(self) -> None:
        """Поставить галочку (no-op если уже стоит)."""
        if not self.is_checked:
            self.click()

    def uncheck(self) -> None:
        """Снять галочку (no-op если уже снята)."""
        if self.is_checked:
            self.click()

    def toggle(self) -> None:
        """Переключить состояние."""
        self.click()
