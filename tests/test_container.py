"""Тесты DI-контейнера `SeleniumServices`: расширение и резолв по типу.

Активного composition root с отдельным реестром больше нет: `get_service`
резолвит из того контейнера, на котором вызван, а подкласс (`@copy`) резолвит
свои переопределения через наследование. Потребители фреймворка обращаются к
`SeleniumServices` напрямую; проект, переопределяющий провайдеры, работает через
собственный `@copy`-подкласс.
"""
from __future__ import annotations

import typing
from typing import Any, override

import pytest
from static_dependency_injector.containers import copy
from static_dependency_injector.static_providers import Singleton

from tquality_selenium import (
    BrowserService,
    ElementFactory,
    SeleniumServices,
)

# --- стабовые сервисы -------------------------------------------------------


class _MyService:
    """Произвольный сервис для проверки расширения контейнера."""


class _ServicesWithExtra(SeleniumServices):
    my_service: _MyService = Singleton(_MyService)


class _FakeBrowserA(BrowserService):
    def __init__(self) -> None:  # пропускаем тяжелую инициализацию драйвера
        pass

    # Возвращаем строки-сентинелы (а не настоящие WebElement) - тестам
    # достаточно идентификации; mypy override-LSP проверяет совместимость
    # типа возврата, поэтому маркируем `list[Any]`.
    @typing.override
    def find_elements(self, by: str, value: str) -> list[Any]:
        return ["A0", "A1", "A2"]


class _FakeBrowserB(BrowserService):
    def __init__(self) -> None:
        pass

    @override
    def find_elements(self, by: str, value: str) -> list[Any]:
        return ["B0", "B1"]


# Базовый `SeleniumServices.browser` - `ContextLocalSingleton[BrowserService]`;
# в подклассе переопределяем более простым `Singleton[_FakeBrowser*]`
# (подтип `BrowserService`, поэтому слот типизируется как `BrowserService`).
class _ServicesA(SeleniumServices):
    browser: BrowserService = Singleton(_FakeBrowserA)


class _ServicesB(SeleniumServices):
    browser: BrowserService = Singleton(_FakeBrowserB)


# --- get_service: резолв по типу --------------------------------------------


def test_get_service_resolves_by_exact_type() -> None:
    factory = SeleniumServices.get_service(ElementFactory)
    assert isinstance(factory, ElementFactory)


def test_get_service_resolves_by_superclass_match() -> None:
    """`browser` зарегистрирован как `BrowserService`; `_FakeBrowserA` - подкласс."""
    browser = _ServicesA.get_service(BrowserService)
    assert isinstance(browser, _FakeBrowserA)


def test_get_service_raises_for_unknown_type() -> None:
    class _Unknown:
        pass

    with pytest.raises(LookupError):
        SeleniumServices.get_service(_Unknown)


def test_subclass_extends_with_new_service() -> None:
    svc = _ServicesWithExtra.get_service(_MyService)
    assert isinstance(svc, _MyService)


def test_subclass_overrides_existing_service() -> None:
    """Override существующего провайдера в подклассе виден через `get_service`."""
    browser = _ServicesA.get_service(BrowserService)
    assert isinstance(browser, _FakeBrowserA)
    assert not isinstance(browser, _FakeBrowserB)


def test_get_service_resolves_from_the_class_it_is_called_on() -> None:
    """Никакого «активного» реестра: каждый контейнер резолвит свои провайдеры."""
    assert isinstance(_ServicesA.get_service(BrowserService), _FakeBrowserA)
    assert isinstance(_ServicesB.get_service(BrowserService), _FakeBrowserB)


# --- inheritance + @copy: подкласс самосогласован ---------------------------


class _FakeBrowserWithDriver(BrowserService):
    """Фейковый browser с сентинел-`driver` (проверяем перевязку зависимого)."""

    driver = "fake-driver-sentinel"

    def __init__(self) -> None:
        pass


@copy(SeleniumServices)
class _CopyServices(SeleniumServices):
    browser: BrowserService = Singleton(_FakeBrowserWithDriver)


def test_copy_rewires_inherited_dependent_onto_overridden_slot() -> None:
    """`@copy` перевязывает унаследованный `driver` на переопределённый `browser`.

    `driver = Callable(attrgetter("driver"), browser)` - зависимый провайдер;
    после `@copy` он смотрит на `_CopyServices.browser`, а не на базовый.
    Это и есть «inheritance + @copy»-маршрутизация вместо реестра активного root.
    """
    assert isinstance(_CopyServices.get_service(BrowserService), _FakeBrowserWithDriver)
    assert _CopyServices.driver == "fake-driver-sentinel"
