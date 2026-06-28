from __future__ import annotations

from tquality_core import ElementState, StateSpec

from tquality_selenium.elements.element import Element
from tquality_selenium.elements.by import By


class Button(Element):
    """Кнопка. В большинстве случаев - `click()`; для submit-кнопок `submit()`."""

    def __init__(
        self,
        by: By,
        name: str = "",
        state: StateSpec = ElementState.CLICKABLE,
    ) -> None:
        super().__init__(by, name, state=state)

    def submit(self) -> None:
        self._log.info("Submit: %s", self._name)
        self._await_state()
        with self.js_actions.maybe_highlight():
            self._find().submit()
