from __future__ import annotations

from tquality_core import ElementState, StateSpec

from tquality_selenium.elements.base_element import BaseElement
from tquality_selenium.elements.by import By


class CheckBox(BaseElement):
    """Чекбокс."""

    def __init__(
        self,
        by: By,
        name: str = "",
        state: StateSpec = ElementState.CLICKABLE,
    ) -> None:
        super().__init__(by, name, state=state)

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
