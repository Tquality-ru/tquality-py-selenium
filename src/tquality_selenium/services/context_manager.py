"""Фасад навигации по тому, куда смотрит `WebDriver`.

Один объект-зонтик над тремя слоями «фокуса» сессии в браузере:

1. **Окна/табы** - W3C `window_handles`.
   API: `windows`, `current_window`, `switch_to_window(handle | index)`,
   `with window(target):`.
2. **Iframes**.
   API: `switch_to_frame(name | index | element)`,
   `back_to_default_content()`, `with frame(target):`.
3. **Алерты** - JS `alert()` / `confirm()` / `prompt()`, прокидываются
   как W3C alert. API: `alert()`, `accept_alert()`, `dismiss_alert()`.

Зеркало `tquality_appium.services.context_manager.ContextManager`
(минус native/webview-контексты, которых в селениуме не бывает -
браузерная сессия всегда «webview»).

`context.wait.for_alert(predicate)` - ожидания, привязанные к этому
фасаду; см. `ContextWaiter`.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Iterator

from selenium.webdriver.common.alert import Alert
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

if TYPE_CHECKING:
    from tquality_core import Logger

    from tquality_selenium.services.context_waiter import ContextWaiter


class UnknownWindowError(RuntimeError):
    """Запрошен window-handle, которого нет в `driver.window_handles`."""


class ContextManager:
    """Доступ к окнам/фреймам/алертам + переключение между ними."""

    @property
    def _driver(self) -> WebDriver:
        from tquality_selenium.browser import BrowserService
        from tquality_selenium.container import SeleniumServices
        return SeleniumServices.get_service(BrowserService).driver

    @property
    def _log(self) -> Logger:
        from tquality_core import Logger

        from tquality_selenium.container import SeleniumServices
        return SeleniumServices.get_service(Logger)

    # --- Окна/табы ---

    @property
    def windows(self) -> list[str]:
        """Все handle открытых окон/табов."""
        return list(self._driver.window_handles)

    @property
    def current_window(self) -> str:
        """Handle текущего окна."""
        result: str = self._driver.current_window_handle
        return result

    def switch_to_window(self, target: str | int) -> None:
        """Переключиться в окно по handle или индексу в `windows`."""
        if isinstance(target, int):
            handles = self.windows
            if not 0 <= target < len(handles):
                raise UnknownWindowError(
                    f"Window index {target} вне диапазона (окон: {len(handles)})"
                )
            handle = handles[target]
        else:
            if target not in self.windows:
                raise UnknownWindowError(
                    f"Window handle {target!r} недоступен. Доступны: {self.windows!r}"
                )
            handle = target
        self._log.info("Switching window: %s -> %s", self.current_window, handle)
        self._driver.switch_to.window(handle)

    @contextmanager
    def window(self, target: str | int) -> Iterator[None]:
        """Временно переключиться в окно; по выходу - обратно."""
        previous = self.current_window
        self.switch_to_window(target)
        try:
            yield
        finally:
            if previous in self.windows:
                self.switch_to_window(previous)

    # --- Фреймы ---

    def switch_to_frame(self, target: str | int | WebElement) -> None:
        """Переключиться во фрейм по name/id, индексу или элементу."""
        self._log.info("Switching to frame: %r", target)
        self._driver.switch_to.frame(target)

    def back_to_default_content(self) -> None:
        """Вернуться в верхний документ из любого фрейма."""
        self._log.info("Switching back to default content")
        self._driver.switch_to.default_content()

    @contextmanager
    def frame(self, target: str | int | WebElement) -> Iterator[None]:
        """Временно переключиться во фрейм; по выходу - в default content.

        Восстановление идёт не в «предыдущий фрейм», а в самый верхний
        документ. Вложенные фреймы - ответственность вызывающего
        кода (W3C API не предоставляет parent-фрейм-stack).
        """
        self.switch_to_frame(target)
        try:
            yield
        finally:
            self.back_to_default_content()

    # --- Алерты ---

    def alert(self) -> Alert:
        """Активный алерт. Бросает `NoAlertPresentException`, если его нет."""
        result: Alert = self._driver.switch_to.alert
        return result

    def accept_alert(self) -> None:
        a = self.alert()
        self._log.info("Accept alert: %s", a.text)
        a.accept()

    def dismiss_alert(self) -> None:
        a = self.alert()
        self._log.info("Dismiss alert: %s", a.text)
        a.dismiss()

    @property
    def wait(self) -> ContextWaiter:
        """Ожидания, привязанные к контексту: `context.wait.for_alert(...)`."""
        from tquality_selenium.container import SeleniumServices
        from tquality_selenium.services.context_waiter import ContextWaiter
        return ContextWaiter(SeleniumServices.waiter(), self)


__all__ = ["ContextManager", "UnknownWindowError"]
