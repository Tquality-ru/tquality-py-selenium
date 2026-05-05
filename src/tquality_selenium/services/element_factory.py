"""Factory для создания элементов страницы.

Удобный короткий доступ из page-object'ов:

```python
class MyPage(BaseForm):
    def __init__(self):
        self._login = self.element_factory.button(By.id("login"), "Login")
        self._email = self.element_factory.input(By.name("email"), "Email")
```
"""
from __future__ import annotations

from tquality_selenium.elements.base_element import BaseElement
from tquality_selenium.elements.button import Button
from tquality_selenium.elements.by import By
from tquality_selenium.elements.checkbox import CheckBox
from tquality_selenium.elements.input import Input
from tquality_selenium.elements.label import Label


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
