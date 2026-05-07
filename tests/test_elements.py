"""Тесты структуры элементов (без реального драйвера)."""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from tquality_selenium import (
    BaseElement,
    Button,
    By,
    CheckBox,
    StyleProperty,
    ElementFactory,
    Input,
    Label,
    LazyElements,
)


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


def test_element_factory_elements_returns_sequence_without_touching_driver() -> None:
    # Должно безопасно конструироваться в __init__ POM (драйвер не настроен).
    factory = ElementFactory()
    collection = factory.elements(Button, By.xpath("//button"), "button")
    assert isinstance(collection, LazyElements)
    assert isinstance(collection, Sequence)


def test_element_factory_elements_indexing_is_lazy_and_names_items() -> None:
    factory = ElementFactory()
    collection = factory.elements(Button, By.xpath("//button"), "button")
    first = collection[0]
    third = collection[2]
    assert isinstance(first, Button)
    assert isinstance(third, Button)
    assert first._name == "button #1"
    assert third._name == "button #3"


def test_element_factory_elements_default_prefix_is_class_name() -> None:
    factory = ElementFactory()
    collection = factory.elements(Input, By.css_selector("input"))
    assert collection[0]._name == "Input #1"


def test_element_js_actions_has_computed_style_getters() -> None:
    btn = Button(By.id("submit"))
    for attr in ("get_computed_style", "get_computed_styles"):
        assert hasattr(btn.js_actions, attr) and callable(getattr(btn.js_actions, attr))


def test_get_computed_style_passes_property_name_to_driver() -> None:
    """Имя свойства уходит в execute_script вторым аргументом, ответ - str."""
    from unittest.mock import MagicMock, PropertyMock, patch

    from tquality_selenium.services.js_actions import ElementJsActions

    fake_driver = MagicMock()
    fake_driver.execute_script.return_value = "block"
    ja = ElementJsActions(find=MagicMock())

    with patch.object(
        ElementJsActions, "_driver", new_callable=PropertyMock,
    ) as drv, patch.object(
        ElementJsActions, "_log", new_callable=PropertyMock,
    ) as log:
        drv.return_value = fake_driver
        log.return_value = MagicMock()
        assert ja.get_computed_style("display") == "block"
        assert ja.get_computed_style(StyleProperty.DISPLAY) == "block"

    # StrEnum в JS уезжает как своё строковое значение - оба вызова видят "display".
    for call in fake_driver.execute_script.call_args_list:
        assert call.args[-1] == "display"


def test_get_computed_styles_returns_dict_str_str() -> None:
    """JS возвращает объект - получаем dict[str, str], типы приведены."""
    from unittest.mock import MagicMock, PropertyMock, patch

    from tquality_selenium.services.js_actions import ElementJsActions

    fake_driver = MagicMock()
    fake_driver.execute_script.return_value = {
        "display": "block", "opacity": "1", "z-index": "auto",
    }
    ja = ElementJsActions(find=MagicMock())

    with patch.object(
        ElementJsActions, "_driver", new_callable=PropertyMock,
    ) as drv, patch.object(
        ElementJsActions, "_log", new_callable=PropertyMock,
    ) as log:
        drv.return_value = fake_driver
        log.return_value = MagicMock()
        result = ja.get_computed_styles()

    assert result == {"display": "block", "opacity": "1", "z-index": "auto"}
    assert all(isinstance(k, str) and isinstance(v, str) for k, v in result.items())


def test_lazy_elements_iteration_caches_find_elements_within_one_pass() -> None:
    """Внутри одного цикла - один `find_elements`; элементы из snapshot'а."""
    from unittest.mock import PropertyMock, patch

    from tquality_selenium.services.lazy_elements import LazyElements

    call_count = 0

    class CountingBrowser:
        def find_elements(self, by: str, value: str) -> list[str]:
            nonlocal call_count
            call_count += 1
            return ["w0", "w1", "w2"]

    factory = ElementFactory()
    collection = factory.elements(Button, By.css_selector("button"), "btn")
    with patch.object(
        LazyElements, "_browser", new_callable=PropertyMock,
    ) as browser_prop:
        browser_prop.return_value = CountingBrowser()
        # Каждый _find() читает из snapshot'а, не из find_elements.
        resolved = [b._find() for b in collection]
    assert resolved == ["w0", "w1", "w2"]
    assert call_count == 1, f"ожидался 1 вызов find_elements, было {call_count}"


def test_lazy_elements_for_loop_uses_one_find_elements_call() -> None:
    """Классический `for` (не comprehension) - тоже один find_elements."""
    from unittest.mock import PropertyMock, patch

    from tquality_selenium.services.lazy_elements import LazyElements

    call_count = 0

    class CountingBrowser:
        def find_elements(self, by: str, value: str) -> list[str]:
            nonlocal call_count
            call_count += 1
            return ["w0", "w1", "w2"]

    factory = ElementFactory()
    collection = factory.elements(Button, By.css_selector("button"), "btn")
    resolved: list[Any] = []
    with patch.object(
        LazyElements, "_browser", new_callable=PropertyMock,
    ) as browser_prop:
        browser_prop.return_value = CountingBrowser()
        for btn in collection:
            # Имитация действия над элементом - каждое читает из snapshot'а.
            resolved.append(btn._find())

    assert resolved == ["w0", "w1", "w2"]
    assert call_count == 1, f"ожидался 1 вызов find_elements, было {call_count}"


def test_lazy_elements_to_list_uses_one_find_elements_call() -> None:
    """`to_list()` - один find_elements; последующие `_find()` из snapshot'а."""
    from unittest.mock import PropertyMock, patch

    from tquality_selenium.services.lazy_elements import LazyElements

    call_count = 0

    class CountingBrowser:
        def find_elements(self, by: str, value: str) -> list[str]:
            nonlocal call_count
            call_count += 1
            return ["w0", "w1", "w2"]

    factory = ElementFactory()
    collection = factory.elements(Button, By.css_selector("button"), "btn")
    with patch.object(
        LazyElements, "_browser", new_callable=PropertyMock,
    ) as browser_prop:
        browser_prop.return_value = CountingBrowser()
        items = collection.to_list()
        # Резолв всех элементов: snapshot уже снят, новых походов в DOM нет.
        resolved = [b._find() for b in items]

    assert len(items) == 3
    assert resolved == ["w0", "w1", "w2"]
    assert call_count == 1, f"ожидался 1 вызов find_elements, было {call_count}"


def test_lazy_elements_separate_iterations_re_fetch() -> None:
    """Между разными итерациями - свежий `find_elements`."""
    from unittest.mock import PropertyMock, patch

    from tquality_selenium.services.lazy_elements import LazyElements

    call_count = 0

    class CountingBrowser:
        def find_elements(self, by: str, value: str) -> list[str]:
            nonlocal call_count
            call_count += 1
            return [f"snapshot{call_count}_w{i}" for i in range(3)]

    factory = ElementFactory()
    collection = factory.elements(Button, By.css_selector("button"), "btn")
    with patch.object(
        LazyElements, "_browser", new_callable=PropertyMock,
    ) as browser_prop:
        browser_prop.return_value = CountingBrowser()
        first = [b._find() for b in collection]
        second = [b._find() for b in collection]
    # Каждая итерация получила свой snapshot - значит два вызова.
    assert call_count == 2
    assert first[0] == "snapshot1_w0"
    assert second[0] == "snapshot2_w0"


def test_lazy_elements_single_index_access_stays_live() -> None:
    """`collection[i]` (без snapshot) делает live-резолв при каждом действии."""
    from unittest.mock import PropertyMock, patch

    from tquality_selenium.services.lazy_elements import LazyElements

    call_count = 0

    class CountingBrowser:
        def find_elements(self, by: str, value: str) -> list[str]:
            nonlocal call_count
            call_count += 1
            return ["w0", "w1", "w2"]

    factory = ElementFactory()
    collection = factory.elements(Button, By.css_selector("button"), "btn")
    with patch.object(
        LazyElements, "_browser", new_callable=PropertyMock,
    ) as browser_prop:
        browser_prop.return_value = CountingBrowser()
        item = collection[1]  # индексный доступ - без snapshot'а
        item._find()
        item._find()
    # Один вызов - per-action find_elements: без len() (positive index)
    # сам __getitem__ не зовет find_elements; зовут только два _find().
    assert call_count == 2


def test_lazy_elements_to_list_resolves_eagerly() -> None:
    """`to_list` отдает list[E] длиной N с уже именованными элементами."""
    from unittest.mock import PropertyMock, patch

    from tquality_selenium.services.lazy_elements import LazyElements

    sentinels = ["w0", "w1", "w2"]

    class FakeBrowser:
        def find_elements(self, by: str, value: str) -> list[str]:
            return list(sentinels)

    factory = ElementFactory()
    collection = factory.elements(Button, By.css_selector("button"), "btn")
    with patch.object(
        LazyElements, "_browser", new_callable=PropertyMock,
    ) as browser_prop:
        browser_prop.return_value = FakeBrowser()
        result = collection.to_list()

    assert isinstance(result, list)
    assert len(result) == len(sentinels)
    assert all(isinstance(b, Button) for b in result)
    assert [b._name for b in result] == ["btn #1", "btn #2", "btn #3"]


def test_lazy_elements_indexed_finder_uses_find_elements_at_index() -> None:
    from unittest.mock import PropertyMock, patch

    from tquality_selenium.services.lazy_elements import LazyElements

    sentinels = ["w0", "w1", "w2"]

    class FakeBrowser:
        def find_elements(self, by: str, value: str) -> list[str]:
            return list(sentinels)

    factory = ElementFactory()
    collection = factory.elements(Button, By.css_selector("button"), "btn")
    item = collection[1]
    with patch.object(
        LazyElements, "_browser", new_callable=PropertyMock,
    ) as browser_prop:
        browser_prop.return_value = FakeBrowser()
        assert item._find() == "w1"
