"""Сервис браузера: создает и оборачивает Selenium WebDriver.

Тип браузера выбирается из `SeleniumConfig.browser`. Поддерживаются Chrome,
Firefox, Edge, Safari и undetected-chrome. Implicit wait захардкожен в 0 -
используйте только explicit ожидания.

Safari и Edge доступны только на своих платформах (см. config.py). Попытка
запустить неподдерживаемый браузер приводит к `BrowserNotSupportedError`
с понятным сообщением.

Все helper'ы (поиск Chrome-бинарника, резолв chromedriver через Selenium
Manager, копирование/патч UC-chromedriver, флаги для Docker и т.д.) -
`@staticmethod` на `BrowserService`. Вызовы внутри `_create_driver` идут
через `self.X(...)`, так что subclass'у достаточно override-нуть нужный
helper, чтобы подменить поведение без переписывания всего factory-метода.
"""
from __future__ import annotations

import contextvars
import os
import pathlib
import shutil
import subprocess
import sys
from typing import TYPE_CHECKING

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.options import ArgOptions
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.safari.options import Options as SafariOptions

from tquality_selenium.config import BrowserType
from tquality_selenium.utils.os_utils import OSUtils

if TYPE_CHECKING:
    from tquality_selenium.config import SeleniumConfig
    from tquality_selenium.services.actions import Actions
    from tquality_selenium.services.bidi_actions import BiDiBrowserActions
    from tquality_selenium.services.context_manager import ContextManager
    from tquality_selenium.services.js_actions import JsActions


class BrowserNotSupportedError(RuntimeError):
    """Браузер не поддерживается в текущей ОС."""


class BrowserService:
    """Обертка над Selenium WebDriver с DI-дружественным интерфейсом."""

    _started: contextvars.ContextVar[bool] = contextvars.ContextVar(
        "_browser_started", default=False,
    )

    def __init__(self, config: SeleniumConfig) -> None:
        self._config = config
        if not config.remote_url:
            self._check_os_support()
        self._driver = self._create_driver()
        type(self)._started.set(True)
        # Lazy-composed action facades (см. .js_actions / .bidi).
        self._js_actions: JsActions | None = None
        self._bidi: BiDiBrowserActions | None = None

    @classmethod
    def is_started(cls) -> bool:
        """Вернуть True, если в текущем контексте запущен браузер."""
        return cls._started.get()

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
        if cfg.remote_url:
            return self._create_remote_driver()
        browser = cfg.browser
        active = cfg.active_browser
        bidi = cfg.bidi
        driver: WebDriver

        if browser is BrowserType.FIREFOX:
            ff_opts = FirefoxOptions()
            if active.headless:
                ff_opts.add_argument("--headless")
            self._apply_arguments(ff_opts, active.arguments)
            if bidi:
                self._enable_bidi(ff_opts)
            driver = webdriver.Firefox(options=ff_opts)
        elif browser is BrowserType.EDGE:
            edge_opts = EdgeOptions()
            if active.headless:
                edge_opts.add_argument("--headless=new")
            self._apply_arguments(edge_opts, active.arguments)
            self._apply_linux_docker_chromium_flags(edge_opts)
            if bidi:
                self._enable_bidi(edge_opts)
            driver = webdriver.Edge(options=edge_opts)
        elif browser is BrowserType.SAFARI:
            # Safari не поддерживает headless; игнорируем флаг. BiDi в
            # safaridriver частично поддерживается с Safari 18.4 (macOS
            # 15.4): `script.*` и базовый `browsingContext.*` работают,
            # `input.*` / `network.*` / `browsingContext.captureScreenshot`
            # ещё нет. На macOS <15.4 webSocketUrl-capability приводит к
            # отказу в сессии - там выставьте `bidi: false`.
            safari_opts = SafariOptions()
            if bidi:
                self._enable_bidi(safari_opts)
            driver = webdriver.Safari(options=safari_opts)
        elif browser is BrowserType.UNDETECTED_CHROME:
            import undetected_chromedriver as uc

            uc_opts = uc.ChromeOptions()
            # Указываем системный Chrome - UC ищет его только в PATH
            # и без `binary_location` падает с TypeError на macOS/Windows.
            chrome_binary = self._find_chrome_binary()
            if chrome_binary:
                uc_opts.binary_location = chrome_binary
            if active.headless:
                uc_opts.add_argument("--headless=new")
            self._apply_arguments(uc_opts, active.arguments)
            self._apply_linux_docker_chromium_flags(uc_opts)
            if bidi:
                self._enable_bidi(uc_opts)
            # Берём chromedriver, который уже подобрал Selenium Manager
            # (правильная архитектура), копируем в свой кэш и патчим
            # копию - SM-исходник трогать нельзя, им пользуется regular
            # Chrome (см. `_copy_chromedriver_to_own_cache`).
            sm_chromedriver = self._selenium_manager_chromedriver()
            chromedriver_path: str | None = None
            if sm_chromedriver:
                chromedriver_path = self._copy_chromedriver_to_own_cache(
                    sm_chromedriver,
                )
                self._ensure_chromedriver_runnable(chromedriver_path)
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
            self._apply_arguments(ch_opts, active.arguments)
            self._apply_linux_docker_chromium_flags(ch_opts)
            if bidi:
                self._enable_bidi(ch_opts)
            driver = webdriver.Chrome(options=ch_opts)
        else:
            raise ValueError(f"Неподдерживаемый тип браузера: {browser!r}")

        driver.implicitly_wait(0)
        driver.set_page_load_timeout(active.page_load_timeout)
        driver.set_window_size(active.window_width, active.window_height)
        return driver

    def _create_remote_driver(self) -> WebDriver:
        cfg = self._config
        assert cfg.remote_url, "remote_url не задан"
        browser = cfg.browser
        active = cfg.active_browser
        if browser is BrowserType.FIREFOX:
            opts: ArgOptions = FirefoxOptions()
            if active.headless:
                opts.add_argument("--headless")
        elif browser is BrowserType.EDGE:
            opts = EdgeOptions()
            if active.headless:
                opts.add_argument("--headless=new")
        elif browser is BrowserType.SAFARI:
            opts = SafariOptions()
        elif browser is BrowserType.UNDETECTED_CHROME:
            import undetected_chromedriver as uc
            opts = uc.ChromeOptions()
            if active.headless:
                opts.add_argument("--headless=new")
        elif browser is BrowserType.CHROME:
            opts = ChromeOptions()
            if active.headless:
                opts.add_argument("--headless=new")
        else:
            raise ValueError(f"Неподдерживаемый тип браузера: {browser!r}")
        if browser is not BrowserType.SAFARI:
            self._apply_arguments(opts, active.arguments)
        if cfg.bidi:
            self._enable_bidi(opts)
        for cap_key, cap_value in cfg.capabilities.model_dump(exclude_none=True).items():
            opts.set_capability(cap_key, cap_value)
        driver = webdriver.Remote(command_executor=cfg.remote_url, options=opts)
        driver.implicitly_wait(0)
        driver.set_page_load_timeout(active.page_load_timeout)
        driver.set_window_size(active.window_width, active.window_height)
        return driver

    @property
    def driver(self) -> WebDriver:
        return self._driver

    @property
    def js_actions(self) -> JsActions:
        """JS-обёртка над driver'ом, привязанная к этому BrowserService.

        Lazy-композиция: `JsActions(driver_getter=lambda: self.driver)`.
        Subclass-у BrowserService достаточно вернуть наследника JsActions
        из этой property - DI-контейнер для этого не нужен.
        """
        if self._js_actions is None:
            from tquality_selenium.services.js_actions import JsActions
            self._js_actions = JsActions(driver_getter=lambda: self._driver)
        return self._js_actions

    @property
    def actions(self) -> Actions:
        """Свежий W3C-actions builder, привязанный к этому BrowserService.

        Каждый вызов отдаёт новый `Actions`-инстанс - state цепочки не
        шарится между независимыми построениями (`browser.actions.click(a)`
        и `browser.actions.click(b)` - две отдельные цепочки).
        """
        from tquality_selenium.services.actions import Actions
        return Actions(driver_getter=lambda: self._driver)

    @property
    def bidi(self) -> BiDiBrowserActions:
        """BiDi-фасад - raw-модули (`script`/`network`/`browsing_context`/
        `input`) плюс высокоуровневые методы. Та же lazy-композиция.
        """
        if self._bidi is None:
            from tquality_selenium.services.bidi_actions import BiDiBrowserActions
            self._bidi = BiDiBrowserActions(driver_getter=lambda: self._driver)
        return self._bidi

    @property
    def context(self) -> ContextManager:
        """Фасад фокуса сессии: окна/табы, фреймы, алерты.

        Шорткат для `SeleniumServices.get_service(ContextManager)`:
        `browser.context.switch_to_window(handle)`,
        `with browser.context.frame("name"):`,
        `browser.context.wait.for_alert(...)`.
        """
        from tquality_selenium.container import SeleniumServices
        from tquality_selenium.services.context_manager import ContextManager
        return SeleniumServices.get_service(ContextManager)

    def open(self, url: str) -> None:
        self._driver.get(url)

    def find_element(self, by: str, value: str) -> WebElement:
        return self._driver.find_element(by, value)

    def find_elements(self, by: str, value: str) -> list[WebElement]:
        return self._driver.find_elements(by, value)

    def quit(self) -> None:
        self._driver.quit()
        type(self)._started.set(False)

    # --- helpers (static; override in subclass via `@staticmethod` of same
    #     name; вызовы внутри идут через `self.X(...)`, polymorphism сохранён)

    @staticmethod
    def _find_chrome_binary() -> str | None:
        """Найти исполняемый Chrome/Chromium на текущей ОС.

        undetected-chromedriver ищет только в PATH, что ломает macOS
        (Chrome в /Applications/) и Windows (Chrome в Program Files).
        Спрашиваем Selenium Manager - он умеет находить бинарник на всех
        поддерживаемых ОС.
        """
        for binary in (
            "google-chrome", "google-chrome-stable", "chromium",
            "chromium-browser", "chrome",
        ):
            path = shutil.which(binary)
            if path:
                return path
        try:
            from selenium.webdriver.common.selenium_manager import SeleniumManager

            result = SeleniumManager().binary_paths(["--browser", "chrome"])
        except Exception:  # noqa: BLE001 - SeleniumManager падает по-разному
            result = {}
        browser_path = result.get("browser_path")
        if isinstance(browser_path, str) and os.path.isfile(browser_path):
            return browser_path
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

    @staticmethod
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

    @staticmethod
    def _copy_chromedriver_to_own_cache(sm_path: str) -> str:
        """Скопировать SM-chromedriver в собственный кэш.

        UC патчит chromedriver in-place. Если патчить SM-исходник, ломается
        Apple-подпись бинарника, общего с обычным Chrome (Gatekeeper потом
        убивает regular Chrome сигналом SIGKILL). Чтобы изолировать UC от
        SM-кэша, копируем в `~/.cache/tquality-py-selenium/chromedriver/`
        c сохранением platform/version-структуры пути (version-aware кэш).
        """
        sm_path_obj = pathlib.Path(sm_path)
        own_root = (
            pathlib.Path.home() / ".cache" / "tquality-py-selenium" / "chromedriver"
        )
        own_path = own_root.joinpath(*sm_path_obj.parts[-3:])
        if not own_path.exists():
            own_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(sm_path, own_path)
            own_path.chmod(0o755)
        return str(own_path)

    @staticmethod
    def _enable_bidi(opts: ArgOptions) -> None:
        """Запросить у драйвера WebSocket-URL для BiDi-сессии.

        Без этой возможности `driver.input`, `driver.browsing_context`,
        `driver.script` и прочие BiDi-сервисы падают с `Unable to find
        url to connect to from capabilities`.
        """
        opts.set_capability("webSocketUrl", True)

    @staticmethod
    def _apply_arguments(opts: ArgOptions, arguments: list[str]) -> None:
        """Добавить пользовательские CLI-аргументы из конфига к options."""
        for arg in arguments:
            opts.add_argument(arg)

    @staticmethod
    def _apply_linux_docker_chromium_flags(opts: ArgOptions) -> None:
        """Флаги для Chromium-based браузеров в Linux под Docker:
        `--no-sandbox` (sandbox конфликтует с root-юзером в контейнере)
        и `--disable-dev-shm-usage` (дефолтный /dev/shm в Docker 64MB,
        не хватает Chrome'у). На macOS/Windows не нужны и иногда ломают
        браузер (Edge на Windows с `--no-sandbox` падает с
        `DevToolsActivePort file doesn't exist`).
        """
        if sys.platform == "linux":
            opts.add_argument("--no-sandbox")
            opts.add_argument("--disable-dev-shm-usage")

    @staticmethod
    def _ensure_chromedriver_runnable(chromedriver_path: str) -> None:
        """Подготовить chromedriver-копию для UC.

        UC патчит chromedriver in-place (правит несколько байт для обхода
        антибот-детекции). На macOS патч ломает Apple-подпись бинарника, и
        Gatekeeper убивает процесс при старте сервиса сигналом SIGKILL
        (`Service ... unexpectedly exited. Status code was: -9`).

        Прогоняем патч заранее тем же `Patcher`, что использует UC, и сразу
        ad-hoc-подписываем результат через `codesign --sign -`.
        """
        from undetected_chromedriver.patcher import Patcher

        Patcher(executable_path=chromedriver_path).auto()
        if sys.platform == "darwin":
            subprocess.run(
                ["codesign", "--force", "--sign", "-", chromedriver_path],
                check=False,
            )


__all__ = [
    "BrowserNotSupportedError",
    "BrowserService",
]
