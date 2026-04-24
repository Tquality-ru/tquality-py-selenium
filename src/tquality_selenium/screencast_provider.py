"""Screencast-провайдер: запись GIF на время выполнения шага.

Фоновый поток берет `driver.get_screenshot_as_png()` с интервалом
`frame_interval` (сек) и аккумулирует кадры. На `stop()` все кадры
собираются в анимированный GIF через Pillow.

Selenium WebDriver thread-safe для read-операций (screenshots - HTTP),
поэтому параллельные действия теста и снимки не конфликтуют.
"""
from __future__ import annotations

import base64
import contextvars
import io
import threading
import time
from typing import Any, Callable

from PIL import Image
from selenium.webdriver.remote.webdriver import WebDriver


class SeleniumScreencastProvider:
    """Реализует `tquality_core.ScreencastProvider` через periodic-скриншоты."""

    def __init__(
        self,
        driver_resolver: Callable[[], WebDriver],
        availability_check: Callable[[], bool],
        frame_interval: float = 0.2,
        max_duration: float = 120.0,
    ) -> None:
        self._driver_resolver = driver_resolver
        self._is_available_cb = availability_check
        self._frame_interval = frame_interval
        self._max_duration = max_duration
        # Пара (PNG-байты, timestamp) - timestamp используется для
        # вычисления длительности показа каждого кадра в итоговом GIF.
        self._frames: list[tuple[bytes, float]] = []
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def is_available(self) -> bool:
        return self._is_available_cb()

    def mime_type(self) -> str:
        return "image/gif"

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
        """Остановить сбор кадров, вернуть GIF-байты или None если кадров нет."""
        if self._thread is None:
            return None
        self._stop_event.set()
        self._thread.join(timeout=5.0)
        self._thread = None
        frames = self._frames
        self._frames = []
        if not frames:
            return None
        return self._to_gif(frames)

    def _capture_loop(self) -> None:
        """Тикает с интервалом `frame_interval` и накапливает скриншоты.

        Пока сессия драйвера неактивна - просто ждем следующего тика.
        Не создаем новый драйвер и не блокируем главный поток.
        Для каждого кадра сохраняет реальный timestamp - итоговый GIF
        будет проигрываться с таймингами, соответствующими реальному
        времени выполнения шага (не влияет скорость `get_screenshot`).
        """
        started = time.monotonic()
        while (
            not self._stop_event.is_set()
            and time.monotonic() - started < self._max_duration
        ):
            if self._is_available_cb():
                try:
                    png = self._capture_frame(self._driver_resolver())
                    if png is not None:
                        self._frames.append((png, time.monotonic()))
                except Exception:  # noqa: BLE001 - сессия могла закрыться
                    pass
            self._stop_event.wait(self._frame_interval)

    @staticmethod
    def _capture_frame(driver: WebDriver) -> bytes | None:
        """Снять кадр через WebDriver BiDi (кросс-браузерный стандарт W3C).

        BiDi `browsingContext.captureScreenshot` не ждет document.readyState
        и не блокируется во время навигации - ловит промежуточные состояния
        UI включая красные рамки выделения. Работает в Chrome/Chromium,
        Firefox, Edge.

        Если BiDi недоступен (старый Selenium, Safari) - fallback на
        классический `get_screenshot_as_png`.
        """
        try:
            bc: Any = driver.browsing_context
            b64 = bc.capture_screenshot(driver.current_window_handle)
            if isinstance(b64, str):
                return base64.b64decode(b64)
        except Exception:  # noqa: BLE001 - BiDi может быть недоступен
            pass
        return driver.get_screenshot_as_png()

    def _to_gif(self, frames: list[tuple[bytes, float]]) -> bytes:
        """Собрать GIF из PNG-кадров через Pillow.

        Длительность показа каждого кадра вычисляется по разнице
        timestamp'ов - так плеер воспроизводит с реальной скоростью теста.
        Последний кадр держится `frame_interval` по умолчанию.
        Кадры шире 800px даунскейлятся (сохраняя пропорции).
        """
        images: list[Image.Image] = []
        for png, _ts in frames:
            img: Image.Image = Image.open(io.BytesIO(png))
            if img.width > 800:
                ratio = 800 / img.width
                img = img.resize(
                    (800, int(img.height * ratio)),
                    Image.Resampling.LANCZOS,
                )
            images.append(img.convert("P", palette=Image.Palette.ADAPTIVE))

        durations_ms: list[int] = []
        for i in range(len(frames) - 1):
            delta = frames[i + 1][1] - frames[i][1]
            durations_ms.append(max(1, int(delta * 1000)))
        durations_ms.append(int(self._frame_interval * 1000))

        buf = io.BytesIO()
        images[0].save(
            buf,
            format="GIF",
            save_all=True,
            append_images=images[1:],
            duration=durations_ms,
            loop=0,
            optimize=True,
        )
        return buf.getvalue()
