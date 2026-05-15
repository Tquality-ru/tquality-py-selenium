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
from tquality_selenium.utils.locator_utils import LocatorUtils


class ElementFactory:
    """Создает типизированные элементы (Button/Input/CheckBox/Label/BaseElement)."""

    def element[E: BaseElement](self, element_cls: type[E], by: By, name: str = "") -> E:
        return element_cls(by, name)

    def button(self, by: By, name: str = "") -> Button:
        return self.element(Button, by, name)

    def checkbox(self, by: By, name: str = "") -> CheckBox:
        return self.element(CheckBox, by, name)

    def label(self, by: By, name: str = "") -> Label:
        return self.element(Label, by, name)

    def input(self, by: By, name: str = "") -> Input:
        return self.element(Input, by, name)

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

    def buttons(self, by: By, name_prefix: str = "") -> LazyElements[Button]:
        return self.elements(Button, by, name_prefix)

    def checkboxes(self, by: By, name_prefix: str = "") -> LazyElements[CheckBox]:
        return self.elements(CheckBox, by, name_prefix)

    def labels(self, by: By, name_prefix: str = "") -> LazyElements[Label]:
        return self.elements(Label, by, name_prefix)

    def inputs(self, by: By, name_prefix: str = "") -> LazyElements[Input]:
        return self.elements(Input, by, name_prefix)

    def get_child_element[E: BaseElement](self,
                                          element_cls: type[E],
                                          parent: BaseElement,
                                          by: By,
                                          name: str = "") -> E:
        return element_cls(LocatorUtils.join_xpath(parent.by, by), name)

    def get_child_button(self, parent: BaseElement, by: By, name: str = "") -> Button:
        return self.get_child_element(Button, parent, by, name)

    def get_child_checkbox(self, parent: BaseElement, by: By, name: str = "") -> CheckBox:
        return self.get_child_element(CheckBox, parent, by, name)

    def get_child_label(self, parent: BaseElement, by: By, name: str = "") -> Label:
        return self.get_child_element(Label, parent, by, name)

    def get_child_input(self, parent: BaseElement, by: By, name: str = "") -> Input:
        return self.get_child_element(Input, parent, by, name)

    def get_child_elements[E: BaseElement](self,
                                           element_cls: type[E],
                                           parent: BaseElement,
                                           by: By,
                                           name_prefix: str = "") -> LazyElements[E]:
        return LazyElements(element_cls, LocatorUtils.join_xpath(parent.by, by), name_prefix)

    def get_child_buttons(self, parent: BaseElement, by: By, name_prefix: str = "") -> LazyElements[Button]:
        return self.get_child_elements(Button, parent, by, name_prefix)

    def get_child_checkboxes(self, parent: BaseElement, by: By, name_prefix: str = "") -> LazyElements[CheckBox]:
        return self.get_child_elements(CheckBox, parent, by, name_prefix)

    def get_child_labels(self, parent: BaseElement, by: By, name_prefix: str = "") -> LazyElements[Label]:
        return self.get_child_elements(Label, parent, by, name_prefix)

    def get_child_inputs(self, parent: BaseElement, by: By, name_prefix: str = "") -> LazyElements[Input]:
        return self.get_child_elements(Input, parent, by, name_prefix)
