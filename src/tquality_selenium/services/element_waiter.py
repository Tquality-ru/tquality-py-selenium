"""Waiter, привязанный к конкретному элементу.

Создаётся самим элементом (`element.wait`); by/name/element берутся из
бинда, поэтому методы не требуют их передачи. Каждый метод возвращает сам
элемент - удобно чейнить:

```python
button.wait.until_clickable().click()
```
"""
from __future__ import annotations

from typing import Any, Callable, TYPE_CHECKING

from selenium.webdriver.support import expected_conditions as EC

if TYPE_CHECKING:
    from tquality_selenium.elements.base_element import BaseElement
    from tquality_selenium.services.style_property import StyleProperty
    from tquality_selenium.services.waiter import Waiter


class ElementWaiter[E: "BaseElement"]:
    """Ожидания, привязанные к элементу: visible/clickable/invisible/(not-)present
    + произвольное условие + computed-style."""

    def __init__(self, waiter: Waiter, element: E) -> None:
        self._waiter = waiter
        self._element = element

    @property
    def _name_for_msg(self) -> str:
        return self._element.name

    def until(
        self,
        condition: Callable[[E], Any],
        timeout: float | None = None,
        message: str = "",
    ) -> E:
        """Произвольное условие. `condition` принимает сам элемент - доступны
        `is_displayed`, `js_actions`, `text`, `get_attribute`, ... -
        работать с `WebDriver` напрямую не нужно."""
        self._waiter.until(
            lambda _: condition(self._element),
            message=f"{self._name_for_msg} to {message or 'meet custom condition'}",
            timeout=timeout,
        )
        return self._element

    def until_visible(self, timeout: float | None = None) -> E:
        self._waiter.until(
            EC.visibility_of_element_located(self._element.by),
            message=f"{self._name_for_msg} to be visible",
            timeout=timeout,
        )
        return self._element

    def until_clickable(self, timeout: float | None = None) -> E:
        self._waiter.until(
            EC.element_to_be_clickable(self._element.by),
            message=f"{self._name_for_msg} to be clickable",
            timeout=timeout,
        )
        return self._element

    def until_present(self, timeout: float | None = None) -> E:
        self._waiter.until(
            EC.presence_of_element_located(self._element.by),
            message=f"{self._name_for_msg} to be present",
            timeout=timeout,
        )
        return self._element

    def until_invisible(self, timeout: float | None = None) -> E:
        self._waiter.until(
            EC.invisibility_of_element_located(self._element.by),
            message=f"{self._name_for_msg} to be invisible",
            timeout=timeout,
        )
        return self._element

    def until_not_present(self, timeout: float | None = None) -> E:
        by = self._element.by
        self._waiter.until(
            lambda driver: not driver.find_elements(*by),
            message=f"{self._name_for_msg} to be not present",
            timeout=timeout,
        )
        return self._element

    def for_computed_style(
        self,
        style_property: str | StyleProperty,
        expected_value: str,
        timeout: float | None = None,
    ) -> E:
        return self.until(
            lambda e: e.js_actions.get_computed_style(style_property) == expected_value,
            timeout,
            message=f"have computed style {style_property} equal to {expected_value!r}",
        )
