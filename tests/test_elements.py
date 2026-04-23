"""Тесты базовой структуры элементов (без реального драйвера)."""
from __future__ import annotations

from typing import cast
from unittest.mock import MagicMock

from tquality_core import BaseElement as CoreBaseElement
from tquality_core import Locator

from tquality_selenium import BaseElement, Button, CheckBox, Input, Label
from tquality_selenium.browser import BrowserService


def _dummy_browser() -> BrowserService:
    return cast(BrowserService, MagicMock(spec=BrowserService))


def test_concrete_elements_inherit_from_core() -> None:
    for cls in (BaseElement, Button, CheckBox, Input, Label):
        assert issubclass(cls, CoreBaseElement)


def test_base_element_is_not_abstract() -> None:
    el = BaseElement(
        Locator("css selector", ".x"),
        "Элемент",
        browser_resolver=_dummy_browser,
    )
    assert el.name == "Элемент"
    assert el.locator == Locator("css selector", ".x")


def test_element_default_name_uses_locator() -> None:
    el = BaseElement(
        Locator("id", "submit"),
        browser_resolver=_dummy_browser,
    )
    assert "id=submit" in el.name


def test_button_has_submit_method() -> None:
    btn = Button(Locator("id", "submit"), browser_resolver=_dummy_browser)
    assert hasattr(btn, "submit")


def test_checkbox_has_toggle_methods() -> None:
    cb = CheckBox(Locator("id", "agree"), browser_resolver=_dummy_browser)
    assert hasattr(cb, "check")
    assert hasattr(cb, "uncheck")
    assert hasattr(cb, "toggle")


def test_input_has_type_and_clear() -> None:
    inp = Input(Locator("id", "q"), browser_resolver=_dummy_browser)
    assert hasattr(inp, "type_text")
    assert hasattr(inp, "clear")
    assert hasattr(inp, "append_text")


def test_label_is_readable() -> None:
    label = Label(Locator("css selector", ".title"), browser_resolver=_dummy_browser)
    assert isinstance(label, CoreBaseElement)
