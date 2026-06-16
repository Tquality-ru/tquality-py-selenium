"""Waiter, привязанный к `ContextManager`.

Создаётся самим менеджером (`context.wait`). Зеркало
`tquality_appium.services.context_waiter.ContextWaiter`: тонкая
обёртка над generic `tquality_core.Waiter`, в которой пока один
метод - `for_alert(...)`.

API возвращает либо «полезный объект» (для алертов - сам `Alert`),
либо `None` на таймаут; `raise_on_timeout=True` (или класс
исключения) - поднимает вместо `None`.
"""
from __future__ import annotations

from typing import Callable

from selenium.common.exceptions import NoAlertPresentException
from selenium.webdriver.common.alert import Alert
from tquality_core import Waiter

from tquality_selenium.services.context_manager import ContextManager

AlertPredicate = Callable[[Alert], object]


class ContextWaiter:
    """Ожидания, привязанные к `ContextManager`."""

    def __init__(self, waiter: Waiter, context_manager: ContextManager) -> None:
        self._waiter = waiter
        self._context = context_manager

    def for_alert(
        self,
        predicate: AlertPredicate | None = None,
        *,
        timeout: float | None = None,
        poll_interval: float | None = None,
        raise_on_timeout: bool | type[BaseException] = False,
        message: str = "",
    ) -> Alert | None:
        """Дождаться появления алерта.

        Без `predicate` - вернуть первый же `Alert`. С `predicate` -
        тот, на котором `predicate(alert)` truthy (типично:
        совпадение по `alert.text`).

        Возвращает `Alert` если условие выполнилось, `None` на
        таймаут. `raise_on_timeout=True` (или класс исключения) -
        поднять вместо `None`. `NoAlertPresentException` глотается
        как «ещё не готово».
        """
        matched: list[Alert] = []

        def _check() -> bool:
            try:
                alert = self._context.alert()
                if predicate is None or predicate(alert):
                    matched.append(alert)
                    return True
                return False
            except NoAlertPresentException:
                return False

        default_msg = (
            "alert matching predicate" if predicate is not None else "alert to appear"
        )
        ok = self._waiter.until(
            _check,
            timeout=timeout,
            poll_interval=poll_interval,
            raise_on_timeout=raise_on_timeout,
            message=message or default_msg,
        )
        return matched[-1] if ok and matched else None


__all__ = ["AlertPredicate", "ContextWaiter"]
