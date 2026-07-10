"""Grid-интеграция: `BaseElement.bidi_actions.submit_to_file_dialogue` через BiDi.

Сценарий с detached file-input - ровно та ситуация, ради которой нужен BiDi
file-dialog, а не `send_keys`: input создаётся и кликается JS-обработчиком ссылки
и никогда не попадает в DOM (по нему нельзя ни найти, ни `send_keys`).
`submit_to_file_dialogue` вешает BiDi-перехватчик file-dialog и кликает ссылку;
перехватчик подсовывает node-абсолютный файл, `change`-обработчик пишет имя
выбранного файла в #file-upload-result.

Страница - общая `page_url` (tests/resources/page.html, фикстура в tests/conftest.py).
Конфиг (chrome + bidi + windows + grid) резолвится из config.json5 этого модуля
поверх ../config.json5 (remote_url).
"""

from __future__ import annotations

import pytest

from tquality_selenium import BrowserService
from tquality_selenium.container import SeleniumServices
from tquality_selenium.elements.by import By
from tquality_selenium.elements.element import Element

pytestmark = [pytest.mark.chrome, pytest.mark.windows]

# Файл, который гарантированно есть на любом Windows-ноде - проверяем, что он
# долетел до input (браузер показывает путь как C:\fakepath\<name>).
_NODE_FILE = r"C:\Windows\win.ini"
_EXPECTED_NAME = "win.ini"


def test_submit_to_file_dialogue_attaches_detached_input_file(page_url: str) -> None:
    service = SeleniumServices.get_service(BrowserService)
    try:
        service.open(page_url)
        Element(By.id("file-upload-trigger")).bidi_actions.submit_to_file_dialogue(_NODE_FILE)
        assert Element(By.id("file-upload-result")).text == _EXPECTED_NAME
    finally:
        service.quit()
