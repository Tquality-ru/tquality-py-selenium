"""`StyleProperty`: имена CSS-свойств для `ElementJsActions.get_computed_style`.

`StrEnum` совместим с `str` - значения уезжают в JS как обычные строки. Список
не исчерпывающий: `get_computed_style` принимает любое имя через `str`, enum
нужен только для удобного автокомплита часто запрашиваемых в тестах свойств.
"""
from __future__ import annotations

from enum import StrEnum


class StyleProperty(StrEnum):
    """Часто запрашиваемые в тестах CSS-свойства."""

    DISPLAY = "display"
    VISIBILITY = "visibility"
    OPACITY = "opacity"
    POINTER_EVENTS = "pointer-events"
    CURSOR = "cursor"
    COLOR = "color"
    BACKGROUND_COLOR = "background-color"
    FONT_SIZE = "font-size"
    FONT_WEIGHT = "font-weight"
    FONT_FAMILY = "font-family"
    TEXT_DECORATION = "text-decoration"
    WIDTH = "width"
    HEIGHT = "height"
    POSITION = "position"
    Z_INDEX = "z-index"


__all__ = ["StyleProperty"]
