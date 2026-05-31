"""Тесты `ShadowRootProxy`: lazy-резолв, stale-safe, nested chain.

Покрытие:
- `_find` дочернего элемента действительно идёт через `parent.shadow_root.find_element`;
- каждый вызов `_find` заново резолвит `parent_find` - stale-reference исключён;
- nested chain (`host.shadow_root.get_label(...).shadow_root.get_button(...)`)
  при `_find` финального элемента прогоняет всю цепочку;
- typed getter'ы возвращают конкретные типы (`Button`, `Input`, `Label`,
  `CheckBox`) + generic `get_element[E]` для пользовательских наследников.
"""
from __future__ import annotations

from unittest.mock import MagicMock

from tquality_selenium import BaseElement, Button, By, CheckBox, Input, Label
from tquality_selenium.elements.shadow_root_proxy import ShadowRootProxy


def _make_chain(depth: int) -> list[MagicMock]:
    """Соберёт цепочку моков: каждый уровень - WebElement с .shadow_root,
    у которого find_element возвращает следующий уровень. Возвращает
    список от хоста к листу - узлы сравниваются по идентичности (`is`).
    """
    nodes: list[MagicMock] = []
    for _ in range(depth):
        node = MagicMock()
        if nodes:
            nodes[-1].shadow_root.find_element.return_value = node
        nodes.append(node)
    return nodes


def test_get_element_routes_find_through_parent_shadow_root() -> None:
    host, child = _make_chain(2)
    proxy = ShadowRootProxy(parent_find=lambda: host)

    button = proxy.get_button(By.css_selector(".submit"))
    resolved = button._find()

    assert resolved is child
    host.shadow_root.find_element.assert_called_with(
        "css selector", ".submit",
    )


def test_each_find_call_re_resolves_parent_no_stale() -> None:
    """Каждый `_find()` дёргает `parent_find` заново - даже если хост
    «сменился» между вызовами, дочерний элемент возьмёт свежий resolve."""
    calls: list[MagicMock] = []

    def parent_find() -> MagicMock:
        host, _child = _make_chain(2)
        calls.append(host)
        return host

    proxy = ShadowRootProxy(parent_find=parent_find)
    label = proxy.get_label(By.css_selector(".name"))

    label._find()
    label._find()
    label._find()

    assert len(calls) == 3  # parent_find called per _find


def test_nested_shadow_chain_resolves_full_path() -> None:
    """`host.shadow_root.get_label(...).shadow_root.get_button(...)` -
    финальный `_find` проходит host -> shadow -> label -> shadow -> button."""
    host, mid, deep = _make_chain(3)

    outer_proxy = ShadowRootProxy(parent_find=lambda: host)
    middle = outer_proxy.get_label(By.css_selector(".mid"))
    # middle._find() -> host.shadow_root.find_element(".mid") -> mid
    inner_proxy = middle.shadow_root
    deep_button = inner_proxy.get_button(By.css_selector(".deep"))

    resolved = deep_button._find()
    assert resolved is deep
    # И первый, и второй уровни были спрошены за shadow_root + find_element:
    host.shadow_root.find_element.assert_called_with("css selector", ".mid")
    mid.shadow_root.find_element.assert_called_with("css selector", ".deep")


def test_typed_getters_return_correct_subclasses() -> None:
    host, _child = _make_chain(2)
    proxy = ShadowRootProxy(parent_find=lambda: host)

    assert isinstance(proxy.get_button(By.css_selector(".b")), Button)
    assert isinstance(proxy.get_input(By.css_selector(".i")), Input)
    assert isinstance(proxy.get_label(By.css_selector(".l")), Label)
    assert isinstance(proxy.get_checkbox(By.css_selector(".c")), CheckBox)


def test_generic_get_element_returns_passed_type() -> None:
    """Пользовательский подкласс `BaseElement` возвращается as-is через generic."""
    class MyCustom(BaseElement):
        pass

    host, child = _make_chain(2)
    proxy = ShadowRootProxy(parent_find=lambda: host)
    custom = proxy.get_element(MyCustom, By.css_selector(".x"))

    assert isinstance(custom, MyCustom)
    assert custom._find() is child


def test_base_element_shadow_root_property_returns_proxy() -> None:
    """`BaseElement.shadow_root` отдаёт `ShadowRootProxy`, не raw Selenium ShadowRoot."""
    el = BaseElement(By.css_selector(".host"))
    sr = el.shadow_root

    assert isinstance(sr, ShadowRootProxy)
