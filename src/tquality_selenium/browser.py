"""Сервис браузера: создает и оборачивает Selenium WebDriver.

Тип браузера выбирается из `SeleniumConfig.browser`. Поддерживаются Chrome,
Firefox, Edge, Safari и undetected-chrome. Implicit wait захардкожен в 0 -
используйте только explicit ожидания.

Safari и Edge доступны только на своих платформах (см. config.py). Попытка
запустить неподдерживаемый браузер приводит к `BrowserNotSupportedError`
с понятным сообщением.
"""
from __future__ import annotations

import contextvars
import re
import shutil
import subprocess
import sys
from typing import TYPE_CHECKING

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.safari.options import Options as SafariOptions

from tquality_selenium.config import BrowserType
from tquality_selenium.os_utils import OSUtils

if TYPE_CHECKING:
    from tquality_selenium.config import SeleniumConfig


_browser_started: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "_browser_started", default=False,
)


class BrowserNotSupportedError(RuntimeError):
    """Браузер не поддерживается в текущей ОС."""


def is_browser_started() -> bool:
    """Вернуть True, если в текущем контексте запущен браузер."""
    return _browser_started.get()


def _detect_chrome_version() -> int | None:
    """Определить мажорную версию установленного Chrome (для uc.Chrome)."""
    for binary in (
        "google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
    ):
        path = shutil.which(binary)
        if path is None:
            continue
        try:
            output = subprocess.check_output(
                [path, "--version"], text=True, timeout=5,
            )
        except (subprocess.SubprocessError, OSError):
            continue
        match = re.search(r"(\d+)", output)
        if match:
            return int(match.group(1))
    return None


class BrowserService:
    """Обертка над Selenium WebDriver с DI-дружественным интерфейсом."""

    def __init__(self, config: SeleniumConfig) -> None:
        self._config = config
        self._check_os_support()
        self._driver = self._create_driver()
        _browser_started.set(True)

    def _check_os_support(self) -> None:
        browser = self._config.browser
        if not OSUtils.is_browser_supported_on_current_os(browser):
            raise BrowserNotSupportedError(
                f"Браузер {browser.value} не поддерживается в ОС {sys.platform}. "
                f"Запустите тесты на совместимой платформе или выберите другой "
                f"браузер в конфиге."
            )

    def _create_driver(self) -> WebDriver:
        cfg = self._config
        browser = cfg.browser
        driver: WebDriver

        if browser is BrowserType.FIREFOX:
            ff_opts = FirefoxOptions()
            if cfg.headless:
                ff_opts.add_argument("--headless")
            driver = webdriver.Firefox(options=ff_opts)
        elif browser is BrowserType.EDGE:
            edge_opts = EdgeOptions()
            if cfg.headless:
                edge_opts.add_argument("--headless=new")
            edge_opts.add_argument("--no-sandbox")
            edge_opts.add_argument("--disable-dev-shm-usage")
            driver = webdriver.Edge(options=edge_opts)
        elif browser is BrowserType.SAFARI:
            # Safari не поддерживает headless; игнорируем флаг.
            safari_opts = SafariOptions()
            driver = webdriver.Safari(options=safari_opts)
        elif browser is BrowserType.UNDETECTED_CHROME:
            import undetected_chromedriver as uc

            uc_opts = uc.ChromeOptions()
            if cfg.headless:
                uc_opts.add_argument("--headless=new")
            uc_opts.add_argument("--no-sandbox")
            uc_opts.add_argument("--disable-dev-shm-usage")
            version_main = _detect_chrome_version()
            driver = uc.Chrome(options=uc_opts, version_main=version_main)
        elif browser is BrowserType.CHROME:
            ch_opts = ChromeOptions()
            if cfg.headless:
                ch_opts.add_argument("--headless=new")
            ch_opts.add_argument("--no-sandbox")
            ch_opts.add_argument("--disable-dev-shm-usage")
            driver = webdriver.Chrome(options=ch_opts)
        else:
            raise ValueError(f"Неподдерживаемый тип браузера: {browser!r}")

        driver.implicitly_wait(0)
        driver.set_page_load_timeout(cfg.page_load_timeout)
        driver.set_window_size(cfg.window_width, cfg.window_height)
        return driver

    @property
    def driver(self) -> WebDriver:
        return self._driver

    def open(self, url: str) -> None:
        self._driver.get(url)

    def find_element(self, by: str, value: str) -> WebElement:
        return self._driver.find_element(by, value)

    def find_elements(self, by: str, value: str) -> list[WebElement]:
        return self._driver.find_elements(by, value)

    def quit(self) -> None:
        self._driver.quit()
        _browser_started.set(False)


__all__ = [
    "BrowserNotSupportedError",
    "BrowserService",
    "By",
    "is_browser_started",
]
