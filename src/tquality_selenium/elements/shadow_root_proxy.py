"""Lazy-proxy к Shadow DOM элемента-хоста.

`BaseElement.shadow_root` отдаёт `ShadowRootProxy`, а не сырой
`selenium.webdriver.remote.shadowroot.ShadowRoot`: каждый дочерний элемент,
полученный через `proxy.get_*(...)`, на каждом `_find()` заново обходит
цепочку shadow root'ов от корня - stale-reference исключён, цепочки
произвольной глубины поддерживаются:

```python
deep_button = (
    form.shadow_root
        .get_label(By.css(".inner_field"))
        .shadow_root
        .get_button(By.css(".submit"))
)
deep_button.click()  # резолв всей цепочки происходит здесь
```

Сигнатуры getter'ов зеркалят `ElementFactory` (с дефолтами `state`).
`get_element[E]` - generic-метод для пользовательских наследников.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from selenium.webdriver.remote.webelement import WebElement
from tquality_core import ElementState, StateSpec

from tquality_selenium.elements.button import Button
from tquality_selenium.elements.checkbox import CheckBox
from tquality_selenium.elements.input import Input
from tquality_selenium.elements.label import Label

if TYPE_CHECKING:
    from tquality_selenium.elements.base_element import BaseElement
    from tquality_selenium.elements.by import By


class ShadowRootProxy:
    """Ленивый прокси: shadow root хост-элемента + типизированные getter'ы.

    Принимает `parent_find` - callable, возвращающий хост-элемент при каждом
    вызове. Возвращаемые getter'ами `BaseElement`-инстансы переопределяют
    свой `_find` так, чтобы при каждом вызове он шёл через
    `parent_find().shadow_root.find_element(*by)`. Цепочки нескольких
    shadow root'ов наслаиваются через property `shadow_root` у каждого
    промежуточного элемента.
    """

    def __init__(self, parent_find: Callable[[], WebElement]) -> None:
        self._parent_find = parent_find

    def _shadow_find(self, by: By) -> Callable[[], WebElement]:
        """Собрать lazy-резолвер: parent -> shadow_root -> find_element(by)."""
        parent_find = self._parent_find

        def _resolve() -> WebElement:
            return parent_find().shadow_root.find_element(*by)

        return _resolve

    def get_element[E: BaseElement](
        self,
        element_cls: type[E],
        by: By,
        name: str = "",
        state: StateSpec = ElementState.DISPLAYED,
    ) -> E:
        """Generic getter - возвращает экземпляр любого `BaseElement`-наследника.

        `_find` инстанса перепривязан к shadow-резолверу: цепочка
        host -> shadow_root -> find_element(by) выполняется при каждом
        обращении, stale-reference исключён.
        """
        elem = element_cls(by, name, state=state)
        elem._find = self._shadow_find(by)  # type: ignore[method-assign]
        return elem

    def get_button(
        self, by: By, name: str = "",
        state: StateSpec = ElementState.CLICKABLE,
    ) -> Button:
        return self.get_element(Button, by, name, state)

    def get_checkbox(
        self, by: By, name: str = "",
        state: StateSpec = ElementState.CLICKABLE,
    ) -> CheckBox:
        return self.get_element(CheckBox, by, name, state)

    def get_label(
        self, by: By, name: str = "",
        state: StateSpec = ElementState.DISPLAYED,
    ) -> Label:
        return self.get_element(Label, by, name, state)

    def get_input(
        self, by: By, name: str = "",
        state: StateSpec = ElementState.DISPLAYED,
    ) -> Input:
        return self.get_element(Input, by, name, state)


__all__ = ["ShadowRootProxy"]
