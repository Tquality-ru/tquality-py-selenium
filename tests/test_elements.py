"""Тесты структуры элементов (без реального драйвера)."""
from __future__ import annotations

from tquality_selenium import BaseElement, Button, By, CheckBox, Input, Label


def test_base_element_default_name_uses_locator() -> None:
    el = BaseElement(By.id("submit"))
    assert "id" in el._name and "submit" in el._name


def test_base_element_custom_name() -> None:
    el = BaseElement(By.css_selector(".x"), "Элемент")
    assert el._name == "Элемент"


def test_button_has_submit_method() -> None:
    btn = Button(By.id("submit"))
    assert hasattr(btn, "submit") and callable(btn.submit)


def test_checkbox_has_toggle_methods() -> None:
    cb = CheckBox(By.id("agree"))
    for attr in ("check", "uncheck", "toggle"):
        assert hasattr(cb, attr) and callable(getattr(cb, attr))


def test_input_has_type_and_clear() -> None:
    inp = Input(By.id("q"))
    for attr in ("type_text", "clear", "append_text"):
        assert hasattr(inp, attr) and callable(getattr(inp, attr))


def test_label_is_base_element() -> None:
    label = Label(By.css_selector(".title"))
    assert isinstance(label, BaseElement)


def test_element_js_actions_is_bound() -> None:
    from tquality_selenium.services.js_actions import ElementJsActions

    btn = Button(By.id("submit"))
    assert isinstance(btn.js_actions, ElementJsActions)


def test_base_element_has_dismiss_if_visible_helper() -> None:
    el = BaseElement(By.css_selector(".cookies"))
    assert hasattr(el, "dismiss_if_visible") and callable(el.dismiss_if_visible)


def test_input_has_submit_text() -> None:
    inp = Input(By.id("price"))
    assert hasattr(inp, "submit_text") and callable(inp.submit_text)


def test_by_factories_produce_expected_pairs() -> None:
    assert By.id("x") == ("id", "x")
    assert By.xpath("//a") == ("xpath", "//a")
    assert By.css_selector(".y") == ("css selector", ".y")
    assert By.name("z") == ("name", "z")
    assert By.class_name("c") == ("class name", "c")
    assert By.tag_name("div") == ("tag name", "div")
    assert By.link_text("L") == ("link text", "L")
    assert By.partial_link_text("P") == ("partial link text", "P")


def test_by_unpacks_to_two_strings() -> None:
    by, value = By.id("submit")
    assert by == "id"
    assert value == "submit"
