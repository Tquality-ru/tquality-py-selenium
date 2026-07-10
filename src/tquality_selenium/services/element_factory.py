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

Все методы создания одиночного элемента принимают `state`
(`ElementState` или callable-предикат). Дефолт сигнатуры совпадает
с дефолтом конструктора целевого класса: `Button`/`CheckBox` -
`CLICKABLE`, остальные - `DISPLAYED`. Когда стандартное условие
мешает (нестандартный web-компонент, кастомные bounds, своё условие
готовности) - передайте свой.
"""

from __future__ import annotations

from tquality_core import ElementState, FormattableElement, StateSpec

from tquality_selenium.elements.button import Button
from tquality_selenium.elements.by import By
from tquality_selenium.elements.checkbox import CheckBox
from tquality_selenium.elements.element import Element
from tquality_selenium.elements.input import Input
from tquality_selenium.elements.label import Label
from tquality_selenium.services.lazy_elements import LazyElements
from tquality_selenium.utils.locator_utils import LocatorUtils


class FormattableElementFactory:
    """Шаблонные элементы: локатор с placeholder'ами + отложенная сборка.

    Доступна как `element_factory.formattable`. Каждый метод повторяет
    сигнатуру одноимённого метода `ElementFactory`, но возвращает не сам
    элемент, а `FormattableElement` - вызовите `.format(*args, **kwargs)`,
    чтобы подставить аргументы в `value` локатора и получить готовый элемент:

    ```python
    row = element_factory.formattable.button(
        By.xpath("//tr[td[normalize-space()={!r}]]//button"),
    )
    row.format("Иванов").click()
    ```
    """

    def element[E: Element](
        self,
        element_cls: type[E],
        by: By,
        name: str = "",
        state: StateSpec = ElementState.DISPLAYED,
    ) -> FormattableElement[E, By]:
        return FormattableElement(by, lambda b: element_cls(b, name, state=state), name)

    def button(
        self,
        by: By,
        name: str = "",
        state: StateSpec = ElementState.CLICKABLE,
    ) -> FormattableElement[Button, By]:
        return FormattableElement(by, lambda b: Button(b, name, state=state), name)

    def checkbox(
        self,
        by: By,
        name: str = "",
        state: StateSpec = ElementState.CLICKABLE,
    ) -> FormattableElement[CheckBox, By]:
        return FormattableElement(by, lambda b: CheckBox(b, name, state=state), name)

    def label(
        self,
        by: By,
        name: str = "",
        state: StateSpec = ElementState.DISPLAYED,
    ) -> FormattableElement[Label, By]:
        return FormattableElement(by, lambda b: Label(b, name, state=state), name)

    def input(
        self,
        by: By,
        name: str = "",
        state: StateSpec = ElementState.DISPLAYED,
    ) -> FormattableElement[Input, By]:
        return FormattableElement(by, lambda b: Input(b, name, state=state), name)


class ElementFactory:
    """Создает типизированные элементы (Button/Input/CheckBox/Label/Element)."""

    @property
    def formattable(self) -> FormattableElementFactory:
        """Фабрика шаблонных элементов (локатор с `str.format`-placeholder'ами)."""
        return FormattableElementFactory()

    def element[E: Element](
        self,
        element_cls: type[E],
        by: By,
        name: str = "",
        state: StateSpec = ElementState.DISPLAYED,
    ) -> E:
        return element_cls(by, name, state=state)

    def button(
        self,
        by: By,
        name: str = "",
        state: StateSpec = ElementState.CLICKABLE,
    ) -> Button:
        return Button(by, name, state=state)

    def checkbox(
        self,
        by: By,
        name: str = "",
        state: StateSpec = ElementState.CLICKABLE,
    ) -> CheckBox:
        return CheckBox(by, name, state=state)

    def label(
        self,
        by: By,
        name: str = "",
        state: StateSpec = ElementState.DISPLAYED,
    ) -> Label:
        return Label(by, name, state=state)

    def input(
        self,
        by: By,
        name: str = "",
        state: StateSpec = ElementState.DISPLAYED,
    ) -> Input:
        return Input(by, name, state=state)

    def elements[E: Element](
        self,
        element_cls: type[E],
        by: By,
        name_prefix: str = "",
    ) -> LazyElements[E]:
        return LazyElements(element_cls, by, name_prefix)

    def buttons(self, by: By, name_prefix: str = "") -> LazyElements[Button]:
        return self.elements(Button, by, name_prefix)

    def checkboxes(self, by: By, name_prefix: str = "") -> LazyElements[CheckBox]:
        return self.elements(CheckBox, by, name_prefix)

    def labels(self, by: By, name_prefix: str = "") -> LazyElements[Label]:
        return self.elements(Label, by, name_prefix)

    def inputs(self, by: By, name_prefix: str = "") -> LazyElements[Input]:
        return self.elements(Input, by, name_prefix)

    def get_child_element[E: Element](
        self,
        element_cls: type[E],
        parent: Element,
        by: By,
        name: str = "",
        state: StateSpec = ElementState.DISPLAYED,
    ) -> E:
        return element_cls(LocatorUtils.join_xpath(parent.by, by), name, state=state)

    def get_child_button(
        self,
        parent: Element,
        by: By,
        name: str = "",
        state: StateSpec = ElementState.CLICKABLE,
    ) -> Button:
        return Button(LocatorUtils.join_xpath(parent.by, by), name, state=state)

    def get_child_checkbox(
        self,
        parent: Element,
        by: By,
        name: str = "",
        state: StateSpec = ElementState.CLICKABLE,
    ) -> CheckBox:
        return CheckBox(LocatorUtils.join_xpath(parent.by, by), name, state=state)

    def get_child_label(
        self,
        parent: Element,
        by: By,
        name: str = "",
        state: StateSpec = ElementState.DISPLAYED,
    ) -> Label:
        return Label(LocatorUtils.join_xpath(parent.by, by), name, state=state)

    def get_child_input(
        self,
        parent: Element,
        by: By,
        name: str = "",
        state: StateSpec = ElementState.DISPLAYED,
    ) -> Input:
        return Input(LocatorUtils.join_xpath(parent.by, by), name, state=state)

    def get_child_elements[E: Element](
        self,
        element_cls: type[E],
        parent: Element,
        by: By,
        name_prefix: str = "",
    ) -> LazyElements[E]:
        return LazyElements(element_cls, LocatorUtils.join_xpath(parent.by, by), name_prefix)

    def get_child_buttons(
        self,
        parent: Element,
        by: By,
        name_prefix: str = "",
    ) -> LazyElements[Button]:
        return self.get_child_elements(Button, parent, by, name_prefix)

    def get_child_checkboxes(
        self,
        parent: Element,
        by: By,
        name_prefix: str = "",
    ) -> LazyElements[CheckBox]:
        return self.get_child_elements(CheckBox, parent, by, name_prefix)

    def get_child_labels(
        self,
        parent: Element,
        by: By,
        name_prefix: str = "",
    ) -> LazyElements[Label]:
        return self.get_child_elements(Label, parent, by, name_prefix)

    def get_child_inputs(
        self,
        parent: Element,
        by: By,
        name_prefix: str = "",
    ) -> LazyElements[Input]:
        return self.get_child_elements(Input, parent, by, name_prefix)
