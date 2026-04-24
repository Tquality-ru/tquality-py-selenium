"""Screencast-провайдер: запись webm на время выполнения шага.

Фоновый поток захватывает кадры через WebDriver BiDi
(`browsingContext.captureScreenshot`), снимая их с интервалом
`frame_interval` (сек). На `stop()` все кадры кодируются в webm (VP9)
через imageio-ffmpeg - тот сам приносит бинарник ffmpeg, внешних
зависимостей нет.

Webm меньше и резче GIF для длинных экранных записей и напрямую
проигрывается в allure-отчетах (тег video).
"""
from __future__ import annotations

import base64
import contextvars
import io
import logging
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Callable

import imageio.v3 as iio
import numpy as np
from PIL import Image
from selenium.webdriver.remote.webdriver import WebDriver

from tquality_selenium.config import SeleniumConfig

_log = logging.getLogger(__name__)

# Процесс-уровневые флаги "один раз ворнинг": не засорять лог на каждый
# кадр, но и не молчать. Сбрасываются при новом процессе.
_BIDI_FALLBACK_WARNED = False
_CDP_FALLBACK_WARNED = False


class SeleniumScreencastProvider:
    """Реализует `tquality_core.ScreencastProvider`.

    Кадры пишутся в webm (VP9) через imageio-ffmpeg. Выходная частота
    кадров фиксирована (`output_fps`); каждый реальный кадр повторяется
    столько output-тиков, сколько реально прожил до следующего - так
    воспроизведение идет в темпе теста, включая паузы на навигацию.
    """

    def __init__(
        self,
        driver_resolver: Callable[[], WebDriver],
        availability_check: Callable[[], bool],
        config: SeleniumConfig,
    ) -> None:
        self._driver_resolver = driver_resolver
        self._is_available_cb = availability_check
        self._frame_interval = config.screencast.frame_interval
        self._max_duration = config.screencast.max_duration
        self._output_fps = config.screencast.fps
        self._max_width = config.screencast.max_width
        # Пара (PNG-байты, timestamp) - timestamp используется для
        # вычисления длительности показа каждого кадра в итоговом видео.
        self._frames: list[tuple[bytes, float]] = []
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def is_available(self) -> bool:
        return self._is_available_cb()

    def mime_type(self) -> str:
        return "video/webm"

    def start(self) -> None:
        """Запустить фоновый сбор кадров. Повторный вызов игнорируется.

        Поток стартует с копией текущего `contextvars.Context`, чтобы
        `ContextLocalSingleton` и `is_browser_started` видели уже созданный
        в главном потоке BrowserService - иначе тред открыл бы второе окно.
        """
        if self._thread is not None and self._thread.is_alive():
            return
        self._frames = []
        self._stop_event = threading.Event()
        ctx = contextvars.copy_context()
        self._thread = threading.Thread(
            target=lambda: ctx.run(self._capture_loop),
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> bytes | None:
        """Остановить сбор кадров, вернуть webm-байты или None, если нет."""
        if self._thread is None:
            return None
        self._stop_event.set()
        self._thread.join(timeout=5.0)
        self._thread = None
        frames = self._frames
        self._frames = []
        if not frames:
            _log.warning("Screencast: ни один кадр не захвачен - запись пуста")
            return None
        duration = frames[-1][1] - frames[0][1]
        _log.info(
            "Screencast: %d кадров, %.2fs (%.1f кадр/с)",
            len(frames), duration,
            (len(frames) - 1) / duration if duration > 0 else 0,
        )
        try:
            return self._to_webm(frames)
        except Exception as exc:  # noqa: BLE001
            _log.warning(
                "Screencast: не удалось закодировать webm - запись потеряна: %s",
                exc,
            )
            return None

    def _capture_loop(self) -> None:
        """Тикает с интервалом `frame_interval` и накапливает скриншоты.

        Пока сессия драйвера неактивна - просто ждем следующего тика.
        Не создаем новый драйвер и не блокируем главный поток.
        Для каждого кадра сохраняет реальный timestamp - итоговое видео
        проигрывается с таймингами, соответствующими реальному времени
        выполнения шага.
        """
        started = time.monotonic()
        warned_capture_error = False
        while (
            not self._stop_event.is_set()
            and time.monotonic() - started < self._max_duration
        ):
            if self._is_available_cb():
                try:
                    png = self._capture_frame(self._driver_resolver())
                    if png is not None:
                        self._frames.append((png, time.monotonic()))
                except Exception as exc:  # noqa: BLE001
                    if not warned_capture_error:
                        warned_capture_error = True
                        _log.warning(
                            "Screencast: ошибка захвата кадра, "
                            "оставшиеся кадры будут пропущены если повторится: %s",
                            exc,
                        )
            self._stop_event.wait(self._frame_interval)

    @staticmethod
    def _capture_frame(driver: WebDriver) -> bytes | None:
        """Снять кадр.

        Иерархия способов (по убыванию предпочтительности):

        1. WebDriver BiDi `browsingContext.captureScreenshot` - W3C-стандарт,
           кросс-браузерный, не ждет document.readyState.
        2. CDP `Page.captureScreenshot` - только Chromium (Chrome/Edge/UC),
           не блокируется во время навигации; нужен когда BiDi не включен в
           capabilities драйвера (напр. undetected-chromedriver).
        3. Классический `get_screenshot_as_png` - работает везде, но ждет
           readyState='complete' и может "слепнуть" во время навигации.

        На каждый фолбек пишем warning ровно один раз за процесс.
        """
        # 1. BiDi
        try:
            bc: Any = driver.browsing_context
            b64 = bc.capture_screenshot(driver.current_window_handle)
            if isinstance(b64, str):
                return base64.b64decode(b64)
        except Exception as exc:  # noqa: BLE001 - BiDi может быть недоступен
            global _BIDI_FALLBACK_WARNED
            if not _BIDI_FALLBACK_WARNED:
                _BIDI_FALLBACK_WARNED = True
                _log.warning(
                    "BiDi browsingContext.captureScreenshot недоступен (%s); "
                    "пробую CDP / fallback",
                    exc,
                )

        # 2. CDP (Chromium only)
        cdp: Any = getattr(driver, "execute_cdp_cmd", None)
        if cdp is not None:
            try:
                result = cdp("Page.captureScreenshot", {"format": "png"})
                data = result.get("data") if isinstance(result, dict) else None
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

        # 3. Classic
        return driver.get_screenshot_as_png()

    def _to_webm(self, frames: list[tuple[bytes, float]]) -> bytes:
        """Собрать webm (VP9) из PNG-кадров через imageio-ffmpeg.

        Каждый захваченный кадр повторяется в выходе столько раз,
        сколько нужно чтобы занять его реальную длительность при
        фиксированной `output_fps`. Кадры шире `max_width` даунскейлятся
        с сохранением пропорций.
        """
        frame_tick = 1.0 / self._output_fps
        rgb_frames: list[np.ndarray] = []
        for idx, (png, ts) in enumerate(frames):
            next_ts = (
                frames[idx + 1][1]
                if idx + 1 < len(frames)
                else ts + self._frame_interval
            )
            repeat = max(1, round((next_ts - ts) / frame_tick))

            img = Image.open(io.BytesIO(png)).convert("RGB")
            if img.width > self._max_width:
                ratio = self._max_width / img.width
                img = img.resize(
                    (self._max_width, int(img.height * ratio)),
                    Image.Resampling.LANCZOS,
                )
            # ffmpeg-кодек требует четные размеры для yuv420p.
            w, h = img.size
            if w % 2 or h % 2:
                img = img.resize((w - w % 2, h - h % 2), Image.Resampling.LANCZOS)

            arr = np.asarray(img)
            rgb_frames.extend([arr] * repeat)

        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            iio.imwrite(
                tmp_path,
                np.stack(rgb_frames),
                fps=self._output_fps,
                codec="libvpx-vp9",
                output_params=["-b:v", "0", "-crf", "32"],
            )
            return tmp_path.read_bytes()
        finally:
            try:
                tmp_path.unlink()
            except OSError:
                pass
