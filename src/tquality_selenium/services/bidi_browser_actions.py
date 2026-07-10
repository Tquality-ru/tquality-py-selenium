"""BiDi-действия driver-scope (`BiDiBrowserActions`).

Высокоуровневые обёртки + escape-hatch к "сырым" BiDi-модулям Selenium
(`script` / `network` / `browsing_context` / `input`) для пользовательских
интеракций, которые не покрыты предоставленными методами - по аналогии
с `element.wait.until(custom_condition)`, где фреймворк даёт и удобные
обёртки, и доступ к низкоуровневому API.

Driver приходит через `driver_getter`-композицию от `BrowserService`
(см. `BrowserService.bidi`), а не реcолвится через DI-контейнер.
"""
from __future__ import annotations

import base64
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Iterator

from selenium.webdriver.common.bidi.browsing_context import BrowsingContext
from selenium.webdriver.common.bidi.input import FileDialogInfo, Input
from selenium.webdriver.common.bidi.network import Network
from selenium.webdriver.common.bidi.script import Script
from selenium.webdriver.remote.webdriver import WebDriver

if TYPE_CHECKING:
    from tquality_core import Logger


class BiDiBrowserActions:
    """BiDi-операции на уровне driver'а.

    Свойства `script` / `network` / `browsing_context` / `input` -
    raw-доступ к BiDi-модулям Selenium для кастомных сценариев. Поверх
    них живут высокоуровневые методы (`intercept_file_dialog`,
    `capture_screenshot`).
    """

    def __init__(self, driver_getter: Callable[[], WebDriver]) -> None:
        self._driver_getter = driver_getter

    @property
    def _driver(self) -> WebDriver:
        return self._driver_getter()

    @property
    def _log(self) -> Logger:
        from tquality_core import step

        return step.resolve()

    # --- raw BiDi modules (escape hatch) -------------------------------

    @property
    def script(self) -> Script:
        """BiDi `script`-модуль: console handlers, preload-скрипты, evaluate."""
        return self._driver.script

    @property
    def network(self) -> Network:
        """BiDi `network`-модуль: request/response handlers, intercept."""
        return self._driver.network

    @property
    def browsing_context(self) -> BrowsingContext:
        """BiDi `browsing_context`-модуль: navigate, screenshots, tree."""
        return self._driver.browsing_context

    @property
    def input(self) -> Input:
        """BiDi `input`-модуль: actions, set_files, file-dialog handlers."""
        return self._driver.input

    # --- high-level helpers --------------------------------------------

    @contextmanager
    def intercept_file_dialog(
        self,
        files: list[str | Path],
        *,
        timeout: float = 5.0,
    ) -> Iterator[None]:
        """Перехватить следующий открывшийся file-dialog и подсунуть `files`.

        ```python
        with browser.bidi.intercept_file_dialog([avatar_path]):
            upload_button.click()
        ```

        Безопасный аналог JS-инъекции `input.click()` + ручной подмены
        значения - работает в Chrome/Firefox/Edge без CDP.
        """
        # Локальные пути резолвим в абсолютные; пути, которых нет на клиенте
        # (например, node-абсолютный путь на удалённом grid-агенте другой ОС),
        # прокидываем как есть - их разрешает уже агент, а client-side resolve
        # на чужой ОС их бы испортил (C:\... -> /cwd/C:\...).
        resolved = [str(Path(f).resolve()) if Path(f).exists() else str(f) for f in files]
        fired = threading.Event()
        input_mod = self.input

        def _on_dialog(info: FileDialogInfo) -> None:
            if fired.is_set() or info.element is None:
                return
            input_mod.set_files(info.context, info.element, resolved)
            fired.set()

        self._log.info("BiDi: intercept file dialog (%d files)", len(resolved))
        handler_id = input_mod.add_file_dialog_handler(_on_dialog)
        try:
            yield
            if not fired.wait(timeout=timeout):
                raise TimeoutError(
                    f"File dialog не открылся за {timeout}s",
                )
        finally:
            input_mod.remove_file_dialog_handler(handler_id)

    def capture_screenshot(self) -> bytes:
        """Screenshot вьюпорта через BiDi `browsingContext.captureScreenshot`.

        Не блокируется во время навигации и не зависит от CDP - проходит
        одинаково на Chrome/Firefox/Edge.
        """
        self._log.info("BiDi: capture viewport screenshot")
        b64 = self.browsing_context.capture_screenshot(
            self._driver.current_window_handle,
        )
        return base64.b64decode(b64)


__all__ = ["BiDiBrowserActions"]
