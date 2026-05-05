"""Waiter, специализированный на условиях для элементов."""
from __future__ import annotations

from typing import TYPE_CHECKING, cast

from selenium.webdriver.support import expected_conditions as EC

if TYPE_CHECKING:
    from tquality_selenium.elements.by import By
    from tquality_selenium.services.waiter import Waiter


class ElementWaiter:
    """Ожидания по локатору: visible/clickable/invisible/not-present."""

    def __init__(self, waiter: Waiter) -> None:
        self._waiter = waiter

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
