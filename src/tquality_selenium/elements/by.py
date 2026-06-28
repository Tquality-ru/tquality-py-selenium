"""Локатор `By` для Selenium - подкласс ядрового `BaseBy`.

Все используемые стратегии - общие W3C (`id`, `xpath`, `name`, `class_name`,
`tag_name`, `css_selector`, `link_text`, `partial_link_text`) - наследуются
из `BaseBy`, поэтому здесь только `to_xpath()` (композиция дочерних
локаторов) и свойство `by_kind` (стратегия как `ByKind`).

`By` - подкласс `tuple[str, str]`, прозрачно распаковывается в `(str, str)`
для `WebDriver.find_element(by, value)` и подходит для selenium API,
ожидающего `(strategy, value)`-кортеж.

```python
from tquality_selenium import By

By.id("submit")          # By(by='id', value='submit')
By.xpath("//button[1]")  # By(by='xpath', value='//button[1]')
By.css_selector(".item") # By(by='css selector', value='.item')
```
"""
from __future__ import annotations

from cssselect import GenericTranslator
from tquality_core import BaseBy

from tquality_selenium.elements.by_kind import ByKind


class By(BaseBy):
    __slots__ = ()

    @property
    def by_kind(self) -> ByKind:
        """Стратегия как `ByKind` (производное от строкового `by`)."""
        return ByKind(self.by)

    def to_xpath(self) -> str:
        from tquality_core.utils.xpath_utils import XPathUtils

        lit = XPathUtils.literal
        match self.by_kind:
            case ByKind.ID:
                return f"//*[@id={lit(self.value)}]"
            case ByKind.XPATH:
                return XPathUtils.normalize(self.value)
            case ByKind.LINK_TEXT:
                return f"//a[text()={lit(self.value)}]"
            case ByKind.PARTIAL_LINK_TEXT:
                return f"//a[contains(text(), {lit(self.value)})]"
            case ByKind.NAME:
                return f"//*[@name={lit(self.value)}]"
            case ByKind.TAG_NAME:
                return f"//{self.value}"
            case ByKind.CLASS_NAME:
                return (
                    f"//*[contains(concat(' ', normalize-space(@class), ' '), "
                    f"{lit(f' {self.value} ')})]"
                )
            case ByKind.CSS_SELECTOR:
                return GenericTranslator().css_to_xpath(self.value, prefix="//")
            case _:
                raise ValueError(f"Unsupported by kind: {self.by_kind}")
