"""Локатор: пара ``(стратегия, значение)``.

`By` - это `NamedTuple` `(by, value)`, где `by` - инстанс enum `ByKind`.
Поскольку `ByKind` наследуется от `str`, `By` прозрачно распаковывается
в `(str, str)` для `WebDriver.find_element(by, value)`.

Конструируется через классовые методы по имени стратегии:

```python
from tquality_selenium import By

By.id("submit") # By(by=ByKind.ID, value="submit")
By.xpath("//button[1]") # By(by=ByKind.XPATH, value="//button[1]")
By.css_selector(".item") # By(by=ByKind.CSS_SELECTOR, value=".item")
```
"""
from __future__ import annotations

from enum import StrEnum
from typing import NamedTuple


class ByKind(StrEnum):
    """Стратегии поиска элемента. Значения совпадают со строками,
    которые ожидает selenium-овский ``WebDriver.find_element``."""

    ID = "id"
    XPATH = "xpath"
    LINK_TEXT = "link text"
    PARTIAL_LINK_TEXT = "partial link text"
    NAME = "name"
    TAG_NAME = "tag name"
    CLASS_NAME = "class name"
    CSS_SELECTOR = "css selector"


class By(NamedTuple):
    by: ByKind
    value: str

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
