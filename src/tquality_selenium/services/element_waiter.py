"""Waiter, специализированный на условиях для элементов."""
from __future__ import annotations

from typing import Any, Callable, TYPE_CHECKING, cast

from selenium.webdriver.support import expected_conditions as EC

if TYPE_CHECKING:
    from tquality_selenium.elements.by import By
    from tquality_selenium.services.waiter import Waiter


class ElementWaiter:
    """Ожидания по локатору: visible/clickable/invisible/not-present + custom."""

    def __init__(self, waiter: Waiter) -> None:
        self._waiter = waiter

    def until(
        self,
        condition: Callable[[Any], Any],
        by: By,
        name: str = "",
        timeout: float | None = None,
        message: str = "",
    ) -> Any:
        """Ожидание произвольного условия с человекочитаемым сообщением.

        `condition` - callable в стиле `selenium.webdriver.support.expected_conditions`
        (принимает `WebDriver`, возвращает truthy / non-falsy). `by`/`name`
        используются только в сообщении ожидания - сам resolver элемента
        обычно встроен в `condition`.

        ```python
        element_waiter.until(
            EC.text_to_be_present_in_element(by, "Готово"),
            by, "Кнопка отправки", message='have text "Готово"',
        )
        ```
        """
        return self._waiter.until(
            condition,
            message=f"{name or by.value} to {message or 'meet custom condition'}",
            timeout=timeout,
        )

    def until_visible(
        self, by: By, name: str = "", timeout: float | None = None,
    ) -> None:
        self._waiter.until(
            EC.visibility_of_element_located(by),
            message=f"{name or by.value} to be visible",
            timeout=timeout,
        )

    def until_clickable(
        self, by: By, name: str = "", timeout: float | None = None,
    ) -> None:
        self._waiter.until(
            EC.element_to_be_clickable(by),
            message=f"{name or by.value} to be clickable",
            timeout=timeout,
        )

    def until_present(
        self, by: By, name: str = "", timeout: float | None = None,
    ) -> None:
        self._waiter.until(
            EC.presence_of_element_located(by),
            message=f"{name or by.value} to be present",
            timeout=timeout,
        )

    def until_invisible(
        self, by: By, name: str = "", timeout: float | None = None,
    ) -> bool:
        return cast(bool, self._waiter.until(
            EC.invisibility_of_element_located(by),
            message=f"{name or by.value} to be invisible",
            timeout=timeout,
        ))

    def until_not_present(
        self, by: By, name: str = "", timeout: float | None = None,
    ) -> bool:
        return cast(bool, self._waiter.until(
            lambda driver: not driver.find_elements(*by),
            message=f"{name or by.value} to be not present",
            timeout=timeout,
        ))
