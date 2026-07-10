"""Screencast-провайдер: запись webm на время выполнения шага.

Frame source - трёхуровневая лестница для съёмки кадра:

1. WebDriver BiDi `browsingContext.captureScreenshot` - W3C-стандарт,
   кросс-браузерный, не ждёт `document.readyState`.
2. CDP `Page.captureScreenshot` - только Chromium (Chrome/Edge/UC),
   не блокируется во время навигации; нужен, когда BiDi не включен
   в capabilities (например, undetected-chromedriver).
3. Классический `get_screenshot_as_png` - работает везде, но ждёт
   `readyState='complete'` и может «слепнуть» во время навигации.

На каждый фолбэк - один WARNING на процесс.

Сама склейка PNG-кадров в webm/VP9 и фоновый цикл - в
`tquality_core.WebmScreencastRecorder`; этот файл - только
адаптация frame source'а под selenium и проброс настроек из
`SeleniumConfig.screencast`.
"""

from __future__ import annotations

import base64
import logging
from typing import Any, Callable

from selenium.webdriver.common.bidi.browsing_context import BrowsingContext
from selenium.webdriver.remote.webdriver import WebDriver
from tquality_core import WebmScreencastRecorder
from tquality_core.services.webm_screencast import MIME_TYPE as _WEBM_MIME

from tquality_selenium.config import SeleniumConfig

_log = logging.getLogger(__name__)

_BIDI_FALLBACK_WARNED = False
_CDP_FALLBACK_WARNED = False


class SeleniumScreencastProvider:
    """Реализует `tquality_core.ScreencastProvider`."""

    def __init__(
        self,
        driver_resolver: Callable[[], WebDriver],
        availability_check: Callable[[], bool],
        config: SeleniumConfig,
    ) -> None:
        self._driver_resolver = driver_resolver
        self._is_available = availability_check
        cfg = config.screencast
        self._recorder = WebmScreencastRecorder(
            frame_source=self._capture_frame,
            availability_check=availability_check,
            frame_interval=cfg.frame_interval,
            output_fps=cfg.fps,
            max_width=cfg.max_width,
            max_duration=cfg.max_duration,
        )

    def is_available(self) -> bool:
        return self._is_available()

    def mime_type(self) -> str:
        return _WEBM_MIME

    def start(self) -> None:
        self._recorder.start()

    def stop(self) -> bytes | None:
        return self._recorder.stop()

    def _capture_frame(self) -> bytes | None:
        driver = self._driver_resolver()

        try:
            bc: BrowsingContext = driver.browsing_context
            b64 = bc.capture_screenshot(driver.current_window_handle)
            if isinstance(b64, str):
                return base64.b64decode(b64)
        except Exception as exc:  # noqa: BLE001 - BiDi может быть недоступен
            global _BIDI_FALLBACK_WARNED
            if not _BIDI_FALLBACK_WARNED:
                _BIDI_FALLBACK_WARNED = True
                _log.warning(
                    "BiDi browsingContext.captureScreenshot недоступен (%s); пробую CDP / fallback",
                    exc,
                )

        cdp: Callable[..., Any] | None = getattr(driver, "execute_cdp_cmd", None)
        if cdp is not None:
            try:
                cdp_result = cdp("Page.captureScreenshot", {"format": "png"})
                data = cdp_result.get("data") if isinstance(cdp_result, dict) else None
                if isinstance(data, str):
                    return base64.b64decode(data)
            except Exception as exc:  # noqa: BLE001
                global _CDP_FALLBACK_WARNED
                if not _CDP_FALLBACK_WARNED:
                    _CDP_FALLBACK_WARNED = True
                    _log.warning(
                        "CDP Page.captureScreenshot недоступен (%s); "
                        "использую классический get_screenshot_as_png - "
                        "кадры могут блокироваться во время навигации",
                        exc,
                    )

        png: bytes = driver.get_screenshot_as_png()
        return png
