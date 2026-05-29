"""Реэкспорт core-`ElementState` ради устойчивого пути импорта.

Сама семантика и enum-значения - в `tquality_core.elements.element_state`;
платформенный `BaseElement._await_state(...)` дальше мапит state на
соответствующий `wait.until_*`.
"""
from tquality_core import ElementState, StatePredicate, StateSpec

__all__ = ["ElementState", "StatePredicate", "StateSpec"]
