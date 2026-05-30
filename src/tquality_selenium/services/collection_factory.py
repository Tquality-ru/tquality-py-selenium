"""`CollectionFactory`: строит список Pydantic-моделей из DOM.

Каждое поле модели объявляется через `DomField.css(...)` или
`DomField.xpath(...)` - метаданные запекаются в `json_schema_extra` и
используются фабрикой для построения одного `execute_script`-запроса.

```python
from pydantic import BaseModel
from tquality_selenium import DomField, SeleniumServices, CollectionFactory

class Product(BaseModel):
    name: str = DomField.css(".title", attr="title")
    price: str = DomField.css(".price")

factory = SeleniumServices.get_service(CollectionFactory)
products = factory.from_page(Product, container_css=".product-card")
```
"""
from __future__ import annotations

from typing import Any, TypeVar, get_args, get_origin

from pydantic import BaseModel, Field
from selenium.webdriver.remote.webelement import WebElement

from tquality_selenium.elements.base_element import BaseElement
from tquality_selenium.elements.by import By
from tquality_selenium.elements.by_kind import ByKind
from tquality_selenium.services.pseudo_element import PseudoElement

T = TypeVar("T", bound=BaseModel)

_BY_KEY = "by"
_VALUE_KEY = "value"
_ATTR_KEY = "attr"
_STYLE_KEY = "style"
_PSEUDO_KEY = "pseudo"
_RAW_KEY = "raw"
_ELEMENT_TYPE_KEY = "element_type"


def _annotation_is_webelement(annotation: Any) -> bool:
    if annotation is WebElement:
        return True
    if get_origin(annotation) is not None:
        return any(arg is WebElement for arg in get_args(annotation))
    return False


def _annotation_base_element_type(annotation: Any) -> type[BaseElement] | None:
    candidates = (
        list(get_args(annotation)) if get_origin(annotation) is not None
        else [annotation]
    )
    for c in candidates:
        if isinstance(c, type) and issubclass(c, BaseElement):
            return c
    return None


class DomField:
    """Factory-методы для Pydantic-полей, наполняемых из DOM.

    Объединяет разные стратегии локаторов (CSS, XPath) под одной
    неймспейс-обёрткой - добавление новых стратегий не ломает импорты.
    """

    @staticmethod
    def css(selector: str, *, attr: str | None = None, **kwargs: Any) -> Any:
        """Поле, заполняемое `container.querySelector(selector)`.

        Аргументы:
            selector: CSS-селектор относительно элемента-контейнера.
            attr: DOM-атрибут; если None - берётся `textContent`.
            **kwargs: пробрасываются в `pydantic.Field`.
        """
        return DomField._build(ByKind.CSS_SELECTOR, selector, attr, **kwargs)

    @staticmethod
    def xpath(selector: str, *, attr: str | None = None, **kwargs: Any) -> Any:
        """Поле, заполняемое `document.evaluate(selector, container, ...)`.

        XPath вычисляется относительно элемента-контейнера через
        `document.evaluate` с `contextNode=el`.
        """
        return DomField._build(ByKind.XPATH, selector, attr, **kwargs)

    @staticmethod
    def css_style(
        selector: str,
        style_prop: str,
        *,
        pseudo: PseudoElement | None = None,
        **kwargs: Any,
    ) -> Any:
        """Computed-style readout: `getComputedStyle(el, pseudo).getPropertyValue(style_prop)`.

        Локатор - CSS. Для не-CSS-локатора используйте `xpath_style` (без
        `pseudo` - псевдо-элементы не находятся через XPath по определению).
        Сырое значение - строка (`"none"`, `"rgb(255,0,0)"`, `'url("x.svg")'`);
        для бизнес-логики оборачивайте поле в валидатор.
        """
        return DomField._build_style(
            ByKind.CSS_SELECTOR, selector, style_prop, pseudo, **kwargs,
        )

    @staticmethod
    def xpath_style(
        selector: str,
        style_prop: str,
        **kwargs: Any,
    ) -> Any:
        """То же, что `css_style`, но локатор - XPath; псевдо-элементы не поддерживаются."""
        return DomField._build_style(
            ByKind.XPATH, selector, style_prop, None, **kwargs,
        )

    @staticmethod
    def _build(
        by: str, value: str, attr: str | None, **kwargs: Any,
    ) -> Any:
        extra: dict[str, Any] = {_BY_KEY: by, _VALUE_KEY: value}
        if attr is not None:
            extra[_ATTR_KEY] = attr
        return Field(json_schema_extra=extra, **kwargs)

    @staticmethod
    def _build_style(
        by: str,
        value: str,
        style_prop: str,
        pseudo: PseudoElement | None,
        **kwargs: Any,
    ) -> Any:
        extra: dict[str, Any] = {
            _BY_KEY: by, _VALUE_KEY: value, _STYLE_KEY: style_prop,
        }
        if pseudo is not None:
            extra[_PSEUDO_KEY] = str(pseudo)
        return Field(json_schema_extra=extra, **kwargs)


class CollectionFactory:
    """Factory: создает список моделей из коллекции DOM-элементов."""

    @property
    def _driver(self) -> Any:
        from tquality_selenium.container import SeleniumServices
        from tquality_selenium.browser import BrowserService
        return SeleniumServices.get_service(BrowserService).driver

    @property
    def _log(self) -> Any:
        from tquality_core import Logger
        from tquality_selenium.container import SeleniumServices
        return SeleniumServices.get_service(Logger)

    def from_page(
        self,
        model: type[T],
        container_css: str,
    ) -> list[T]:
        """Вернуть список экземпляров `model` по одному на каждый элемент,
        подходящий под `container_css`."""
        field_map = self._extract_field_map(model)
        if not field_map:
            raise ValueError(
                f"У модели {model.__name__} нет полей с DomField-метаданными",
            )

        script = self._build_script(container_css, field_map)
        self._log.info(
            "CollectionFactory: extract %s from '%s'",
            model.__name__, container_css,
        )
        raw_items: list[dict[str, Any]] = self._driver.execute_script(script)
        self._populate_element_fields(
            raw_items, field_map, container_css, model.__name__,
        )
        return [model.model_validate(item) for item in raw_items]

    @staticmethod
    def _populate_element_fields(
        raw_items: list[dict[str, Any]],
        field_map: dict[str, dict[str, Any]],
        container_css: str,
        model_name: str,
    ) -> None:
        element_fields = {
            name: meta for name, meta in field_map.items()
            if _ELEMENT_TYPE_KEY in meta
        }
        if not element_fields:
            return
        container_xpath = By.css_selector(container_css).to_xpath()
        for i, item in enumerate(raw_items):
            row_xpath = f"({container_xpath})[{i + 1}]"
            for name, meta in element_fields.items():
                element_cls = meta[_ELEMENT_TYPE_KEY]
                field_by = By(ByKind(meta[_BY_KEY]), meta[_VALUE_KEY])
                joined = By.xpath(row_xpath + field_by.to_xpath())
                item[name] = element_cls(joined, f"{model_name}.{name}[{i}]")

    @staticmethod
    def _extract_field_map(
        model: type[BaseModel],
    ) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        for name, field_info in model.model_fields.items():
            extra = field_info.json_schema_extra
            if not isinstance(extra, dict) or _BY_KEY not in extra:
                continue
            by_value = extra[_BY_KEY]
            value_value = extra.get(_VALUE_KEY)
            if not (isinstance(by_value, str) and isinstance(value_value, str)):
                continue
            entry: dict[str, Any] = {
                _BY_KEY: by_value, _VALUE_KEY: value_value,
            }
            attr_value = extra.get(_ATTR_KEY)
            if isinstance(attr_value, str):
                entry[_ATTR_KEY] = attr_value
            style_value = extra.get(_STYLE_KEY)
            if isinstance(style_value, str):
                entry[_STYLE_KEY] = style_value
            pseudo_value = extra.get(_PSEUDO_KEY)
            if isinstance(pseudo_value, str):
                entry[_PSEUDO_KEY] = pseudo_value
            if _annotation_is_webelement(field_info.annotation):
                entry[_RAW_KEY] = True
            element_type = _annotation_base_element_type(field_info.annotation)
            if element_type is not None:
                entry[_ELEMENT_TYPE_KEY] = element_type
            result[name] = entry
        return result

    @staticmethod
    def _build_script(
        container_css: str,
        field_map: dict[str, dict[str, Any]],
    ) -> str:
        """Сгенерировать JS `[{field: value, ...}, ...]`."""
        field_lines: list[str] = []
        for name, meta in field_map.items():
            if _ELEMENT_TYPE_KEY in meta:
                continue
            by = meta[_BY_KEY]
            value = meta[_VALUE_KEY].replace("'", "\\'")
            attr = meta.get(_ATTR_KEY)
            style_prop = meta.get(_STYLE_KEY)
            pseudo = meta.get(_PSEUDO_KEY)
            raw = meta.get(_RAW_KEY, False)

            if by == ByKind.CSS_SELECTOR:
                selector_js = f"el.querySelector('{value}')"
            elif by == ByKind.XPATH:
                selector_js = (
                    f"document.evaluate('{value}', el, null, "
                    f"XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue"
                )
            else:
                raise ValueError(
                    f"Неподдерживаемая стратегия локатора для поля: {by!r}",
                )

            if raw:
                extract = (
                    f"        var _{name} = {selector_js};\n"
                    f"        item['{name}'] = _{name};"
                )
            elif style_prop is not None:
                style_escaped = style_prop.replace("'", "\\'")
                pseudo_arg = f"'{pseudo}'" if pseudo else "null"
                extract = (
                    f"        var _{name} = {selector_js};\n"
                    f"        item['{name}'] = _{name}"
                    f" ? window.getComputedStyle(_{name}, {pseudo_arg})"
                    f".getPropertyValue('{style_escaped}').trim() : '';"
                )
            elif attr is not None:
                attr_escaped = attr.replace("'", "\\'")
                extract = (
                    f"        var _{name} = {selector_js};\n"
                    f"        item['{name}'] = _{name}"
                    f" ? (_{name}.getAttribute('{attr_escaped}')"
                    f" || _{name}.textContent.trim()) : '';"
                )
            else:
                extract = (
                    f"        var _{name} = {selector_js};\n"
                    f"        item['{name}'] = _{name}"
                    f" ? _{name}.textContent.trim() : '';"
                )
            field_lines.append(extract)

        fields_js = "\n".join(field_lines)
        container_escaped = container_css.replace("'", "\\'")

        # language=js
        return f"""
        var containers = document.querySelectorAll('{container_escaped}');
        var result = [];
        for (var i = 0; i < containers.length; i++) {{
            var el = containers[i];
            var item = {{}};
{fields_js}
            result.push(item);
        }}
        return result;
        """


__all__ = ["CollectionFactory", "DomField"]
