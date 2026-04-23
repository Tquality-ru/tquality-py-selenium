"""Factory для создания элементов страницы.

Удобный короткий доступ из page-object'ов:

```python
class MyPage(BaseForm):
    def __init__(self):
        self._login = self.element_factory.button(By.ID, "login", "Login")
        self._email = self.element_factory.input(By.NAME, "email", "Email")
```
"""
from __future__ import annotations

from tquality_selenium.elements.base_element import BaseElement
from tquality_selenium.elements.button import Button
from tquality_selenium.elements.checkbox import CheckBox
from tquality_selenium.elements.input import Input
from tquality_selenium.elements.label import Label


class ElementFactory:
    """Создает типизированные элементы (Button/Input/CheckBox/Label/BaseElement)."""

    def element(self, by: str, value: str, name: str = "") -> BaseElement:
        return BaseElement(by, value, name)

    def button(self, by: str, value: str, name: str = "") -> Button:
        return Button(by, value, name)

    def checkbox(self, by: str, value: str, name: str = "") -> CheckBox:
        return CheckBox(by, value, name)

    def label(self, by: str, value: str, name: str = "") -> Label:
        return Label(by, value, name)

    def input(self, by: str, value: str, name: str = "") -> Input:
        return Input(by, value, name)
