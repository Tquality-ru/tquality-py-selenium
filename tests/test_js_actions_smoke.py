"""Интеграционные smoke-тесты `ElementJsActions` через настоящий Chrome.

Запускают headless Chrome и проверяют, что JS-getters действительно читают
CSS-значения с DOM-элемента: модульные тесты в `test_elements.py` мокают
driver и не исполняют сам JS-скрипт, поэтому корректность JS-строк именно
здесь и проверяется. Маркированы тегами всех ОС, на которых Chrome
поддерживается, плюс `chrome` - попадают в `tests:*-browsers-healthcheck`
и фильтруются из юнит-job'а через `-m "not macos"`.
"""
from __future__ import annotations

from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from tquality_selenium import (
    BrowserService,
    BrowserType,
    SeleniumConfig,
    StyleProperty,
)
from tquality_selenium.config import BrowserConfig
from tquality_selenium.services.js_actions import ElementJsActions

# Минимальная страница со стилями inline - не зависит от сети.
_STYLED_PAGE = (
    "data:text/html,"
    "<html><body>"
    "<div id='target' style='"
    "display:block;"
    "opacity:0.5;"
    "background-color:rgb(255,0,0);"
    "z-index:42;"
    "color:rgb(0,128,0)"
    "'>x</div>"
    "</body></html>"
)


@pytest.mark.macos
@pytest.mark.linux
@pytest.mark.windows
@pytest.mark.chrome
def test_get_computed_style_reads_real_css_values() -> None:
    """Single и bulk getters возвращают значения, которые поставил браузер."""
    cfg = SeleniumConfig(
        browser=BrowserType.CHROME,
        chrome=BrowserConfig(headless=True),
    )
    service = BrowserService(cfg)
    try:
        service.open(_STYLED_PAGE)
        target = service.driver.find_element("id", "target")
        ja = ElementJsActions(find=lambda: target)

        # Подменяем _driver/_log на классе - DI-контейнер для smoke не нужен.
        with patch.object(
            ElementJsActions, "_driver", new_callable=PropertyMock,
        ) as drv, patch.object(
            ElementJsActions, "_log", new_callable=PropertyMock,
        ) as log:
            drv.return_value = service.driver
            log.return_value = MagicMock()

            # str-аргумент.
            assert ja.get_computed_style("display") == "block"
            # Enum-аргумент - StrEnum уезжает в JS как строковое значение.
            assert ja.get_computed_style(StyleProperty.OPACITY) == "0.5"
            assert ja.get_computed_style(StyleProperty.Z_INDEX) == "42"
            # Несуществующее свойство - пустая строка (контракт CSSOM).
            assert ja.get_computed_style("definitely-not-a-css-property") == ""

            # Bulk getter содержит все стилизованные свойства.
            styles = ja.get_computed_styles()
            assert styles["display"] == "block"
            assert styles["opacity"] == "0.5"
            assert styles["z-index"] == "42"
            # Chrome сериализует rgb с пробелами после запятых.
            assert styles["background-color"] == "rgb(255, 0, 0)"
            assert styles["color"] == "rgb(0, 128, 0)"
            # В bulk-результате - десятки computed-свойств, проверим
            # минимальный размер чтобы не разъехалось семантически.
            assert len(styles) > 50
    finally:
        service.quit()
