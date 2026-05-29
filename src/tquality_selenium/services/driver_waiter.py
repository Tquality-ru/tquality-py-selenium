"""`DriverWaiter` - тонкая обёртка над `tquality_core.ResolvedWaiter`.

Логика и сигнатура `until(...)` целиком в core; здесь сохраняется
ожидаемое имя kwarg'а `driver_resolver=` (чтобы DI-провайдеры в
`SeleniumServices` оставались как есть) и удобный путь импорта из
`tquality_selenium`.
"""
from __future__ import annotations

from typing import Callable

from selenium.webdriver.remote.webdriver import WebDriver

from tquality_core import ResolvedWaiter, Waiter


class DriverWaiter(ResolvedWaiter[WebDriver]):
    def __init__(
        self,
        waiter: Waiter,
        driver_resolver: Callable[[], WebDriver],
    ) -> None:
        super().__init__(waiter, driver_resolver)


__all__ = ["DriverWaiter"]
