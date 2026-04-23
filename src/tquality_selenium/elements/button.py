"""Кнопка - элемент с явным действием `submit` поверх обычного click."""
from __future__ import annotations

from tquality_selenium.elements.base_element import BaseElement


class Button(BaseElement):
    """Кнопка. Для большинства сценариев используйте `click()`."""

    def submit(self) -> None:
        """Отправить форму, которой принадлежит кнопка."""
        self.wait_until_clickable()
        self._find().submit()
