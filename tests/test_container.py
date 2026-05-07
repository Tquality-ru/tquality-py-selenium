"""Тесты DI-контейнера `SeleniumServices`: расширение, override, тред-изоляция.

Двухуровневая модель активного контейнера:
- `_default_services` (process-wide) - выставляется `setup()`.
- `_active_services_ctx` (per-context ContextVar) - выставляется
  `override_active(...)`. Тесты этого файла, мутирующие process-wide default,
  выполняются в отдельном подпроцессе через `subprocess.run` с явным `cwd=`.

Почему не `pytester.runpytest_subprocess`: pytester полагается на
`monkeypatch.chdir(tmp_path)` в основном процессе и не передает `cwd=` в
`Popen`. Под тред-параллелизмом два конкурирующих pytester-теста могут
chdir-ить друг другу cwd, и subprocess стартует не в своей директории -
наблюдалось на pytest-threadpool. Прямой `subprocess.run([..., cwd=tmp_path])`
от этого свободен.
"""
from __future__ import annotations

import subprocess
import sys
import textwrap
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
from pathlib import Path
from typing import Any

import pytest
from dependency_injector import providers

from tquality_selenium import (
    BaseElement,
    BrowserService,
    Button,
    By,
    ElementFactory,
    SeleniumServices,
)


def _run_in_subprocess(tmp_path: Path, body: str) -> None:
    """Выполнить `body` Python-кода в подпроцессе с cwd=tmp_path.

    Подпроцесс наследует venv (через `sys.executable`), но не cwd
    основного процесса - это снимает гонку chdir/setattr между тредами.
    Падает с понятным сообщением, если код вернул ненулевой код выхода.
    """
    script = tmp_path / "_assert.py"
    script.write_text(body)
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"Subprocess вернул {result.returncode}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )


# --- стабовые сервисы -------------------------------------------------------


class _MyService:
    """Произвольный сервис для проверки расширения контейнера."""


class _ServicesWithExtra(SeleniumServices):
    my_service: providers.Singleton[_MyService] = providers.Singleton(_MyService)


class _FakeBrowserA(BrowserService):
    def __init__(self) -> None:  # пропускаем тяжелую инициализацию драйвера
        pass

    # Возвращаем строки-сентинелы (а не настоящие WebElement) - тестам
    # достаточно идентификации; mypy override-LSP проверяет совместимость
    # типа возврата, поэтому маркируем `list[Any]`.
    def find_elements(self, by: str, value: str) -> list[Any]:
        return ["A0", "A1", "A2"]


class _FakeBrowserB(BrowserService):
    def __init__(self) -> None:
        pass

    def find_elements(self, by: str, value: str) -> list[Any]:
        return ["B0", "B1"]


# Базовый `SeleniumServices.browser` - `ContextLocalSingleton[BrowserService]`,
# нам же удобнее `Singleton[_FakeBrowser*]`. Runtime dependency-injector
# принимает любой Provider, но mypy строго проверяет совпадение типа
# атрибута - `# type: ignore[assignment]` на провайдер-override-ах.
class _ServicesA(SeleniumServices):
    browser = providers.Singleton(_FakeBrowserA)  # type: ignore[assignment]


class _ServicesB(SeleniumServices):
    browser = providers.Singleton(_FakeBrowserB)  # type: ignore[assignment]


# --- in-process: get_service резолв -----------------------------------------


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


# --- in-process: override_active per-context --------------------------------


def test_override_active_swaps_resolution_within_block() -> None:
    """Внутри `with override_active(...)` lookups через базовый класс идут в override."""
    with _ServicesA.override_active():
        browser = SeleniumServices.get_service(BrowserService)
    assert isinstance(browser, _FakeBrowserA)


def test_override_active_does_not_leak_after_block() -> None:
    """После выхода из контекста override снят - default не затронут."""
    with _ServicesA.override_active():
        pass
    # Снаружи: `_default_services` не выставлен в этом тесте, fallback идет
    # в базовый `SeleniumServices`, где browser требует config - но мы не
    # резолвим browser, проверяем легковесный сервис.
    factory = SeleniumServices.get_service(ElementFactory)
    assert isinstance(factory, ElementFactory)


def test_override_active_propagates_to_base_element_browser_lookup() -> None:
    """`BaseElement._browser` идет через активный контейнер - видит override."""
    el = BaseElement(By.css_selector(".x"))
    with _ServicesA.override_active():
        assert isinstance(el._browser, _FakeBrowserA)


def test_override_active_propagates_to_lazy_elements() -> None:
    """LazyElements использует тот же активный контейнер."""
    collection = ElementFactory().elements(Button, By.css_selector("button"), "btn")
    with _ServicesA.override_active():
        assert len(collection) == 3
        assert collection[1]._find() == "A1"


# --- in-process: тред-изоляция через ContextVar -----------------------------


def test_override_active_is_isolated_across_threads() -> None:
    """Каждый тред со своим override видит свой контейнер; не пересекаются.

    `ContextVar` НЕ наследуется дочерним тредом автоматически - используем
    `copy_context().run(...)` явно. В каждом треде контекст - копия родительского
    + локальные `set()` поверх (не видны другим тредам)."""

    def worker(services_cls: type[SeleniumServices]) -> str:
        def _run() -> str:
            with services_cls.override_active():
                browser = SeleniumServices.get_service(BrowserService)
                return type(browser).__name__
        return copy_context().run(_run)

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(
            worker, [_ServicesA, _ServicesB, _ServicesA, _ServicesB],
        ))

    assert results == ["_FakeBrowserA", "_FakeBrowserB", "_FakeBrowserA", "_FakeBrowserB"]


def test_override_active_does_not_propagate_to_child_thread_without_copy() -> None:
    """Документируем гарантию: без `copy_context` дочерний тред НЕ видит override.

    Если этот тест когда-нибудь начнет падать - значит Python поменял
    дефолтное поведение наследования контекста, и доку контейнера надо обновить.
    """
    seen_in_child: list[type | None] = []

    def child() -> None:
        from tquality_selenium.container import _active_services_ctx
        seen_in_child.append(_active_services_ctx.get())

    with _ServicesA.override_active():
        # запускаем без copy_context().run(...)
        with ThreadPoolExecutor(max_workers=1) as pool:
            pool.submit(child).result()

    assert seen_in_child == [None]


# --- subprocess: process-wide default через setup() -------------------------


def test_setup_writes_process_wide_default(tmp_path: Path) -> None:
    """`setup()` ставит default, видимый из любого треда без override.

    Объединяет три проверки в одном subprocess-прогоне: default видим после
    `setup()`, виден в worker-треде, последний `setup()` побеждает.
    """
    _run_in_subprocess(tmp_path, textwrap.dedent("""
        from concurrent.futures import ThreadPoolExecutor
        from dependency_injector import providers

        from tquality_selenium import BrowserService, SeleniumServices


        class _FakeBrowser(BrowserService):
            def __init__(self): pass


        class ProjectServices(SeleniumServices):
            browser = providers.Singleton(_FakeBrowser)


        ProjectServices.setup()

        # 1. default виден после setup() через базовый класс
        assert isinstance(SeleniumServices.get_service(BrowserService), _FakeBrowser)

        # 2. default виден в worker-треде (без copy_context)
        with ThreadPoolExecutor(max_workers=1) as pool:
            cls_name = pool.submit(
                lambda: type(SeleniumServices.get_service(BrowserService)).__name__,
            ).result()
        assert cls_name == "_FakeBrowser", cls_name


        # 3. последний setup() побеждает
        class _OtherFakeBrowser(BrowserService):
            def __init__(self): pass


        class OtherServices(SeleniumServices):
            browser = providers.Singleton(_OtherFakeBrowser)


        OtherServices.setup()
        assert isinstance(
            SeleniumServices.get_service(BrowserService), _OtherFakeBrowser,
        )
    """))


def test_override_active_takes_precedence_over_setup_default(tmp_path: Path) -> None:
    """ContextVar override побеждает process-wide default."""
    _run_in_subprocess(tmp_path, textwrap.dedent("""
        from dependency_injector import providers

        from tquality_selenium import BrowserService, SeleniumServices


        class _DefaultBrowser(BrowserService):
            def __init__(self): pass


        class _OverrideBrowser(BrowserService):
            def __init__(self): pass


        class DefaultServices(SeleniumServices):
            browser = providers.Singleton(_DefaultBrowser)


        class OverrideServices(SeleniumServices):
            browser = providers.Singleton(_OverrideBrowser)


        DefaultServices.setup()
        with OverrideServices.override_active():
            assert isinstance(
                SeleniumServices.get_service(BrowserService), _OverrideBrowser,
            )
        # После выхода - снова default.
        assert isinstance(
            SeleniumServices.get_service(BrowserService), _DefaultBrowser,
        )
    """))
