"""Сборщик BiDi-логов сети и JS-console-сообщений.

`BiDiLogCollector` хранит timestamped-буфер записей (network + js console)
для текущей сессии браузера, подписывается на BiDi-события через
`subscribe_to_events(browser.bidi)` и регистрирует step-hook'и на `Logger` через
`install_step_hooks(logger, logs_config)`. Step-hook на входе снимает
метку `now()`, на выходе вычитывает события, попавшие в окно, фильтрует
по `logs_config` и прикрепляет к шагу.

Форматирование и фильтрация - `@staticmethod` на этом же классе:
`format_network` / `format_js` разворачивают событие в multi-line текст,
`filter_records` применяет whitelist/blacklist regex-правила,
`format_attachment` склеивает с size-truncate.
"""
from __future__ import annotations

import re
import time
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from tquality_core import Logger, Step

    from tquality_selenium.config import LogsConfig
    from tquality_selenium.services.bidi_actions import BiDiBrowserActions


class BiDiLogCollector:
    """Timestamped-буфер network + JS-console событий для одной сессии.

    Жизненный цикл:
    ```
    collector = BiDiLogCollector()
    collector.subscribe_to_events(browser.bidi)    # на BiDi-события
    collector.install_step_hooks(logger, cfg)      # на step lifecycle
    # ... тесты идут ...
    collector.stop()                               # снять и то, и другое
    ```
    """

    _SNAPSHOT_ATTR = "_bidi_log_snapshot"

    def __init__(self, *, clock: Callable[[], float] | None = None) -> None:
        self._clock = clock or time.monotonic
        self._network: list[tuple[float, str]] = []
        self._js: list[tuple[float, str]] = []
        self._unsubscribe_bidi: Callable[[], None] | None = None
        self._unregister_hooks: Callable[[], None] | None = None

    # --- buffer ----------------------------------------------------------

    def now(self) -> float:
        """Текущий тик clock'а - нижняя граница для `drain_*_since`."""
        return self._clock()

    def add_network(self, event: dict[str, Any]) -> None:
        self._network.append((self._clock(), self.format_network(event)))

    def add_js(self, event: dict[str, Any]) -> None:
        self._js.append((self._clock(), self.format_js(event)))

    def drain_network_since(self, timestamp: float) -> list[str]:
        return [s for t, s in self._network if t >= timestamp]

    def drain_js_since(self, timestamp: float) -> list[str]:
        return [s for t, s in self._js if t >= timestamp]

    # --- wiring ----------------------------------------------------------

    def subscribe_to_events(
        self, bidi: BiDiBrowserActions,
    ) -> BiDiLogCollector:
        """Подписать сборщик на BiDi-события через `BiDiBrowserActions`-фасад.

        Все обращения в BiDi идут через `bidi.network` / `bidi.script` -
        единая точка композиции, не напрямую в `driver.X`. Падения
        отдельных подписок (сервис недоступен / API сменился) тихо
        пропускаются. Возвращает self для чейнинга.
        """
        unsubs: list[Callable[[], None]] = []

        try:
            net = bidi.network
            net_id = net.add_event_handler(
                "response_completed",
                lambda evt: self.add_network(self._network_event_to_dict(evt)),
            )
            unsubs.append(
                lambda: net.remove_event_handler("response_completed", net_id),
            )
        except Exception:  # noqa: BLE001
            pass

        try:
            script = bidi.script
            con_id = script.add_console_message_handler(
                lambda evt: self.add_js(self._js_console_event_to_dict(evt)),
            )
            unsubs.append(lambda: script.remove_console_message_handler(con_id))
        except Exception:  # noqa: BLE001
            pass

        try:
            script = bidi.script
            err_id = script.add_javascript_error_handler(
                lambda evt: self.add_js(self._js_error_event_to_dict(evt)),
            )
            unsubs.append(lambda: script.remove_javascript_error_handler(err_id))
        except Exception:  # noqa: BLE001
            pass

        def _unsub_all() -> None:
            for u in unsubs:
                try:
                    u()
                except Exception:  # noqa: BLE001
                    pass

        self._unsubscribe_bidi = _unsub_all
        return self

    def stop(self) -> None:
        """Снять и подписки на BiDi-события, и step-hook'и - полный teardown."""
        if self._unsubscribe_bidi is not None:
            self._unsubscribe_bidi()
            self._unsubscribe_bidi = None
        if self._unregister_hooks is not None:
            self._unregister_hooks()
            self._unregister_hooks = None

    def install_step_hooks(
        self, logger: Logger, logs_config: LogsConfig,
    ) -> BiDiLogCollector:
        """Зарегистрировать enter/exit-hooks для прикрепления собранных логов.

        Enter снимает `now()` как нижнюю границу окна шага. Exit вычитывает
        события, фильтрует через `logs_config.{network,js}.filters` /
        `ignored_patterns`, форматирует с `size_limit`, прикрепляет к
        allure-шагу и пишет в `logger.info`. Каналы в режиме `never` -
        пропускаются; `on_fail` - только при падении.
        """
        import allure

        from tquality_selenium.config import LogMode

        def _enter(step: Step) -> None:
            setattr(step, self._SNAPSHOT_ATTR, self.now())

        def _exit(
            step: Step,
            exc_type: type[BaseException] | None,
            exc_val: BaseException | None,
        ) -> None:
            snapshot = getattr(step, self._SNAPSHOT_ATTR, None)
            if snapshot is None:
                return
            failed = exc_type is not None
            channels = (
                ("network", self.drain_network_since, logs_config.network),
                ("js", self.drain_js_since, logs_config.js),
            )
            for name, drain, channel_cfg in channels:
                if channel_cfg.mode == LogMode.NEVER:
                    continue
                if channel_cfg.mode == LogMode.ON_FAIL and not failed:
                    continue
                records = drain(snapshot)
                filtered = self.filter_records(
                    records, channel_cfg.filters, channel_cfg.ignored_patterns,
                )
                if not filtered:
                    continue
                payload = self.format_attachment(filtered, channel_cfg.size_limit)
                label = f"BiDi {name} logs [{step.title}]"
                try:
                    allure.attach(
                        payload, name=label,
                        attachment_type=allure.attachment_type.TEXT,
                    )
                except Exception:  # noqa: BLE001
                    pass
                logger.info("%s\n%s", label, payload)

        unreg_enter = logger.register_step_enter_hook(_enter)
        unreg_exit = logger.register_step_exit_hook(_exit)

        def _unregister_both() -> None:
            unreg_enter()
            unreg_exit()

        self._unregister_hooks = _unregister_both
        return self

    # --- formatting / filtering (static) --------------------------------

    @staticmethod
    def format_network(event: dict[str, Any]) -> str:
        """Развернуть network-событие в multi-line текстовый record.

        Метод/URL/статус, request/response-заголовки, request/response-тело.
        Каждое поле на своей строке - чтобы regex-фильтр пользователя
        матчился против любого из них в одном проходе.
        """
        method = event.get("method", "?")
        url = event.get("url", "")
        status = event.get("status")
        duration = event.get("duration_ms")

        head = f"{method} {url}"
        if status is not None:
            head += f" -> {status}"
        if duration is not None:
            head += f" ({duration}ms)"
        lines = [head]

        for key, value in (event.get("request_headers") or {}).items():
            lines.append(f"  > {key}: {value}")
        req_body = event.get("request_body")
        if req_body:
            lines.append(f"  > body: {req_body}")
        for key, value in (event.get("response_headers") or {}).items():
            lines.append(f"  < {key}: {value}")
        resp_body = event.get("response_body")
        if resp_body:
            lines.append(f"  < body: {resp_body}")
        return "\n".join(lines)

    @staticmethod
    def format_js(event: dict[str, Any]) -> str:
        """`[level] text` - однострочный JS-console record."""
        level = event.get("level", "log")
        text = event.get("text", "")
        return f"[{level}] {text}"

    @staticmethod
    def filter_records(
        records: list[str],
        filters: list[str],
        ignored_patterns: list[str],
    ) -> list[str]:
        """Whitelist/blacklist precedence:

        - `filters` non-empty + match -> keep (whitelist explicit allow);
        - `filters` non-empty + no match -> drop;
        - `filters` empty + `ignored_patterns` match -> drop;
        - `filters` empty + no match -> keep.

        Pattern - `re.search`-семантика: достаточно подстроки-матча в
        любом месте record (multi-line). `[".*"]` пропускает всё.
        """
        if filters:
            compiled = [re.compile(p) for p in filters]
            return [r for r in records if any(c.search(r) for c in compiled)]
        compiled = [re.compile(p) for p in ignored_patterns]
        return [r for r in records if not any(c.search(r) for c in compiled)]

    @staticmethod
    def format_attachment(records: list[str], size_limit: int) -> str:
        """Склеить через пустую строку, обрезать по `size_limit` символов.

        Records, не влезающие в лимит, пропускаются; в конце добавляется
        `... [truncated N entries]`.
        """
        sep = "\n\n"
        chunks: list[str] = []
        used = 0
        dropped = 0
        for r in records:
            cost = len(r) + (len(sep) if chunks else 0)
            if used + cost > size_limit:
                dropped += 1
                continue
            chunks.append(r)
            used += cost
        out = sep.join(chunks)
        if dropped:
            out += f"\n\n... [truncated {dropped} entries]"
        return out

    # --- event -> dict (static, defensive) ------------------------------

    @staticmethod
    def _headers_to_dict(headers: Any) -> dict[str, str]:
        if headers is None:
            return {}
        if isinstance(headers, dict):
            return {str(k): str(v) for k, v in headers.items()}
        try:
            return {str(h.name): str(h.value) for h in headers}
        except (AttributeError, TypeError):
            return {}

    @classmethod
    def _network_event_to_dict(cls, evt: Any) -> dict[str, Any]:
        request = getattr(evt, "request", None)
        response = getattr(evt, "response", None)
        return {
            "method": getattr(request, "method", None) or "?",
            "url": getattr(request, "url", None) or "",
            "status": getattr(response, "status", None),
            "request_headers": cls._headers_to_dict(
                getattr(request, "headers", None),
            ),
            "response_headers": cls._headers_to_dict(
                getattr(response, "headers", None),
            ),
        }

    @staticmethod
    def _js_console_event_to_dict(evt: Any) -> dict[str, Any]:
        text_parts: list[str] = []
        for arg in getattr(evt, "args", []) or []:
            val = getattr(arg, "value", None)
            text_parts.append(str(val) if val is not None else str(arg))
        text = (
            " ".join(text_parts)
            if text_parts
            else str(getattr(evt, "text", evt))
        )
        return {
            "level": getattr(evt, "level", None) or getattr(evt, "type", "log"),
            "text": text,
        }

    @staticmethod
    def _js_error_event_to_dict(evt: Any) -> dict[str, Any]:
        text = (
            getattr(evt, "text", None)
            or getattr(evt, "message", None)
            or str(evt)
        )
        return {"level": "error", "text": str(text)}


__all__ = ["BiDiLogCollector"]
