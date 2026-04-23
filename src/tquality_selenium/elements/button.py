from __future__ import annotations

from tquality_selenium.elements.base_element import BaseElement


class Button(BaseElement):
    """Кнопка. В большинстве случаев - `click()`; для submit-кнопок `submit()`."""

    def submit(self) -> None:
        self._log.info("Submit: %s", self._name)
        self.wait_until_clickable()
        with self.js_actions.maybe_highlight():
            self._find().submit()
