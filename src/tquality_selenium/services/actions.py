"""W3C input-actions chain - принимает `BaseElement`, не raw `WebElement`.

`Actions` - fluent builder поверх Selenium-овского `ActionChains`. Каждый
метод возвращает `self`, в конце `perform()` выполняет накопленную цепочку.
Элементы резолвятся через `BaseElement._find()` непосредственно при
`perform()`, поэтому stale reference между построением и выполнением
цепочки не возникает.

`browser.actions.move_to(menu).click(submenu_item).perform()` -
типичное использование. Driver приходит через `driver_getter`-композицию
от `BrowserService`. Каждый `browser.actions`-вызов отдаёт свежий builder
(state цепочки не шарится между вызовами).
"""
from __future__ import annotations

from typing import Callable, TYPE_CHECKING

from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.remote.webdriver import WebDriver

if TYPE_CHECKING:
    from tquality_selenium.elements.base_element import BaseElement


class Actions:
    """Fluent W3C-actions builder, элементы - `BaseElement` (lazy-резолв)."""

    def __init__(self, driver_getter: Callable[[], WebDriver]) -> None:
        self._driver_getter = driver_getter
        self._steps: list[Callable[[ActionChains], ActionChains]] = []

    # --- mouse -----------------------------------------------------------

    def click(self, element: BaseElement | None = None) -> Actions:
        """Click. Без `element` - клик в текущей точке курсора."""
        if element is None:
            self._steps.append(lambda ac: ac.click())
        else:
            self._steps.append(lambda ac: ac.click(element._find()))
        return self

    def click_and_hold(self, element: BaseElement | None = None) -> Actions:
        """Зажать ЛКМ. Парный `release()` отпускает."""
        if element is None:
            self._steps.append(lambda ac: ac.click_and_hold())
        else:
            self._steps.append(lambda ac: ac.click_and_hold(element._find()))
        return self

    def release(self, element: BaseElement | None = None) -> Actions:
        """Отпустить ранее зажатую ЛКМ."""
        if element is None:
            self._steps.append(lambda ac: ac.release())
        else:
            self._steps.append(lambda ac: ac.release(element._find()))
        return self

    def context_click(self, element: BaseElement | None = None) -> Actions:
        """Правый клик."""
        if element is None:
            self._steps.append(lambda ac: ac.context_click())
        else:
            self._steps.append(lambda ac: ac.context_click(element._find()))
        return self

    def double_click(self, element: BaseElement | None = None) -> Actions:
        if element is None:
            self._steps.append(lambda ac: ac.double_click())
        else:
            self._steps.append(lambda ac: ac.double_click(element._find()))
        return self

    def move_to(self, element: BaseElement) -> Actions:
        """Навести курсор на элемент (hover)."""
        self._steps.append(lambda ac: ac.move_to_element(element._find()))
        return self

    def move_to_with_offset(
        self, element: BaseElement, x: int, y: int,
    ) -> Actions:
        """Hover с offset'ом относительно центра элемента."""
        self._steps.append(
            lambda ac: ac.move_to_element_with_offset(element._find(), x, y),
        )
        return self

    def move_by_offset(self, x: int, y: int) -> Actions:
        """Сдвинуть курсор от текущей позиции на (x, y)."""
        self._steps.append(lambda ac: ac.move_by_offset(x, y))
        return self

    def drag_and_drop(
        self, source: BaseElement, target: BaseElement,
    ) -> Actions:
        self._steps.append(
            lambda ac: ac.drag_and_drop(source._find(), target._find()),
        )
        return self

    def drag_and_drop_by_offset(
        self, source: BaseElement, x: int, y: int,
    ) -> Actions:
        self._steps.append(
            lambda ac: ac.drag_and_drop_by_offset(source._find(), x, y),
        )
        return self

    # --- keyboard --------------------------------------------------------

    def send_keys(self, *keys: str) -> Actions:
        """Печатать `keys` в текущий фокус. `Keys.CONTROL`-подобные модификаторы
        работают через `key_down` / `key_up`, не здесь."""
        self._steps.append(lambda ac: ac.send_keys(*keys))
        return self

    def send_keys_to(self, element: BaseElement, *keys: str) -> Actions:
        """Сфокусировать `element` и напечатать `keys`."""
        self._steps.append(
            lambda ac: ac.send_keys_to_element(element._find(), *keys),
        )
        return self

    def key_down(
        self, key: str, element: BaseElement | None = None,
    ) -> Actions:
        """Зажать модификатор (`Keys.CONTROL` / `Keys.SHIFT` / ...).
        Парный `key_up(key)` обязателен."""
        if element is None:
            self._steps.append(lambda ac: ac.key_down(key))
        else:
            self._steps.append(lambda ac: ac.key_down(key, element._find()))
        return self

    def key_up(
        self, key: str, element: BaseElement | None = None,
    ) -> Actions:
        if element is None:
            self._steps.append(lambda ac: ac.key_up(key))
        else:
            self._steps.append(lambda ac: ac.key_up(key, element._find()))
        return self

    # --- scroll ---------------------------------------------------------

    def scroll_to(self, element: BaseElement) -> Actions:
        """Прокрутить страницу так, чтобы элемент попал во вьюпорт."""
        self._steps.append(lambda ac: ac.scroll_to_element(element._find()))
        return self

    def scroll_by(self, x: int, y: int) -> Actions:
        """Прокрутить страницу на (x, y) пикселей от текущей позиции."""
        self._steps.append(lambda ac: ac.scroll_by_amount(x, y))
        return self

    # --- timing ---------------------------------------------------------

    def pause(self, seconds: float) -> Actions:
        """Пауза между шагами (для тайминг-чувствительных UI)."""
        self._steps.append(lambda ac: ac.pause(seconds))
        return self

    # --- execute --------------------------------------------------------

    def perform(self) -> None:
        """Собрать `ActionChains` и выполнить накопленную цепочку.

        `BaseElement._find()` вызывается здесь, per-step - stale reference
        между билдером и выполнением исключён. После выполнения внутренний
        буфер очищается, builder можно переиспользовать для новой цепочки.
        """
        chain = ActionChains(self._driver_getter())
        for step in self._steps:
            step(chain)
        chain.perform()
        self._steps.clear()


__all__ = ["Actions"]
