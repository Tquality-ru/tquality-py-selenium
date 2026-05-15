from enum import StrEnum


class ByKind(StrEnum):
    """Стратегии поиска элемента. Значения совпадают со строками,
    которые ожидает `WebDriver.find_element`."""

    ID = "id"
    XPATH = "xpath"
    LINK_TEXT = "link text"
    PARTIAL_LINK_TEXT = "partial link text"
    NAME = "name"
    TAG_NAME = "tag name"
    CLASS_NAME = "class name"
    CSS_SELECTOR = "css selector"
