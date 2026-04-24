"""Тесты структуры элементов (без реального драйвера)."""
from __future__ import annotations

from selenium.webdriver.common.by import By

from tquality_selenium import BaseElement, Button, CheckBox, Input, Label


def test_base_element_default_name_uses_locator() -> None:
    el = BaseElement(By.ID, "submit")
    assert "id" in el._name and "submit" in el._name


def test_base_element_custom_name() -> None:
    el = BaseElement(By.CSS_SELECTOR, ".x", "Элемент")
    assert el._name == "Элемент"


def test_button_has_submit_method() -> None:
    btn = Button(By.ID, "submit")
    assert hasattr(btn, "submit") and callable(btn.submit)


def test_checkbox_has_toggle_methods() -> None:
    cb = CheckBox(By.ID, "agree")
    for attr in ("check", "uncheck", "toggle"):
        assert hasattr(cb, attr) and callable(getattr(cb, attr))


def test_input_has_type_and_clear() -> None:
    inp = Input(By.ID, "q")
    for attr in ("type_text", "clear", "append_text"):
        assert hasattr(inp, attr) and callable(getattr(inp, attr))


def test_label_is_base_element() -> None:
    label = Label(By.CSS_SELECTOR, ".title")
    assert isinstance(label, BaseElement)


def test_element_js_actions_is_bound() -> None:
    from tquality_selenium.services.js_actions import ElementJsActions

    btn = Button(By.ID, "submit")
    assert isinstance(btn.js_actions, ElementJsActions)


def test_base_element_has_dismiss_if_visible_helper() -> None:
    el = BaseElement(By.CSS_SELECTOR, ".cookies")
    assert hasattr(el, "dismiss_if_visible") and callable(el.dismiss_if_visible)


def test_input_has_submit_text() -> None:
    inp = Input(By.ID, "price")
    assert hasattr(inp, "submit_text") and callable(inp.submit_text)
