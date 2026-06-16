"""Тесты `CollectionFactory`: типизированная сборка моделей из DOM.

JS-скрипт фабрики всегда возвращает строки (`textContent.trim()` или
`getAttribute(...)`), а превращение их в `int`/`float`/`bool`/...
делегируется `model_validate` - то есть стандартному Pydantic-pipeline'у.
Здесь проверяем, что:
- базовая coercion работает (str -> int/float/bool);
- пользовательские `@field_validator` (mode="before"/"after") и
  `Annotated[..., BeforeValidator/AfterValidator]` отрабатывают штатно;
- ошибки валидации действительно поднимаются как `ValidationError`.

Драйвер заменяется подклассом `CollectionFactory`, переопределяющим
`_driver`/`_log` - реальный браузер не нужен.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Annotated, Any, Callable, cast
from unittest.mock import MagicMock

import pytest
from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    ValidationError,
    field_validator,
)
from selenium.webdriver.remote.webelement import WebElement

from tquality_selenium import BaseElement, Button, ByKind
from tquality_selenium.services.collection_factory import (
    CollectionFactory,
    DomField,
)
from tquality_selenium.services.pseudo_element import PseudoElement

MakeFactory = Callable[[list[dict[str, Any]]], CollectionFactory]


def _last_script(factory: CollectionFactory) -> str:
    """Последний JS-скрипт, переданный в `execute_script` мок-драйвера."""
    execute = cast(MagicMock, factory._driver.execute_script)
    (script,), _ = execute.call_args
    return cast(str, script)


# --- встроенная Pydantic coercion -------------------------------------------


def test_str_values_coerced_to_declared_scalar_types(
    make_collection_factory: MakeFactory,
) -> None:
    """`int`/`float`/`bool` поля заполняются из строк через Pydantic-coercion."""
    class Product(BaseModel):
        name: str = DomField.css(".title")
        price: int = DomField.css(".price")
        rating: float = DomField.css(".rating")
        in_stock: bool = DomField.css(".in-stock")

    factory = make_collection_factory([
        {"name": "Widget", "price": "42", "rating": "4.5", "in_stock": "true"},
        {"name": "Gadget", "price": "100", "rating": "3.2", "in_stock": "false"},
    ])

    result = factory.from_page(Product, ".product-card")

    assert result == [
        Product(name="Widget", price=42, rating=4.5, in_stock=True),
        Product(name="Gadget", price=100, rating=3.2, in_stock=False),
    ]
    assert isinstance(result[0].price, int)
    assert isinstance(result[0].rating, float)
    assert isinstance(result[0].in_stock, bool)


def test_empty_string_for_int_field_raises_validation_error(
    make_collection_factory: MakeFactory,
) -> None:
    """Без кастомного валидатора пустая строка из `textContent` ломает `int`."""
    class Product(BaseModel):
        price: int = DomField.css(".price")

    factory = make_collection_factory([{"price": ""}])

    with pytest.raises(ValidationError):
        factory.from_page(Product, ".product-card")


# --- field_validator(mode="before") -----------------------------------------


def test_before_field_validator_sanitizes_raw_string(
    make_collection_factory: MakeFactory,
) -> None:
    """`mode="before"` чистит сырой ввод до Pydantic-coercion в `int`."""
    class Product(BaseModel):
        price: int = DomField.css(".price")

        @field_validator("price", mode="before")
        @classmethod
        def _strip_currency(cls, v: Any) -> Any:
            if isinstance(v, str):
                return v.strip().lstrip("$€₽").replace(",", "")
            return v

    factory = make_collection_factory([
        {"price": " $1,299 "},
        {"price": "€42"},
    ])

    result = factory.from_page(Product, ".product-card")

    assert [p.price for p in result] == [1299, 42]


def test_before_field_validator_maps_empty_string_to_none(
    make_collection_factory: MakeFactory,
) -> None:
    """Типичный шаблон: пустой `textContent` -> `None` для `Optional` поля."""
    class Product(BaseModel):
        price: int | None = DomField.css(".price")

        @field_validator("price", mode="before")
        @classmethod
        def _empty_to_none(cls, v: Any) -> Any:
            if isinstance(v, str) and not v.strip():
                return None
            return v

    factory = make_collection_factory([{"price": "42"}, {"price": ""}])

    result = factory.from_page(Product, ".product-card")

    assert [p.price for p in result] == [42, None]


# --- field_validator(mode="after") ------------------------------------------


def test_after_field_validator_runs_post_coercion(
    make_collection_factory: MakeFactory,
) -> None:
    """`mode="after"` получает уже типизированное значение - удобно для range-check."""
    class Product(BaseModel):
        rating: float = DomField.css(".rating")

        @field_validator("rating", mode="after")
        @classmethod
        def _within_range(cls, v: float) -> float:
            if not 0.0 <= v <= 5.0:
                raise ValueError(f"rating {v} вне диапазона 0..5")
            return v

    ok = make_collection_factory([{"rating": "4.5"}])
    assert ok.from_page(Product, ".card")[0].rating == 4.5

    bad = make_collection_factory([{"rating": "9.9"}])
    with pytest.raises(ValidationError) as exc:
        bad.from_page(Product, ".card")
    assert "вне диапазона" in str(exc.value)


# --- Annotated + BeforeValidator / AfterValidator ---------------------------


def _clean_price(v: Any) -> Any:
    if isinstance(v, str):
        return v.strip().lstrip("$€₽").replace(",", "").replace(" ", "")
    return v


Price = Annotated[int, BeforeValidator(_clean_price)]


def test_annotated_before_validator_is_reusable_across_fields(
    make_collection_factory: MakeFactory,
) -> None:
    """Один `Annotated[..., BeforeValidator]` применяется к нескольким полям."""
    class Product(BaseModel):
        price: Price = DomField.css(".price")
        discounted: Price = DomField.css(".discounted")

    factory = make_collection_factory([
        {"price": "$1,299", "discounted": " 999 "},
    ])

    [item] = factory.from_page(Product, ".card")

    assert item.price == 1299
    assert item.discounted == 999


def _must_be_positive(v: int) -> int:
    if v <= 0:
        raise ValueError(f"ожидалось положительное число, получено {v}")
    return v


PositiveInt = Annotated[int, AfterValidator(_must_be_positive)]


def test_annotated_after_validator_enforces_post_coercion_invariant(
    make_collection_factory: MakeFactory,
) -> None:
    """`AfterValidator` получает уже сконвертированное число."""
    class Product(BaseModel):
        qty: PositiveInt = DomField.css(".qty")

    ok = make_collection_factory([{"qty": "5"}])
    assert ok.from_page(Product, ".card")[0].qty == 5

    bad = make_collection_factory([{"qty": "0"}])
    with pytest.raises(ValidationError) as exc:
        bad.from_page(Product, ".card")
    assert "положительное" in str(exc.value)


def test_annotated_chain_runs_before_then_after(
    make_collection_factory: MakeFactory,
) -> None:
    """`Annotated[T, BeforeValidator(a), AfterValidator(b)]` - оба применяются.

    Цепочка: сырая строка -> `_clean_price` -> Pydantic int-coercion ->
    `_must_be_positive`. Падение на любом этапе превращается в `ValidationError`.
    """
    type SanitizedPositive = Annotated[
        int,
        BeforeValidator(_clean_price),
        AfterValidator(_must_be_positive),
    ]

    class Product(BaseModel):
        qty: SanitizedPositive = DomField.css(".qty")

    ok = make_collection_factory([{"qty": "$1,299"}])
    assert ok.from_page(Product, ".card")[0].qty == 1299

    bad = make_collection_factory([{"qty": "$0"}])
    with pytest.raises(ValidationError) as exc:
        bad.from_page(Product, ".card")
    assert "положительное" in str(exc.value)


def test_annotated_before_validator_handles_decimal_separator(
    make_collection_factory: MakeFactory,
) -> None:
    """Локализованные числа (`"1,5"`) -> `Decimal` через `BeforeValidator`."""
    def _comma_to_dot(v: Any) -> Any:
        if isinstance(v, str):
            return v.strip().replace(",", ".")
        return v

    type LocaleDecimal = Annotated[Decimal, BeforeValidator(_comma_to_dot)]

    class Product(BaseModel):
        rating: LocaleDecimal = DomField.css(".rating")

    factory = make_collection_factory([{"rating": "4,5"}, {"rating": "3,14"}])

    result = factory.from_page(Product, ".card")

    assert [p.rating for p in result] == [Decimal("4.5"), Decimal("3.14")]


# --- attribute fetch -------------------------------------------------------


def test_css_attr_emits_getattribute_with_text_fallback(
    make_collection_factory: MakeFactory,
) -> None:
    """`DomField.css(..., attr=X)` -> `getAttribute(X) || textContent.trim()`.

    Контрольный тест на форму генерируемого JS: если кто-то рефакторит
    `_build_script` и теряет fallback на `textContent` - тест падает.
    """
    class Product(BaseModel):
        title: str = DomField.css(".name", attr="data-title")

    factory = make_collection_factory([{"title": "X"}])
    factory.from_page(Product, ".card")

    script = _last_script(factory)
    assert "el.querySelector('.name')" in script
    assert "getAttribute('data-title')" in script
    assert "textContent.trim()" in script


def test_xpath_attr_emits_getattribute_with_text_fallback(
    make_collection_factory: MakeFactory,
) -> None:
    """То же для XPath: `document.evaluate(...).singleNodeValue` + fallback."""
    class Product(BaseModel):
        href: str = DomField.xpath(".//a", attr="href")

    factory = make_collection_factory([{"href": "/p/1"}])
    factory.from_page(Product, ".card")

    script = _last_script(factory)
    assert "document.evaluate('.//a'" in script
    assert "singleNodeValue" in script
    assert "getAttribute('href')" in script
    assert "textContent.trim()" in script


def test_attr_value_flows_through_into_typed_field(
    make_collection_factory: MakeFactory,
) -> None:
    """Значение, приехавшее из `getAttribute`, проходит coercion в `int`."""
    class Product(BaseModel):
        product_id: int = DomField.css(".name", attr="data-id")

    factory = make_collection_factory([
        {"product_id": "42"},
        {"product_id": "100"},
    ])

    result = factory.from_page(Product, ".card")

    assert [p.product_id for p in result] == [42, 100]


def test_attr_with_quote_in_name_is_escaped_in_script(
    make_collection_factory: MakeFactory,
) -> None:
    """Имя атрибута с `'` экранируется - JS остаётся валидным."""
    class Product(BaseModel):
        x: str = DomField.css(".name", attr="data-it's")

    factory = make_collection_factory([{"x": "y"}])
    factory.from_page(Product, ".card")

    script = _last_script(factory)
    assert "getAttribute('data-it\\'s')" in script


def test_field_without_attr_uses_text_content_only(
    make_collection_factory: MakeFactory,
) -> None:
    """Без `attr=` в JS не должно быть `getAttribute`."""
    class Product(BaseModel):
        name: str = DomField.css(".title")

    factory = make_collection_factory([{"name": "Widget"}])
    factory.from_page(Product, ".card")

    script = _last_script(factory)
    assert "getAttribute" not in script
    assert "textContent.trim()" in script


# --- computed style readouts -----------------------------------------------


def test_css_style_emits_get_computed_style_with_null_pseudo(
    make_collection_factory: MakeFactory,
) -> None:
    """`css_style` без `pseudo=` -> `getComputedStyle(el, null).getPropertyValue(...)`."""
    class Card(BaseModel):
        bg: str = DomField.css_style(".thumb", "background-color")

    factory = make_collection_factory([{"bg": "rgb(0, 0, 0)"}])
    factory.from_page(Card, ".card")

    script = _last_script(factory)
    assert "el.querySelector('.thumb')" in script
    assert "window.getComputedStyle(_bg, null)" in script
    assert "getPropertyValue('background-color')" in script
    assert "getAttribute" not in script
    assert "textContent" not in script


def test_css_style_with_pseudo_emits_pseudo_arg(
    make_collection_factory: MakeFactory,
) -> None:
    """`pseudo=PseudoElement.BEFORE` подставляется вторым аргументом."""
    class Card(BaseModel):
        content: str = DomField.css_style(
            ".cb", "content", pseudo=PseudoElement.BEFORE,
        )

    factory = make_collection_factory([{"content": '"✓"'}])
    factory.from_page(Card, ".card")

    script = _last_script(factory)
    assert "window.getComputedStyle(_content, '::before')" in script
    assert "getPropertyValue('content')" in script


def test_xpath_style_emits_evaluate_and_get_computed_style(
    make_collection_factory: MakeFactory,
) -> None:
    """`xpath_style` использует `document.evaluate` + `getComputedStyle`."""
    class Card(BaseModel):
        display: str = DomField.xpath_style(".//div", "display")

    factory = make_collection_factory([{"display": "none"}])
    factory.from_page(Card, ".card")

    script = _last_script(factory)
    assert "document.evaluate('.//div'" in script
    assert "singleNodeValue" in script
    assert "window.getComputedStyle(_display, null)" in script
    assert "getPropertyValue('display')" in script


def test_style_value_flows_through_before_validator(
    make_collection_factory: MakeFactory,
) -> None:
    """Сырой computed-style оборачивается валидатором в бизнес-bool."""
    def _is_visible(v: Any) -> bool:
        return v not in ("", "none", "hidden")

    type Visible = Annotated[bool, BeforeValidator(_is_visible)]

    class Card(BaseModel):
        visible: Visible = DomField.css_style(".badge", "display")

    factory = make_collection_factory([
        {"visible": "block"},
        {"visible": "none"},
        {"visible": ""},
    ])

    result = factory.from_page(Card, ".card")

    assert [c.visible for c in result] == [True, False, False]


def test_style_missing_element_returns_empty_string(
    make_collection_factory: MakeFactory,
) -> None:
    """JS-шаблон сохраняет `_el ? ... : ''` fallback и для style-чтения."""
    class Card(BaseModel):
        bg: str = DomField.css_style(".missing", "background-color")

    factory = make_collection_factory([{"bg": ""}])
    factory.from_page(Card, ".card")

    script = _last_script(factory)
    assert "_bg ? window.getComputedStyle" in script
    assert ": ''" in script


# --- raw WebElement field --------------------------------------------------


def test_webelement_typed_field_receives_raw_element(
    make_collection_factory: MakeFactory,
) -> None:
    """Аннотация `WebElement` -> поле получает сам элемент, без `.textContent`.

    Редкий кейс: модель хранит ссылку на DOM-узел для быстрых POM-действий
    (clicks, submits) сразу после `from_page`. Подходит только для
    short-lived инстансов - элемент устаревает при перерисовке DOM.
    """
    class Card(BaseModel):
        model_config = ConfigDict(arbitrary_types_allowed=True)
        button: WebElement = DomField.css(".btn")

    fake_button = MagicMock(spec=WebElement)
    factory = make_collection_factory([{"button": fake_button}])

    [item] = factory.from_page(Card, ".card")

    assert item.button is fake_button

    script = _last_script(factory)
    assert "el.querySelector('.btn')" in script
    assert "item['button'] = _button;" in script
    assert "textContent" not in script
    assert "getAttribute" not in script


# --- BaseElement-typed field (lazy, scoped to row) --------------------------


def test_base_element_subclass_typed_field_is_built_with_row_scoped_locator(
    make_collection_factory: MakeFactory,
) -> None:
    """Поле типа `Button` (или другого BaseElement-наследника) собирается
    лениво: фабрика склеивает XPath контейнера-строки + локатора поля через
    `LocatorUtils.join_xpath`, ничего не вытаскивая из JS.
    """
    class Row(BaseModel):
        model_config = ConfigDict(arbitrary_types_allowed=True)
        action: Button = DomField.css(".btn")

    factory = make_collection_factory([{}, {}, {}])

    rows = factory.from_page(Row, ".product-card")

    assert len(rows) == 3
    assert all(isinstance(r.action, Button) for r in rows)
    assert all(r.action.by.by_kind is ByKind.XPATH for r in rows)

    locators = [r.action.by.value for r in rows]
    assert locators[0] != locators[1] != locators[2]
    assert "[1]" in locators[0]
    assert "[2]" in locators[1]
    assert "[3]" in locators[2]

    script = _last_script(factory)
    assert "querySelectorAll('.product-card')" in script
    assert "item['action']" not in script
    assert "var _action" not in script


def test_base_element_field_does_not_pollute_other_fields(
    make_collection_factory: MakeFactory,
) -> None:
    """BaseElement-поле сосуществует с обычными текст/attr-полями."""
    class Row(BaseModel):
        model_config = ConfigDict(arbitrary_types_allowed=True)
        title: str = DomField.css(".name")
        action: Button = DomField.css(".btn")

    factory = make_collection_factory([
        {"title": "Widget"}, {"title": "Gadget"},
    ])

    rows = factory.from_page(Row, ".card")

    assert [r.title for r in rows] == ["Widget", "Gadget"]
    assert all(isinstance(r.action, Button) for r in rows)

    script = _last_script(factory)
    assert "var _title" in script
    assert "var _action" not in script


def test_bare_base_element_annotation_is_also_supported(
    make_collection_factory: MakeFactory,
) -> None:
    """`BaseElement` сам по себе (не подкласс) тоже допустим."""
    class Row(BaseModel):
        model_config = ConfigDict(arbitrary_types_allowed=True)
        any_el: BaseElement = DomField.xpath(".//span")

    factory = make_collection_factory([{}])

    [row] = factory.from_page(Row, ".card")

    assert isinstance(row.any_el, BaseElement)
    assert row.any_el.by.by_kind is ByKind.XPATH


@pytest.mark.parametrize(
    ("raw_xpath", "expected_tail"),
    [
        pytest.param(".//button", "]//button", id="dot-slash-slash"),
        pytest.param("./button", "]/button", id="dot-slash"),
        pytest.param("//button", "]//button", id="absolute"),
    ],
)
def test_dot_prefixed_xpath_joins_correctly_against_row(
    make_collection_factory: MakeFactory, raw_xpath: str, expected_tail: str,
) -> None:
    """`./...` и `.//...` приводятся к относительному виду через `to_xpath()`,
    так что после склейки получается корректный `(row)[N]//...`/`(row)[N]/...`
    без лишней точки между ними.
    """
    class Row(BaseModel):
        model_config = ConfigDict(arbitrary_types_allowed=True)
        action: Button = DomField.xpath(raw_xpath)

    factory = make_collection_factory([{}])
    [row] = factory.from_page(Row, ".card")

    locator = row.action.by.value
    assert locator.endswith(expected_tail)
    assert "]." not in locator
