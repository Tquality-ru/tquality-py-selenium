"""Реэкспорт core-`Waiter` ради устойчивого пути импорта.

Сам класс - в `tquality_core.services.waiter`: чистый polling-цикл,
без selenium. Драйвер прокидывается в condition через `DriverWaiter`
(см. `driver_waiter.py`).
"""
from tquality_core import Waiter, WaitTimeoutError

__all__ = ["Waiter", "WaitTimeoutError"]
