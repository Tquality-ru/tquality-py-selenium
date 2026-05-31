"""Геометрия элемента: rect / size / location как `NamedTuple`-ы.

Selenium возвращает `{'x', 'y', 'width', 'height'}` как `dict[str, Any]`,
что неудобно: нет автокомплита, опечатка в ключе не падает на проверке
типов. Оборачиваем в `NamedTuple` - immutable, typed, всё ещё совместимо
с tuple-unpack'ом (`x, y, w, h = element.rect`).

Поля - `float`, потому что некоторые браузеры (Firefox) возвращают
sub-pixel-позиции для DPR > 1.
"""
from __future__ import annotations

from typing import NamedTuple


class ElementSize(NamedTuple):
    """Размеры элемента в CSS-пикселях."""

    width: float
    height: float


class ElementLocation(NamedTuple):
    """Верхний левый угол элемента в координатах вьюпорта."""

    x: float
    y: float


class ElementRect(NamedTuple):
    """Положение + размеры элемента в координатах вьюпорта."""

    x: float
    y: float
    width: float
    height: float


__all__ = ["ElementLocation", "ElementRect", "ElementSize"]
