"""Тесты структуры элементов (без реального драйвера)."""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import pytest

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


@pytest.mark.parametrize(
    ("factory", "value", "expected"),
    [
        pytest.param(By.id, "x", ("id", "x"), id="id"),
        pytest.param(By.xpath, "//a", ("xpath", "//a"), id="xpath"),
        pytest.param(By.css_selector, ".y", ("css selector", ".y"), id="css_selector"),
        pytest.param(By.name, "z", ("name", "z"), id="name"),
        pytest.param(By.class_name, "c", ("class name", "c"), id="class_name"),
        pytest.param(By.tag_name, "div", ("tag name", "div"), id="tag_name"),
        pytest.param(By.link_text, "L", ("link text", "L"), id="link_text"),
        pytest.param(
            By.partial_link_text, "P", ("partial link text", "P"),
            id="partial_link_text",
        ),
    ],
)
def test_by_factories_produce_expected_pairs(
    factory: Any, value: str, expected: tuple[str, str],
) -> None:
    assert factory(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param(".", "", id="self-dot-empty"),
        pytest.param("./foo", "/foo", id="dot-slash-prefix"),
        pytest.param(".//foo[1]", "//foo[1]", id="dot-double-slash-prefix"),
        pytest.param(
            ".//div[@class='x']/span",
            "//div[@class='x']/span",
            id="dot-double-slash-with-predicate",
        ),
        pytest.param("foo", "/foo", id="bare-tag"),
        pytest.param("button[1]", "/button[1]", id="bare-tag-with-index"),
        pytest.param("/foo", "/foo", id="absolute-single-slash"),
        pytest.param("//foo", "//foo", id="absolute-double-slash"),
        pytest.param("/foo/bar[2]", "/foo/bar[2]", id="absolute-multi-step"),
    ],
)
def test_locator_utils_normalize_xpath(value: str, expected: str) -> None:
    from tquality_selenium import LocatorUtils

    assert LocatorUtils.normalize_xpath(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param(".//button", "//button", id="dot-double-slash"),
        pytest.param("./button", "/button", id="dot-slash"),
        pytest.param("button[1]", "/button[1]", id="bare-with-index"),
        pytest.param(".", "", id="self-empty"),
        pytest.param("//div", "//div", id="absolute"),
    ],
)
def test_by_xpath_to_xpath_normalizes_via_locator_utils(
    value: str, expected: str,
) -> None:
    """`to_xpath()` для XPATH использует `LocatorUtils.normalize_xpath`."""
    assert By.xpath(value).to_xpath() == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param("submit", "'submit'", id="no-quotes"),
        pytest.param("don't", '"don\'t"', id="apostrophe-only"),
        pytest.param(
            'a\'b"c', "concat('a', \"'\", 'b\"c')",
            id="both-quote-kinds",
        ),
    ],
)
def test_locator_utils_xpath_literal_quotes_safely(
    value: str, expected: str,
) -> None:
    from tquality_selenium import LocatorUtils

    assert LocatorUtils.xpath_literal(value) == expected


@pytest.mark.parametrize(
    ("by", "expected"),
    [
        pytest.param(
            By.id("don't"), '//*[@id="don\'t"]',
            id="id-with-apostrophe",
        ),
        pytest.param(
            By.name("a'b"), '//*[@name="a\'b"]',
            id="name-with-apostrophe",
        ),
        pytest.param(
            By.link_text("Don't click"), '//a[text()="Don\'t click"]',
            id="link-text-with-apostrophe",
        ),
        pytest.param(
            By.partial_link_text("don't"),
            '//a[contains(text(), "don\'t")]',
            id="partial-link-text-with-apostrophe",
        ),
    ],
)
def test_by_to_xpath_escapes_quotes_in_value(by: By, expected: str) -> None:
    """Значения с кавычками не должны ломать XPath."""
    assert by.to_xpath() == expected


def test_by_to_xpath_uses_concat_when_value_has_both_quote_kinds() -> None:
    # И `'`, и `"` - concat-форма (точная строка проверяется в xpath_literal).
    assert "concat(" in By.id('a\'b"c').to_xpath()


def test_by_class_name_to_xpath_escapes_quoted_value() -> None:
    """`class_name` тоже корректно квотит значение в `contains(...)`."""
    assert By.class_name("foo'bar").to_xpath() == (
        "//*[contains(concat(' ', normalize-space(@class), ' '), "
        '" foo\'bar ")]'
    )


def test_locator_utils_join_xpath_concatenates_via_to_xpath() -> None:
    """`LocatorUtils.join_xpath` склеивает несколько `By` через `to_xpath()`."""
    from tquality_selenium import LocatorUtils

    parent = By.id("x")
    child = By.css_selector("button")
    joined = LocatorUtils.join_xpath(parent, child)
    assert joined.by_kind.value == "xpath"
    assert joined.value == parent.to_xpath() + child.to_xpath()


@pytest.mark.parametrize(
    ("child_xpath", "expected"),
    [
        # Голый `button` без нормализации стал бы невалидным
        # `//*[@id='container']button`; нормализация добавляет `/`.
        pytest.param(
            "button", "//*[@id='container']/button",
            id="bare-tag-gets-leading-slash",
        ),
        # `.//foo` → `//foo`, конкатенация даёт descendant-релейшен.
        pytest.param(
            ".//span", "//*[@id='container']//span",
            id="dot-double-slash-becomes-descendant",
        ),
    ],
)
def test_locator_utils_join_xpath_normalizes_relative_child_xpath(
    child_xpath: str, expected: str,
) -> None:
    """Дочерний xpath без ведущего слэша / с `.//` корректно склеивается:
    `By.to_xpath()` уже нормализует значение для XPATH."""
    from tquality_selenium import LocatorUtils

    parent = By.id("container")
    assert LocatorUtils.join_xpath(parent, By.xpath(child_xpath)).value == expected


def test_locator_utils_join_xpath_supports_more_than_two_locators() -> None:
    from tquality_selenium import LocatorUtils

    grand = By.id("g")
    parent = By.css_selector(".p")
    child = By.xpath("a")
    joined = LocatorUtils.join_xpath(grand, parent, child)
    assert joined.value == grand.to_xpath() + parent.to_xpath() + child.to_xpath()


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


def test_base_element_by_and_name_properties_expose_locator_and_name() -> None:
    el = BaseElement(By.id("submit"), "Login")
    assert el.by == By.id("submit")
    assert el.name == "Login"


def test_element_factory_element_generic_returns_subclass_instance() -> None:
    """`element[E](Button, ...)` - инстанс именно `Button`, не `BaseElement`."""
    factory = ElementFactory()
    btn = factory.element(Button, By.id("submit"), "Submit")
    assert isinstance(btn, Button)
    assert btn.name == "Submit"


@pytest.mark.parametrize(
    ("method", "expected_cls"),
    [
        pytest.param("buttons", Button, id="buttons"),
        pytest.param("checkboxes", CheckBox, id="checkboxes"),
        pytest.param("labels", Label, id="labels"),
        pytest.param("inputs", Input, id="inputs"),
    ],
)
def test_element_factory_typed_collection_wrappers(
    method: str, expected_cls: type[BaseElement],
) -> None:
    """`factory.buttons/checkboxes/labels/inputs` - типизированные обёртки
    над `elements()` для конкретных классов."""
    factory = ElementFactory()
    collection = getattr(factory, method)(By.css_selector(".x"), "item")
    assert isinstance(collection, LazyElements)
    assert isinstance(collection[0], expected_cls)


def test_element_factory_get_child_element_joins_parent_locator_via_xpath() -> None:
    """`get_child_element` склеивает `parent.by + child.by` через
    `LocatorUtils.join_xpath` - результат XPATH-локатор."""
    factory = ElementFactory()
    parent = BaseElement(By.id("container"), "Container")
    child = factory.get_child_element(
        Button, parent, By.css_selector("button.primary"), "Primary",
    )
    assert isinstance(child, Button)
    assert child.name == "Primary"
    assert child.by.by_kind.value == "xpath"
    # `parent.to_xpath()` + `child.to_xpath()`
    assert child.by.value.startswith("//*[@id=")
    assert "button" in child.by.value


@pytest.mark.parametrize(
    ("method", "expected_cls"),
    [
        pytest.param("get_child_button", Button, id="button"),
        pytest.param("get_child_checkbox", CheckBox, id="checkbox"),
        pytest.param("get_child_label", Label, id="label"),
        pytest.param("get_child_input", Input, id="input"),
    ],
)
def test_element_factory_get_child_per_class_wrappers(
    method: str, expected_cls: type[BaseElement],
) -> None:
    factory = ElementFactory()
    parent = BaseElement(By.id("root"), "Root")
    child = getattr(factory, method)(parent, By.css_selector(".x"), "X")
    assert isinstance(child, expected_cls)
    assert child.by.by_kind.value == "xpath"


def test_element_factory_get_child_elements_joins_locator_and_returns_lazy() -> None:
    factory = ElementFactory()
    parent = BaseElement(By.id("container"), "Container")
    collection = factory.get_child_elements(
        Button, parent, By.css_selector("button"), "btn",
    )
    assert isinstance(collection, LazyElements)
    assert collection._by.by_kind.value == "xpath"
    assert collection._by.value.startswith("//*[@id=")
    assert isinstance(collection[0], Button)
    assert collection[0]._name == "btn #1"


@pytest.mark.parametrize(
    ("method", "expected_cls"),
    [
        pytest.param("get_child_buttons", Button, id="buttons"),
        pytest.param("get_child_checkboxes", CheckBox, id="checkboxes"),
        pytest.param("get_child_labels", Label, id="labels"),
        pytest.param("get_child_inputs", Input, id="inputs"),
    ],
)
def test_element_factory_get_child_collection_per_class_wrappers(
    method: str, expected_cls: type[BaseElement],
) -> None:
    factory = ElementFactory()
    parent = BaseElement(By.id("root"), "Root")
    collection = getattr(factory, method)(parent, By.css_selector(".x"), "item")
    assert isinstance(collection, LazyElements)
    assert isinstance(collection[0], expected_cls)


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


# ----------------- element.wait API -----------------


from tquality_selenium.services.waiter import Waiter as _Waiter  # noqa: E402


class _FakeWaiter(_Waiter):
    """Fake of `Waiter`: records calls, returns the value supplied per-call.

    Наследуется от `Waiter`, чтобы быть type-compatible с
    `ElementWaiter.__init__(waiter: Waiter, ...)`, но `Waiter.__init__`
    не вызывает - в фейке не нужны ни `SeleniumConfig`, ни DI.
    """

    def __init__(self, return_value: Any = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self._return_value = return_value

    def until(
        self,
        condition: Any,
        message: str = "",
        timeout: float | None = None,
    ) -> Any:
        self.calls.append(
            {"condition": condition, "message": message, "timeout": timeout},
        )
        return self._return_value


def test_element_wait_property_returns_bound_element_waiter() -> None:
    """`btn.wait` резолвит `Waiter` из DI и биндит сам элемент."""
    from unittest.mock import MagicMock, patch

    from tquality_selenium.container import SeleniumServices
    from tquality_selenium.services.element_waiter import ElementWaiter as EW

    btn = Button(By.id("submit"), "Submit")
    fake_waiter = MagicMock()
    with patch.object(SeleniumServices, "get_service", return_value=fake_waiter):
        w = btn.wait

    assert isinstance(w, EW)
    assert w._element is btn
    assert w._waiter is fake_waiter


def test_until_visible_delegates_to_waiter_and_returns_element() -> None:
    from tquality_selenium.services.element_waiter import ElementWaiter as EW

    btn = Button(By.id("submit"), "Submit")
    fake = _FakeWaiter()
    result = EW(fake, btn).until_visible(timeout=2.5)

    assert result is btn
    assert len(fake.calls) == 1
    call = fake.calls[0]
    assert call["timeout"] == 2.5
    assert "Submit" in call["message"]
    assert "to be visible" in call["message"]


def test_until_clickable_delegates_and_returns_element() -> None:
    from tquality_selenium.services.element_waiter import ElementWaiter as EW

    btn = Button(By.id("submit"), "Submit")
    fake = _FakeWaiter()
    result = EW(fake, btn).until_clickable()

    assert result is btn
    assert "to be clickable" in fake.calls[0]["message"]


def test_until_invisible_delegates_and_returns_element() -> None:
    from tquality_selenium.services.element_waiter import ElementWaiter as EW

    el = BaseElement(By.css_selector(".banner"), "Cookie banner")
    fake = _FakeWaiter(return_value=True)
    result = EW(fake, el).until_invisible(timeout=1.0)

    assert result is el
    assert "to be invisible" in fake.calls[0]["message"]
    assert "Cookie banner" in fake.calls[0]["message"]


def test_until_present_delegates_and_returns_element() -> None:
    from tquality_selenium.services.element_waiter import ElementWaiter as EW

    el = BaseElement(By.id("x"), "X")
    fake = _FakeWaiter()
    result = EW(fake, el).until_present()

    assert result is el
    assert "to be present" in fake.calls[0]["message"]


def test_until_not_present_invokes_find_elements_in_predicate() -> None:
    """Predicate `lambda d: not d.find_elements(*by)` - распаковывается локатор."""
    from unittest.mock import MagicMock

    from tquality_selenium.services.element_waiter import ElementWaiter as EW

    el = BaseElement(By.css_selector(".gone"), "Gone")
    fake = _FakeWaiter(return_value=True)
    result = EW(fake, el).until_not_present()

    assert result is el
    assert "to be not present" in fake.calls[0]["message"]

    captured_predicate = fake.calls[0]["condition"]
    fake_driver = MagicMock()
    fake_driver.find_elements.return_value = []
    assert captured_predicate(fake_driver) is True
    fake_driver.find_elements.assert_called_once_with("css selector", ".gone")


def test_wait_until_passes_element_into_user_condition() -> None:
    """`wait.until(cond, ...)` - cond получает сам элемент, не WebDriver."""
    from tquality_selenium.services.element_waiter import ElementWaiter as EW

    el = BaseElement(By.id("x"), "X")
    fake = _FakeWaiter()

    captured: list[Any] = []

    def user_cond(e: BaseElement) -> bool:
        captured.append(e)
        return True

    result = EW(fake, el).until(user_cond, timeout=0.5, message="be ready")

    assert result is el
    assert len(fake.calls) == 1
    assert fake.calls[0]["timeout"] == 0.5
    assert "be ready" in fake.calls[0]["message"]
    assert "X" in fake.calls[0]["message"]

    # Wrapper-кондишн дёргает user_cond с элементом, игнорируя driver.
    fake.calls[0]["condition"](object())
    assert captured == [el]


def test_wait_until_default_message_when_omitted() -> None:
    from tquality_selenium.services.element_waiter import ElementWaiter as EW

    el = BaseElement(By.id("x"), "X")
    fake = _FakeWaiter()
    EW(fake, el).until(lambda _e: True)

    assert "meet custom condition" in fake.calls[0]["message"]


def test_wait_for_computed_style_builds_message_and_uses_js_actions() -> None:
    from unittest.mock import MagicMock, PropertyMock, patch

    from tquality_selenium.services.element_waiter import ElementWaiter as EW

    btn = Button(By.id("submit"), "Submit")
    fake = _FakeWaiter()

    ja = MagicMock()
    ja.get_computed_style.return_value = "block"
    with patch.object(BaseElement, "js_actions", new_callable=PropertyMock) as prop:
        prop.return_value = ja
        result = EW(fake, btn).for_computed_style(
            StyleProperty.DISPLAY, "block", timeout=3.0,
        )
        # Triggering the captured wait condition - проверяем, что предикат
        # действительно дёргает get_computed_style и сравнивает с expected.
        assert fake.calls[0]["condition"](object()) is True

    assert result is btn
    assert len(fake.calls) == 1
    msg = fake.calls[0]["message"]
    assert "have computed style display equal to 'block'" in msg
    assert fake.calls[0]["timeout"] == 3.0
    ja.get_computed_style.assert_called_with(StyleProperty.DISPLAY)


def test_wait_chain_returns_subclass_for_subclass_elements() -> None:
    """Generics: `Button.wait.until_visible()` тип Button, не BaseElement."""
    from tquality_selenium.services.element_waiter import ElementWaiter as EW

    btn = Button(By.id("submit"), "Submit")
    fake = _FakeWaiter()
    result = EW(fake, btn).until_visible()
    # Runtime-проверка: тот же объект, того же класса.
    assert result is btn
    assert isinstance(result, Button)
