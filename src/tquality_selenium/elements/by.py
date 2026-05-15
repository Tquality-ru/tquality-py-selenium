"""Локатор: пара `(стратегия, значение)`.

`By` - это `NamedTuple` `(by_kind, value)`, где `by_kind` - инстанс enum
`ByKind`. Поскольку `ByKind` наследуется от `str`, `By` прозрачно
распаковывается в `(str, str)` для `WebDriver.find_element(by, value)`.

Конструируется через классовые методы по имени стратегии:

```python
from tquality_selenium import By

By.id("submit") # By(by_kind=ByKind.ID, value="submit")
By.xpath("//button[1]") # By(by_kind=ByKind.XPATH, value="//button[1]")
By.css_selector(".item") # By(by_kind=ByKind.CSS_SELECTOR, value=".item")
```
"""
from __future__ import annotations

from typing import NamedTuple

from cssselect import GenericTranslator

from tquality_selenium.elements.by_kind import ByKind


class By(NamedTuple):
    by_kind: ByKind
    value: str

    def to_xpath(self) -> str:
        # Локально, чтобы не было цикла: `locator_utils` импортирует `By`.
        from tquality_selenium.utils.locator_utils import LocatorUtils

        lit = LocatorUtils.xpath_literal
        match self.by_kind:
            case ByKind.ID:
                return f"//*[@id={lit(self.value)}]"
            case ByKind.XPATH:
                return LocatorUtils.normalize_xpath(self.value)
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

    @classmethod
    def id(cls, value: str) -> By:
        return cls(ByKind.ID, value)

    @classmethod
    def xpath(cls, value: str) -> By:
        return cls(ByKind.XPATH, value)

    @classmethod
    def link_text(cls, value: str) -> By:
        return cls(ByKind.LINK_TEXT, value)

    @classmethod
    def partial_link_text(cls, value: str) -> By:
        return cls(ByKind.PARTIAL_LINK_TEXT, value)

    @classmethod
    def name(cls, value: str) -> By:
        return cls(ByKind.NAME, value)

    @classmethod
    def tag_name(cls, value: str) -> By:
        return cls(ByKind.TAG_NAME, value)

    @classmethod
    def class_name(cls, value: str) -> By:
        return cls(ByKind.CLASS_NAME, value)

    @classmethod
    def css_selector(cls, value: str) -> By:
        return cls(ByKind.CSS_SELECTOR, value)
