"""Waiter, привязанный к конкретному элементу.

Все методы возвращают `bool` (`True` - условие выполнилось, `False` -
истёк таймаут). По умолчанию исключение НЕ кидается; для жёсткого
падения - `raise_on_timeout=True` либо класс исключения.

```python
if not button.wait.until_clickable():
    pytest.fail("кнопка не стала кликабельной")

button.wait.until_visible(raise_on_timeout=True)
button.wait.until(predicate, raise_on_timeout=MyError, message="...",
                  poll_interval=0.1)
```

`for_computed_style` - утилита поверх `until(...)`, ждёт пока
вычисленный CSS-стиль элемента совпадёт с ожидаемым значением.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from selenium.webdriver.support.expected_conditions import (
    element_to_be_clickable,
    invisibility_of_element_located,
    presence_of_element_located,
    visibility_of_element_located,
)

if TYPE_CHECKING:
    from tquality_selenium.elements.base_element import BaseElement
    from tquality_selenium.services.driver_waiter import DriverWaiter
    from tquality_selenium.services.style_property import StyleProperty


class ElementWaiter[E: "BaseElement"]:
    """Ожидания, привязанные к элементу. Делегирует polling в `DriverWaiter`.

    Параметры (одинаковые у всех методов):

    - `timeout` (сек) - default из `config.waiter.timeout`.
    - `poll_interval` (сек) - пауза между опросами; default из
      `config.waiter.poll_interval`.
    - `raise_on_timeout` - `False` (default), `True`, либо класс исключения.
    - `message` - переопределяет авто-сгенерированный текст; попадает
      в лог и в текст исключения.
    """

    def __init__(self, driver_waiter: DriverWaiter, element: E) -> None:
        self._driver_waiter = driver_waiter
        self._element = element

    @property
    def _name_for_msg(self) -> str:
        return self._element.name

    def until(
        self,
        condition: Callable[[E], Any],
        *,
        timeout: float | None = None,
        poll_interval: float | None = None,
        raise_on_timeout: bool | type[BaseException] = False,
        message: str = "",
    ) -> bool:
        """Произвольное условие. `condition` принимает сам элемент - доступны
        `is_displayed`, `js_actions`, `text`, `get_attribute`, ... -
        работать с `WebDriver` напрямую не нужно."""
        return self._driver_waiter.until(
            lambda _: condition(self._element),
            timeout=timeout,
            poll_interval=poll_interval,
            raise_on_timeout=raise_on_timeout,
            message=message or f"{self._name_for_msg} to meet custom condition",
        )

    def until_visible(
        self,
        timeout: float | None = None,
        *,
        poll_interval: float | None = None,
        raise_on_timeout: bool | type[BaseException] = False,
        message: str = "",
    ) -> bool:
        return self._driver_waiter.until(
            visibility_of_element_located(self._element.by),
            timeout=timeout,
            poll_interval=poll_interval,
            raise_on_timeout=raise_on_timeout,
            message=message or f"{self._name_for_msg} to be visible",
        )

    def until_clickable(
        self,
        timeout: float | None = None,
        *,
        poll_interval: float | None = None,
        raise_on_timeout: bool | type[BaseException] = False,
        message: str = "",
    ) -> bool:
        return self._driver_waiter.until(
            element_to_be_clickable(self._element.by),
            timeout=timeout,
            poll_interval=poll_interval,
            raise_on_timeout=raise_on_timeout,
            message=message or f"{self._name_for_msg} to be clickable",
        )

    def until_present(
        self,
        timeout: float | None = None,
        *,
        poll_interval: float | None = None,
        raise_on_timeout: bool | type[BaseException] = False,
        message: str = "",
    ) -> bool:
        return self._driver_waiter.until(
            presence_of_element_located(self._element.by),
            timeout=timeout,
            poll_interval=poll_interval,
            raise_on_timeout=raise_on_timeout,
            message=message or f"{self._name_for_msg} to be present",
        )

    def until_invisible(
        self,
        timeout: float | None = None,
        *,
        poll_interval: float | None = None,
        raise_on_timeout: bool | type[BaseException] = False,
        message: str = "",
    ) -> bool:
        return self._driver_waiter.until(
            invisibility_of_element_located(self._element.by),
            timeout=timeout,
            poll_interval=poll_interval,
            raise_on_timeout=raise_on_timeout,
            message=message or f"{self._name_for_msg} to be invisible",
        )

    def until_not_present(
        self,
        timeout: float | None = None,
        *,
        poll_interval: float | None = None,
        raise_on_timeout: bool | type[BaseException] = False,
        message: str = "",
    ) -> bool:
        by = self._element.by
        return self._driver_waiter.until(
            lambda driver: not driver.find_elements(*by),
            timeout=timeout,
            poll_interval=poll_interval,
            raise_on_timeout=raise_on_timeout,
            message=message or f"{self._name_for_msg} to be not present",
        )

    def for_computed_style(
        self,
        style_property: str | StyleProperty,
        expected_value: str,
        *,
        timeout: float | None = None,
        poll_interval: float | None = None,
        raise_on_timeout: bool | type[BaseException] = False,
        message: str = "",
    ) -> bool:
        return self.until(
            lambda e: e.js_actions.get_computed_style(style_property) == expected_value,
            timeout=timeout,
            poll_interval=poll_interval,
            raise_on_timeout=raise_on_timeout,
            message=(
                message
                or f"{self._name_for_msg} computed style {style_property}={expected_value!r}"
            ),
        )
