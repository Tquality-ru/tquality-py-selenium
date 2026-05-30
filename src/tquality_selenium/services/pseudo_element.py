from __future__ import annotations

from enum import StrEnum


class PseudoElement(StrEnum):
    BEFORE = "::before"
    AFTER = "::after"
    MARKER = "::marker"
    PLACEHOLDER = "::placeholder"
    FIRST_LINE = "::first-line"
    FIRST_LETTER = "::first-letter"
    SELECTION = "::selection"
    BACKDROP = "::backdrop"
