"""Waiter, специализированный на условиях для элементов."""
from __future__ import annotations

from typing import TYPE_CHECKING, cast

from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC

if TYPE_CHECKING:
    from tquality_selenium.services.waiter import Waiter


class ElementWaiter:
    """Ожидания по локатору: visible/clickable/invisible/not-present."""

    def __init__(self, waiter: Waiter) -> None:
        self._waiter = waiter

    def until_visible(
        self, by: str, value: str, name: str = "", timeout: float | None = None,
    ) -> WebElement:
        return cast(WebElement, self._waiter.until(
            EC.visibility_of_element_located((by, value)),
            message=f"{name or value} to be visible",
            timeout=timeout,
        ))

    def until_clickable(
        self, by: str, value: str, name: str = "", timeout: float | None = None,
    ) -> WebElement:
        return cast(WebElement, self._waiter.until(
            EC.element_to_be_clickable((by, value)),
            message=f"{name or value} to be clickable",
            timeout=timeout,
        ))

    def until_present(
        self, by: str, value: str, name: str = "", timeout: float | None = None,
    ) -> WebElement:
        return cast(WebElement, self._waiter.until(
            EC.presence_of_element_located((by, value)),
            message=f"{name or value} to be present",
            timeout=timeout,
        ))

    def until_invisible(
        self, by: str, value: str, name: str = "", timeout: float | None = None,
    ) -> bool:
        return cast(bool, self._waiter.until(
            EC.invisibility_of_element_located((by, value)),
            message=f"{name or value} to be invisible",
            timeout=timeout,
        ))

    def until_not_present(
        self, by: str, value: str, name: str = "", timeout: float | None = None,
    ) -> bool:
        return cast(bool, self._waiter.until(
            lambda driver: not driver.find_elements(by, value),
            message=f"{name or value} to be not present",
            timeout=timeout,
        ))
