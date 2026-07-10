"""Driver-scope JS-действия (`JsActions`) - приватная selenium-обёртка над
core-реализацией `tquality_core.JSActions`.

Скрипты и логика действий живут в core (`CommonJSScripts`); здесь
подключается selenium-driver через `driver_getter`-композицию от
`BrowserService` и добавляется selenium-специфика - логирование.

Класс приватный: пользователю он нужен разве что для аннотаций типов
(тип `BrowserService.js_actions`) - туда его и можно force-импортировать.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from selenium.webdriver.remote.webdriver import WebDriver
from tquality_core.services.js_actions import JSActions as CoreJsActions

if TYPE_CHECKING:
    from tquality_core import Logger

    from tquality_selenium.config import SeleniumConfig

__all__ = ["JsActions"]


class JsActions(CoreJsActions):
    """Driver-scope JS-действия (`CommonJSScripts`).

    Driver приходит через `driver_getter` (композиция от `BrowserService`).
    Logger/config резолвятся через DI - они per-test и не зависят от
    конкретного браузера.
    """

    def __init__(self, driver_getter: Callable[[], WebDriver]) -> None:
        self._driver_getter = driver_getter
        super().__init__(self._execute, self._execute_async, self._resolve_config())

    @property
    def _driver(self) -> WebDriver:
        return self._driver_getter()

    @property
    def _log(self) -> Logger:
        from tquality_core import step

        return step.resolve()

    @staticmethod
    def _resolve_config() -> SeleniumConfig:
        from tquality_selenium.config import SeleniumConfig
        from tquality_selenium.container import SeleniumServices

        return SeleniumServices.get_service(SeleniumConfig)

    def _execute(self, script: str, *args: Any) -> Any:
        self._log.info("Execute JS: %s", script[:120])
        return self._driver.execute_script(script, *args)

    def _execute_async(self, script: str, *args: Any) -> Any:
        self._log.info("Execute async JS: %s", script[:120])
        return self._driver.execute_async_script(script, *args)
