"""`CollectionFactory`: строит список Pydantic-моделей из DOM.

Каждое поле модели объявляется через `DomField.css(...)` или
`DomField.xpath(...)` - метаданные запекаются в `json_schema_extra` и
используются фабрикой для построения одного `execute_script`-запроса.

```python
from pydantic import BaseModel
from selenium.webdriver.common.by import By
from tquality_selenium import DomField, SeleniumServices, CollectionFactory

class Product(BaseModel):
    name: str = DomField.css(".title", attr="title")
    price: str = DomField.css(".price")

factory = SeleniumServices.get_service(CollectionFactory)
products = factory.from_page(Product, container_css=".product-card")
```
"""
from __future__ import annotations

from typing import Any, TypeVar

from pydantic import BaseModel, Field
from selenium.webdriver.common.by import By

T = TypeVar("T", bound=BaseModel)

# Ключи метаданных в json_schema_extra.
_BY_KEY = "by"
_VALUE_KEY = "value"
_ATTR_KEY = "attr"


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
        return DomField._build(By.CSS_SELECTOR, selector, attr, **kwargs)

    @staticmethod
    def xpath(selector: str, *, attr: str | None = None, **kwargs: Any) -> Any:
        """Поле, заполняемое `document.evaluate(selector, container, ...)`.

        XPath вычисляется относительно элемента-контейнера через
        `document.evaluate` с `contextNode=el`.
        """
        return DomField._build(By.XPATH, selector, attr, **kwargs)

    @staticmethod
    def _build(
        by: str, value: str, attr: str | None, **kwargs: Any,
    ) -> Any:
        extra: dict[str, Any] = {_BY_KEY: by, _VALUE_KEY: value}
        if attr is not None:
            extra[_ATTR_KEY] = attr
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
        return [model.model_validate(item) for item in raw_items]

    @staticmethod
    def _extract_field_map(
        model: type[BaseModel],
    ) -> dict[str, dict[str, str]]:
        result: dict[str, dict[str, str]] = {}
        for name, field_info in model.model_fields.items():
            extra = field_info.json_schema_extra
            if not isinstance(extra, dict) or _BY_KEY not in extra:
                continue
            by_value = extra[_BY_KEY]
            value_value = extra.get(_VALUE_KEY)
            if not (isinstance(by_value, str) and isinstance(value_value, str)):
                continue
            entry: dict[str, str] = {
                _BY_KEY: by_value, _VALUE_KEY: value_value,
            }
            attr_value = extra.get(_ATTR_KEY)
            if isinstance(attr_value, str):
                entry[_ATTR_KEY] = attr_value
            result[name] = entry
        return result

    @staticmethod
    def _build_script(
        container_css: str,
        field_map: dict[str, dict[str, str]],
    ) -> str:
        """Сгенерировать JS `[{field: value, ...}, ...]`."""
        field_lines: list[str] = []
        for name, meta in field_map.items():
            by = meta[_BY_KEY]
            value = meta[_VALUE_KEY].replace("'", "\\'")
            attr = meta.get(_ATTR_KEY)

            if by == By.CSS_SELECTOR:
                selector_js = f"el.querySelector('{value}')"
            elif by == By.XPATH:
                selector_js = (
                    f"document.evaluate('{value}', el, null, "
                    f"XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue"
                )
            else:
                raise ValueError(
                    f"Неподдерживаемая стратегия локатора для поля: {by!r}",
                )

            if attr is not None:
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
