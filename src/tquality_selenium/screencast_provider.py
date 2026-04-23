"""Screencast-провайдер: запись GIF на время выполнения шага.

Фоновый поток берет `driver.get_screenshot_as_png()` с интервалом
`frame_interval` (сек) и аккумулирует кадры. На `stop()` все кадры
собираются в анимированный GIF через Pillow.

Selenium WebDriver thread-safe для read-операций (screenshots - HTTP),
поэтому параллельные действия теста и снимки не конфликтуют.
"""
from __future__ import annotations

import io
import threading
from typing import Callable

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
        self._frames: list[bytes] = []
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def is_available(self) -> bool:
        return self._is_available_cb()

    def mime_type(self) -> str:
        return "image/gif"

    def start(self) -> None:
        """Запустить фоновый сбор кадров. Повторный вызов игнорируется."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._frames = []
        self._stop_event = threading.Event()
        self._thread = threading.Thread(
            target=self._capture_loop, daemon=True,
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
        """Тикает с интервалом `frame_interval` и накапливает скриншоты."""
        elapsed = 0.0
        while not self._stop_event.is_set() and elapsed < self._max_duration:
            try:
                png: bytes = self._driver_resolver().get_screenshot_as_png()
                self._frames.append(png)
            except Exception:  # noqa: BLE001 - драйвер может быть невалиден
                pass
            self._stop_event.wait(self._frame_interval)
            elapsed += self._frame_interval

    def _to_gif(self, frames: list[bytes]) -> bytes:
        """Собрать GIF из PNG-кадров через Pillow. Скейлим до ширины 800px."""
        images: list[Image.Image] = []
        for png in frames:
            img: Image.Image = Image.open(io.BytesIO(png))
            if img.width > 800:
                ratio = 800 / img.width
                img = img.resize(
                    (800, int(img.height * ratio)),
                    Image.Resampling.LANCZOS,
                )
            images.append(img.convert("P", palette=Image.Palette.ADAPTIVE))
        buf = io.BytesIO()
        images[0].save(
            buf,
            format="GIF",
            save_all=True,
            append_images=images[1:],
            duration=int(self._frame_interval * 1000),
            loop=0,
            optimize=True,
        )
        return buf.getvalue()
