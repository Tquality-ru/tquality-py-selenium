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
import os
import pathlib
import shutil
import subprocess
import sys
from typing import TYPE_CHECKING, Any

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.safari.options import Options as SafariOptions

from tquality_selenium.config import BrowserType
from tquality_selenium.utils.os_utils import OSUtils

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


def _find_chrome_binary() -> str | None:
    """Найти исполняемый Chrome/Chromium на текущей ОС.

    undetected-chromedriver ищет только в PATH, что ломает macOS
    (Chrome в /Applications/) и Windows (Chrome в Program Files). Поэтому
    спрашиваем Selenium Manager - он идет с selenium и умеет находить
    бинарник на всех поддерживаемых ОС.
    """
    # 1. PATH (Linux обычно)
    for binary in (
        "google-chrome", "google-chrome-stable", "chromium",
        "chromium-browser", "chrome",
    ):
        path = shutil.which(binary)
        if path:
            return path
    # 2. Selenium Manager - знает где Chrome на любой ОС
    try:
        from selenium.webdriver.common.selenium_manager import SeleniumManager

        result = SeleniumManager().binary_paths(["--browser", "chrome"])
    except Exception:  # noqa: BLE001 - SeleniumManager может падать по-разному
        result = {}
    browser_path = result.get("browser_path")
    if isinstance(browser_path, str) and os.path.isfile(browser_path):
        return browser_path
    # 3. Фолбек на стандартные пути, если Selenium Manager недоступен
    if sys.platform == "darwin":
        for name in (
            "Google Chrome", "Google Chrome Beta", "Google Chrome Dev",
            "Google Chrome Canary", "Chromium",
        ):
            candidate = f"/Applications/{name}.app/Contents/MacOS/{name}"
            if os.path.isfile(candidate):
                return candidate
    if sys.platform == "win32":
        for env in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
            root = os.environ.get(env)
            if not root:
                continue
            candidate = os.path.join(
                root, "Google", "Chrome", "Application", "chrome.exe",
            )
            if os.path.isfile(candidate):
                return candidate
    return None


def _selenium_manager_chromedriver() -> str | None:
    """Резолвим chromedriver через Selenium Manager.

    SM подбирает chromedriver под версию системного Chrome и кладёт
    в свой кэш (правильная архитектура, Apple-подписан на macOS).
    Возвращаем путь или None, если SM не смог.
    """
    try:
        from selenium.webdriver.common.selenium_manager import SeleniumManager

        result = SeleniumManager().binary_paths(["--browser", "chrome"])
    except Exception:  # noqa: BLE001 - SeleniumManager падает по-разному
        return None
    driver_path = result.get("driver_path")
    if isinstance(driver_path, str) and os.path.isfile(driver_path):
        return driver_path
    return None


def _copy_chromedriver_to_own_cache(sm_path: str) -> str:
    """Скопировать SM-chromedriver в собственный кэш.

    UC патчит chromedriver in-place. Если патчить SM-исходник, ломается
    Apple-подпись бинарника, общего с обычным Chrome (Gatekeeper потом
    убивает regular Chrome сигналом SIGKILL). Чтобы изолировать UC от
    SM-кэша, копируем в `~/.cache/tquality-py-selenium/chromedriver/`
    c сохранением platform/version-структуры пути (version-aware кэш).
    """
    sm_path_obj = pathlib.Path(sm_path)
    own_root = pathlib.Path.home() / ".cache" / "tquality-py-selenium" / "chromedriver"
    own_path = own_root.joinpath(*sm_path_obj.parts[-3:])
    if not own_path.exists():
        own_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(sm_path, own_path)
        own_path.chmod(0o755)
    return str(own_path)


def _apply_linux_docker_chromium_flags(opts: Any) -> None:
    """Добавить флаги, нужные Chromium-based браузерам только в Linux
    под Docker: `--no-sandbox` (sandbox конфликтует с root-юзером
    в контейнере) и `--disable-dev-shm-usage` (дефолтный /dev/shm
    в Docker 64MB, не хватает Chrome'у). На macOS/Windows эти флаги
    не нужны и иногда ломают браузер: на Windows Edge с `--no-sandbox`
    падает на старте c `DevToolsActivePort file doesn't exist`.
    """
    if sys.platform == "linux":
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")


def _ensure_chromedriver_runnable(chromedriver_path: str) -> None:
    """Подготовить chromedriver-копию для UC.

    UC патчит chromedriver in-place (правит несколько байт для обхода
    антибот-детекции). На macOS патч ломает Apple-подпись бинарника, и
    Gatekeeper убивает процесс при старте сервиса сигналом SIGKILL
    (`Service ... unexpectedly exited. Status code was: -9`).

    Прогоняем патч заранее тем же `Patcher`, что использует UC, и сразу
    ad-hoc-подписываем результат через `codesign --sign -`. Когда дальше
    `uc.Chrome(driver_executable_path=...)` инициализирует свой Patcher,
    `is_binary_patched` вернет True и бинарник остается подписанным.
    """
    from undetected_chromedriver.patcher import Patcher

    Patcher(executable_path=chromedriver_path).auto()
    if sys.platform == "darwin":
        # check=False: если codesign недоступен (минимальный image без
        # CLI tools) - не валим запуск, а отдаем непадписанный бинарник.
        # Gatekeeper тогда снова убьет, но это поведение видно в логе сервиса.
        subprocess.run(
            ["codesign", "--force", "--sign", "-", chromedriver_path],
            check=False,
        )


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
        active = cfg.active_browser
        driver: WebDriver

        if browser is BrowserType.FIREFOX:
            ff_opts = FirefoxOptions()
            if active.headless:
                ff_opts.add_argument("--headless")
            driver = webdriver.Firefox(options=ff_opts)
        elif browser is BrowserType.EDGE:
            edge_opts = EdgeOptions()
            if active.headless:
                edge_opts.add_argument("--headless=new")
            _apply_linux_docker_chromium_flags(edge_opts)
            driver = webdriver.Edge(options=edge_opts)
        elif browser is BrowserType.SAFARI:
            # Safari не поддерживает headless; игнорируем флаг.
            safari_opts = SafariOptions()
            driver = webdriver.Safari(options=safari_opts)
        elif browser is BrowserType.UNDETECTED_CHROME:
            import undetected_chromedriver as uc

            uc_opts = uc.ChromeOptions()
            # Указываем системный Chrome - UC ищет его только в PATH
            # и без `binary_location` падает с TypeError на macOS/Windows.
            chrome_binary = _find_chrome_binary()
            if chrome_binary:
                uc_opts.binary_location = chrome_binary
            if active.headless:
                uc_opts.add_argument("--headless=new")
            _apply_linux_docker_chromium_flags(uc_opts)
            # Берём chromedriver, который уже подобрал Selenium Manager
            # (правильная архитектура), копируем в свой кэш и патчим
            # копию - SM-исходник трогать нельзя, им пользуется regular
            # Chrome (см. _copy_chromedriver_to_own_cache).
            sm_chromedriver = _selenium_manager_chromedriver()
            chromedriver_path: str | None = None
            if sm_chromedriver:
                chromedriver_path = _copy_chromedriver_to_own_cache(sm_chromedriver)
                _ensure_chromedriver_runnable(chromedriver_path)
            # use_subprocess=True - без него UC закрывает Chrome сразу
            # после старта (агрессивное управление процессом), сессия не
            # успевает подняться. Документировано в UC discussion #2282
            # и issue #2186.
            driver = uc.Chrome(
                options=uc_opts,
                driver_executable_path=chromedriver_path,
                use_subprocess=True,
            )
        elif browser is BrowserType.CHROME:
            ch_opts = ChromeOptions()
            if active.headless:
                ch_opts.add_argument("--headless=new")
            _apply_linux_docker_chromium_flags(ch_opts)
            driver = webdriver.Chrome(options=ch_opts)
        else:
            raise ValueError(f"Неподдерживаемый тип браузера: {browser!r}")

        driver.implicitly_wait(0)
        driver.set_page_load_timeout(active.page_load_timeout)
        driver.set_window_size(active.window_width, active.window_height)
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
    "is_browser_started",
]
