"""Pytest-плагин: при падении теста прикрепляет page_source к allure.

Зарегистрирован через `[project.entry-points.pytest11]` в pyproject.toml,
поэтому в проектах-потребителях не требует явного `pytest_plugins`.

### Поведение

- Триггер: pytest-репорт `failed=True` (любая фаза - call/setup/teardown).
- Единственный run-time guard: запущен ли браузер
  (`SeleniumServices.is_browser_started()`). Не запущен - no-op.
  Покрывает api/db-only тесты, упавшие до старта сессии, и сам же случай
  `setup` с непроинициализированным драйвером.
- Если запущен - читаем `driver.page_source` и кладём в allure как
  HTML-вложение `Page source`. Если `page_source` бросает (сессия мертва) -
  прикрепляется короткий TEXT-диагностик вместо HTML, чтобы не маскировать
  исходное падение.

### Опт-аут

Поле `attach_page_source_on_failure` в `SeleniumConfig` (по умолчанию
`True`). Можно выключить через config.json5 или env-переменную
`TEST_ATTACH_PAGE_SOURCE_ON_FAILURE=false`.
"""
from __future__ import annotations

from typing import Any

import allure
import pytest


_ATTACHMENT_NAME = "Page source"


def _try_get_config() -> Any:
    """Вернуть активный SeleniumConfig либо None, если контейнер не настроен."""
    try:
        from tquality_selenium.config import SeleniumConfig
        from tquality_selenium.container import SeleniumServices
    except ImportError:
        return None
    try:
        return SeleniumServices.get_service(SeleniumConfig)
    except Exception:
        return None


def _try_get_driver() -> Any:
    """Вернуть активный WebDriver либо None, если браузер не запущен."""
    try:
        from tquality_selenium.container import SeleniumServices
    except ImportError:
        return None
    try:
        if not SeleniumServices.is_browser_started():
            return None
        return SeleniumServices.browser().driver
    except Exception:
        return None


def _capture_page_source(driver: Any) -> tuple[str, Any]:
    """Снять page_source. На сбое - вернуть диагностический stub."""
    try:
        source: str = driver.page_source
        return source, allure.attachment_type.HTML
    except Exception as exc:
        comment = (
            "<!-- page_source capture failed: "
            f"{type(exc).__name__}: {exc!r} -->"
        )
        return comment, allure.attachment_type.TEXT


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(
    item: pytest.Item, call: pytest.CallInfo[None],
) -> Any:
    """Прикрепить page_source к allure при падении теста."""
    outcome = yield
    report = outcome.get_result()

    if not report.failed:
        return

    config = _try_get_config()
    if config is not None and not getattr(
        config, "attach_page_source_on_failure", True,
    ):
        return

    driver = _try_get_driver()
    if driver is None:
        return

    body, attachment_type = _capture_page_source(driver)
    allure.attach(body, name=_ATTACHMENT_NAME, attachment_type=attachment_type)
