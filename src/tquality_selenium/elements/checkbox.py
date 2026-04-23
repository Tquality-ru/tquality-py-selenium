from __future__ import annotations

from tquality_selenium.elements.base_element import BaseElement


class CheckBox(BaseElement):
    """Чекбокс."""

    @property
    def is_checked(self) -> bool:
        return self._find().is_selected()

    def check(self) -> None:
        if not self.is_checked:
            self._log.info("Check: %s", self._name)
            self.click()

    def uncheck(self) -> None:
        if self.is_checked:
            self._log.info("Uncheck: %s", self._name)
            self.click()

    def toggle(self) -> None:
        self._log.info("Toggle: %s", self._name)
        self.click()
