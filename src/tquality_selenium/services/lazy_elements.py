"""`LazyElements`: лениво-резолвимая коллекция типизированных элементов."""
from __future__ import annotations

from collections.abc import Iterator, Sequence
from typing import TYPE_CHECKING, overload

from selenium.webdriver.remote.webelement import WebElement

from tquality_selenium.elements.base_element import BaseElement
from tquality_selenium.elements.by import By

if TYPE_CHECKING:
    from tquality_selenium.browser import BrowserService


class LazyElements[E: BaseElement](Sequence[E]):
    """Лениво-резолвимая коллекция типизированных элементов.

    Длина и сами элементы вычисляются по обращению - можно объявлять
    коллекцию в `__init__` page-object'а до загрузки страницы. Каждый
    элемент получает имя `f"{name_prefix} #{i+1}"` (1-based).

    ### Кэширование между итерациями

    В рамках одной итерации/comprehension (`__iter__`, `to_list`,
    `__getitem__(slice)`) `find_elements` вызывается ровно один раз -
    элементы привязаны к этому snapshot'у, и `_find()` возвращает
    сохранённый `WebElement` без повторного похода в DOM. Это срезает
    `O(N)` лишних `find_elements` при `for el in collection: el.action()`.

    Между итерациями кэш не переиспользуется: повторный `for` или
    `to_list()` делают свежий `find_elements`. Live-резолв сохраняется
    также для индексного доступа `collection[i]` - он берёт N-й узел на момент
    действия, без snapshot'а.

    Сторона риска: внутри одной итерации `WebElement`-ссылки могут
    стать stale, если страница перерисовалась между `find_elements` и
    действием над элементом. Если итерация триггерит ре-рендер - либо
    действуйте через индексный доступ (`collection[i]` каждый раз делает
    свежий resolve), либо итерируйтесь заново.
    """

    def __init__(
        self, element_cls: type[E], by: By, name_prefix: str = "",
    ) -> None:
        self._element_cls = element_cls
        self._by = by
        self._name_prefix = name_prefix or element_cls.__name__

    @property
    def _browser(self) -> BrowserService:
        from tquality_selenium.browser import BrowserService
        from tquality_selenium.container import SeleniumServices
        return SeleniumServices.get_service(BrowserService)

    def __len__(self) -> int:
        return len(self._browser.find_elements(*self._by))

    def __iter__(self) -> Iterator[E]:
        snapshot = self._browser.find_elements(*self._by)
        for i in range(len(snapshot)):
            yield self._make(i, snapshot)

    @overload
    def __getitem__(self, index: int) -> E: ...
    @overload
    def __getitem__(self, index: slice) -> list[E]: ...
    def __getitem__(self, index: int | slice) -> E | list[E]:
        if isinstance(index, slice):
            snapshot = self._browser.find_elements(*self._by)
            return [
                self._make(i, snapshot)
                for i in range(*index.indices(len(snapshot)))
            ]
        if index < 0:
            index += len(self)
        # Одиночный индексный доступ - live-резолв на момент действия,
        # snapshot не уместен (один элемент, и мы не знаем когда
        # пользователь будет с ним работать).
        return self._make(index)

    def to_list(self) -> list[E]:
        """Резолвить коллекцию полностью и вернуть `list[E]`.

        Один `find_elements` + N конструкций индексированных элементов;
        все возвращенные элементы привязаны к этому snapshot'у (как при
        обычной итерации - см. описание класса).

        Реализовано напрямую через `find_elements`, а не через
        `list(self)` - последний дёргает `__length_hint__` →
        `__len__`, и получается лишний `find_elements` в довесок к
        `__iter__`.
        """
        snapshot = self._browser.find_elements(*self._by)
        return [self._make(i, snapshot) for i in range(len(snapshot))]

    def _make(
        self,
        index: int,
        snapshot: list[WebElement] | None = None,
    ) -> E:
        """Создать элемент с резолвером, целящимся в N-й узел.

        `snapshot=None` - live-резолв (`find_elements` при каждом
        `_find()`). Передан `snapshot` - используется он, без
        повторного захода в DOM.
        """
        name = f"{self._name_prefix} #{index + 1}"
        elem = self._element_cls(self._by, name)
        by = self._by

        if snapshot is None:
            def _find() -> WebElement:
                return self._browser.find_elements(*by)[index]
        else:
            bound: list[WebElement] = snapshot

            def _find() -> WebElement:
                return bound[index]

        elem._find = _find  # type: ignore[method-assign]
        return elem


__all__ = ["LazyElements"]
