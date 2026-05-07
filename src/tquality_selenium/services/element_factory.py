"""Factory для создания элементов страницы.

Удобный короткий доступ из page-object'ов:

```python
class MyPage(BaseForm):
    def __init__(self):
        self._login = self.element_factory.button(By.id("login"), "Login")
        self._email = self.element_factory.input(By.name("email"), "Email")
        self._rows = self.element_factory.elements(
            Button, By.css_selector(".row button"), "row",
        )
```
"""
from __future__ import annotations

from tquality_selenium.elements.base_element import BaseElement
from tquality_selenium.elements.button import Button
from tquality_selenium.elements.by import By
from tquality_selenium.elements.checkbox import CheckBox
from tquality_selenium.elements.input import Input
from tquality_selenium.elements.label import Label
from tquality_selenium.services.lazy_elements import LazyElements


class ElementFactory:
    """Создает типизированные элементы (Button/Input/CheckBox/Label/BaseElement)."""

    def element(self, by: By, name: str = "") -> BaseElement:
        return BaseElement(by, name)

    def button(self, by: By, name: str = "") -> Button:
        return Button(by, name)

    def checkbox(self, by: By, name: str = "") -> CheckBox:
        return CheckBox(by, name)

    def label(self, by: By, name: str = "") -> Label:
        return Label(by, name)

    def input(self, by: By, name: str = "") -> Input:
        return Input(by, name)

    def elements[E: BaseElement](
        self,
        element_cls: type[E],
        by: By,
        name_prefix: str = "",
    ) -> LazyElements[E]:
        """Лениво-резолвимая коллекция элементов типа `element_cls`.

        Длина и содержимое вычисляются по обращению - безопасно объявлять
        в `__init__` page-object'а. Имена: `f"{name_prefix} #{i}"` (1-based).
        Если `name_prefix` пуст - используется имя класса.
        """
        return LazyElements(element_cls, by, name_prefix)
