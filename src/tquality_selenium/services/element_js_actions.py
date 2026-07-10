"""Element-scope JS-действия (`ElementJsActions`) - приватная selenium-обёртка
над core-реализацией `tquality_core.JsElementActions`.

Скрипты и логика действий живут в core (`CommonElementJSScripts`); здесь
подключается selenium-driver через `driver_getter`-композицию и добавляется
selenium-специфика - логирование и `highlight`/`maybe_highlight`. Элемент
находится заново при каждом вызове (`find`-резолвер), что снимает stale
reference между действиями.

Класс приватный: пользователю он нужен разве что для аннотаций типов
(тип `Element.js_actions`) - туда его и можно force-импортировать.
"""

from __future__ import annotations

import typing
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Callable, Iterator

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from tquality_core.services.js_element_actions import (
    JsElementActions as CoreElementJsActions,
)

if TYPE_CHECKING:
    from tquality_core import Logger

    from tquality_selenium.config import SeleniumConfig

__all__ = ["ElementJsActions"]


class ElementJsActions(CoreElementJsActions):
    """Element-scope JS-действия (`CommonElementJSScripts`), привязанные к
    элементу через ленивый `find`-резолвер. Поверх core-действий добавляет
    логирование и `highlight`/`maybe_highlight`.
    """

    def __init__(
        self,
        find: Callable[[], WebElement],
        driver_getter: Callable[[], WebDriver],
    ) -> None:
        self._find = find
        self._driver_getter = driver_getter
        super().__init__(self._execute, self._execute_async, find)

    @property
    def _driver(self) -> WebDriver:
        return self._driver_getter()

    @property
    def _log(self) -> Logger:
        from tquality_core import step

        return step.resolve()

    @property
    def _config(self) -> SeleniumConfig:
        from tquality_selenium.config import SeleniumConfig
        from tquality_selenium.container import SeleniumServices

        return SeleniumServices.get_service(SeleniumConfig)

    def _execute(self, script: str, *args: Any) -> Any:
        self._log.info("Execute element JS: %s", script[:120])
        return self._driver.execute_script(script, *args)

    def _execute_async(self, script: str, *args: Any) -> Any:
        self._log.info("Execute async element JS: %s", script[:120])
        return self._driver.execute_async_script(script, *args)

    @typing.override
    def apply_highlight(self, outline: str = "3px solid red") -> None:
        # Подсветка - вспомогательная косметика: если элемент исчез
        # (навигация/перерендер), не фейлим тест, но пишем в лог.
        try:
            super().apply_highlight(outline)
        except Exception as exc:  # noqa: BLE001
            self._log.warning("Не удалось подсветить элемент: %s", exc)

    @typing.override
    def clear_highlights(self) -> None:
        try:
            super().clear_highlights()
        except Exception as exc:  # noqa: BLE001
            self._log.warning("Не удалось снять highlight: %s", exc)

    @contextmanager
    def maybe_highlight(self) -> Iterator[None]:
        """Подсветить элемент, если в конфиге `highlight_elements=True`.

        Рамка снимается не в конце текущего действия, а перед СЛЕДУЮЩИМ:
        подсветка «залипает» на последнем затронутом элементе, поэтому её
        видно в паузах между действиями - в частности на screencast-видео.
        Снятие идёт document-wide по маркеру `data-tq-highlight`, поэтому
        переживает навигацию и перерендер.
        """
        if not self._config.highlight_elements:
            yield
            return
        self.clear_highlights()
        self.apply_highlight()
        yield
