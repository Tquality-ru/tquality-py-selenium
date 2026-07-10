"""Тесты `BiDiLogCollector`, фильтрации и форматирования.

Покрытие:
- precedence-правила `BiDiLogCollector.filter_records` (whitelist > blacklist, граничные
  случаи `[]` и `[".*"]`);
- collection-семантика collector'а (timestamps, drain-since, раздельные
  буферы network/js);
- truncation в `BiDiLogCollector.format_attachment`;
- regex-фильтрация по разным полям record'а (URL, заголовки, тело,
  статус);
- real-world сценарии: drop static assets, keep API errors only,
  whitelist-precedence над blacklist.
"""
from __future__ import annotations

from tquality_selenium.services.bidi_log_collector import BiDiLogCollector

# --- BiDiLogCollector.filter_records: precedence ----------------------------------------------


def test_empty_filters_and_ignored_keeps_everything() -> None:
    """`filters=[]`, `ignored_patterns=[]` - все записи проходят."""
    records = ["alpha", "beta", "gamma"]
    assert BiDiLogCollector.filter_records(records, filters=[], ignored_patterns=[]) == records


def test_match_all_whitelist_keeps_everything() -> None:
    """`filters=[".*"]` - `.*` матчит всё, эквивалент no-filter."""
    records = ["alpha", "beta", "gamma"]
    assert BiDiLogCollector.filter_records(records, filters=[".*"], ignored_patterns=[]) == records


def test_match_all_whitelist_overrides_blacklist() -> None:
    """`[".*"]` whitelist приоритетнее blacklist - всё остаётся."""
    records = ["good", "spam", "fine"]
    kept = BiDiLogCollector.filter_records(records, filters=[".*"], ignored_patterns=["spam"])
    assert kept == records


def test_non_empty_whitelist_keeps_only_matches() -> None:
    records = ["error: critical", "info: routine", "warn: minor"]
    kept = BiDiLogCollector.filter_records(records, filters=["error|warn"], ignored_patterns=[])
    assert kept == ["error: critical", "warn: minor"]


def test_non_empty_whitelist_no_match_drops_all() -> None:
    records = ["foo", "bar"]
    assert BiDiLogCollector.filter_records(records, filters=["baz"], ignored_patterns=[]) == []


def test_blacklist_drops_matches_when_whitelist_empty() -> None:
    records = ["spam: A", "good: B", "spam: C", "good: D"]
    kept = BiDiLogCollector.filter_records(records, filters=[], ignored_patterns=["spam"])
    assert kept == ["good: B", "good: D"]


def test_whitelist_precedence_over_blacklist_explicit() -> None:
    """Запись, матчащаяся одновременно whitelist и blacklist, остаётся."""
    records = ["important spam", "just spam", "important"]
    kept = BiDiLogCollector.filter_records(
        records, filters=["important"], ignored_patterns=["spam"],
    )
    assert kept == ["important spam", "important"]


# --- BiDiLogCollector: collection mechanics ---------------------------------


def test_drain_since_returns_only_newer_records() -> None:
    """`drain_*_since(t)` возвращает только события с timestamp >= t."""
    ticks = iter([10.0, 20.0, 30.0])
    collector = BiDiLogCollector(clock=lambda: next(ticks))
    collector.add_js({"text": "first"})
    collector.add_js({"text": "second"})
    collector.add_js({"text": "third"})

    drained = collector.drain_js_since(20.0)
    assert len(drained) == 2
    assert "first" not in drained[0]
    assert "second" in drained[0]
    assert "third" in drained[1]


def test_separate_buffers_for_network_and_js() -> None:
    collector = BiDiLogCollector(clock=lambda: 0.0)
    collector.add_network({"method": "GET", "url": "/api"})
    collector.add_js({"text": "hello"})
    assert len(collector.drain_network_since(0.0)) == 1
    assert len(collector.drain_js_since(0.0)) == 1


def test_now_returns_current_clock_tick() -> None:
    """`now()` для снимка перед шагом возвращает текущее значение clock'а."""
    collector = BiDiLogCollector(clock=lambda: 42.0)
    assert collector.now() == 42.0


# --- BiDiLogCollector.format_attachment: truncation ------------------------------------------


def test_format_attachment_joins_records_with_blank_line() -> None:
    out = BiDiLogCollector.format_attachment(["a", "b", "c"], size_limit=1000)
    assert out == "a\n\nb\n\nc"


def test_format_attachment_truncates_past_limit() -> None:
    """Records, не влезающие в size_limit, отбрасываются с маркером."""
    out = BiDiLogCollector.format_attachment(["aaaaa", "bbbbb", "ccccc"], size_limit=15)
    # "aaaaa" (5) + "\n\nbbbbb" (7) = 12. "\n\nccccc" (7) -> 19 > 15: drop
    assert "aaaaa" in out
    assert "bbbbb" in out
    assert "ccccc" not in out
    assert "truncated 1 entries" in out


def test_format_attachment_empty_records() -> None:
    assert BiDiLogCollector.format_attachment([], size_limit=1000) == ""


# --- Regex-фильтрация по разным полям record'а --------------------------


def test_filter_matches_url() -> None:
    collector = BiDiLogCollector(clock=lambda: 0.0)
    collector.add_network({"method": "GET", "url": "https://api.example.com/items/42"})
    collector.add_network({"method": "GET", "url": "https://api.example.com/users/7"})
    records = collector.drain_network_since(0.0)
    kept = BiDiLogCollector.filter_records(records, filters=[r"/items/\d+"], ignored_patterns=[])
    assert len(kept) == 1
    assert "/items/42" in kept[0]


def test_filter_matches_request_header() -> None:
    collector = BiDiLogCollector(clock=lambda: 0.0)
    collector.add_network({
        "method": "GET", "url": "/api",
        "request_headers": {"X-Auth-Token": "secret123", "Accept": "application/json"},
    })
    collector.add_network({"method": "GET", "url": "/other"})
    records = collector.drain_network_since(0.0)
    kept = BiDiLogCollector.filter_records(records, filters=["X-Auth-Token"], ignored_patterns=[])
    assert len(kept) == 1
    assert "/api" in kept[0]


def test_filter_matches_response_header() -> None:
    collector = BiDiLogCollector(clock=lambda: 0.0)
    collector.add_network({
        "method": "GET", "url": "/api/feed",
        "response_headers": {"Content-Type": "application/xml; charset=utf-8"},
    })
    collector.add_network({
        "method": "GET", "url": "/api/items",
        "response_headers": {"Content-Type": "application/json"},
    })
    records = collector.drain_network_since(0.0)
    kept = BiDiLogCollector.filter_records(records, filters=[r"application/xml"], ignored_patterns=[])
    assert len(kept) == 1
    assert "/api/feed" in kept[0]


def test_filter_matches_request_body() -> None:
    collector = BiDiLogCollector(clock=lambda: 0.0)
    collector.add_network({
        "method": "POST", "url": "/api/orders",
        "request_body": '{"qty": 3, "promo": "SUMMER25"}',
    })
    collector.add_network({"method": "GET", "url": "/api/items"})
    records = collector.drain_network_since(0.0)
    kept = BiDiLogCollector.filter_records(records, filters=[r"SUMMER\d+"], ignored_patterns=[])
    assert len(kept) == 1
    assert "/api/orders" in kept[0]


def test_filter_matches_response_body() -> None:
    collector = BiDiLogCollector(clock=lambda: 0.0)
    collector.add_network({
        "method": "GET", "url": "/api/items/42",
        "response_body": '{"id": 42, "error": "not found"}',
    })
    records = collector.drain_network_since(0.0)
    kept = BiDiLogCollector.filter_records(
        records, filters=[r'"error":\s*"not found"'], ignored_patterns=[],
    )
    assert len(kept) == 1


def test_filter_matches_status_code() -> None:
    """Filter по HTTP-статусу через паттерн в заголовочной строке."""
    collector = BiDiLogCollector(clock=lambda: 0.0)
    collector.add_network({"method": "GET", "url": "/api/a", "status": 200})
    collector.add_network({"method": "GET", "url": "/api/b", "status": 404})
    collector.add_network({"method": "GET", "url": "/api/c", "status": 503})
    records = collector.drain_network_since(0.0)
    failed = BiDiLogCollector.filter_records(records, filters=[r"-> [45]\d\d"], ignored_patterns=[])
    assert len(failed) == 2
    assert all("/api/a" not in r for r in failed)


def test_filter_matches_js_console_level() -> None:
    collector = BiDiLogCollector(clock=lambda: 0.0)
    collector.add_js({"level": "info", "text": "Page loaded"})
    collector.add_js({"level": "warn", "text": "Deprecated API"})
    collector.add_js({"level": "error", "text": "Uncaught TypeError"})
    records = collector.drain_js_since(0.0)
    kept = BiDiLogCollector.filter_records(records, filters=[r"\[(warn|error)\]"], ignored_patterns=[])
    assert len(kept) == 2
    assert all("Page loaded" not in r for r in kept)


# --- Real-world сценарии ----------------------------------------------------


def test_realworld_drop_static_assets_keep_api() -> None:
    """Drop HTML / images / videos, keep JSON / XML API responses."""
    collector = BiDiLogCollector(clock=lambda: 0.0)
    collector.add_network({"method": "GET", "url": "https://app/index.html"})
    collector.add_network({"method": "GET", "url": "https://app/static/logo.png"})
    collector.add_network({"method": "GET", "url": "https://app/static/banner.jpeg"})
    collector.add_network({"method": "GET", "url": "https://app/static/icon.svg"})
    collector.add_network({"method": "GET", "url": "https://app/media/promo.mp4"})
    collector.add_network({"method": "GET", "url": "https://app/api/items.json"})
    collector.add_network({"method": "POST", "url": "https://app/api/feed.xml"})

    records = collector.drain_network_since(0.0)
    static_assets = [
        r"\.html(\?|$|\s)",
        r"\.(png|jpe?g|gif|webp|svg|ico)\b",
        r"\.(mp4|webm|mov|m4v)\b",
    ]
    kept = BiDiLogCollector.filter_records(records, filters=[], ignored_patterns=static_assets)

    assert len(kept) == 2
    assert any("/api/items.json" in r for r in kept)
    assert any("/api/feed.xml" in r for r in kept)


def test_realworld_keep_only_failures() -> None:
    """Combined: 4xx/5xx network responses + JS console errors."""
    collector = BiDiLogCollector(clock=lambda: 0.0)
    collector.add_network({"method": "GET", "url": "/api/ok", "status": 200})
    collector.add_network({"method": "POST", "url": "/api/bad", "status": 400})
    collector.add_network({"method": "GET", "url": "/api/broken", "status": 503})
    collector.add_js({"level": "info", "text": "Loaded"})
    collector.add_js({"level": "warn", "text": "Slow"})
    collector.add_js({"level": "error", "text": "Crash"})

    failed_net = BiDiLogCollector.filter_records(
        collector.drain_network_since(0.0),
        filters=[r"-> [45]\d\d"], ignored_patterns=[],
    )
    failed_js = BiDiLogCollector.filter_records(
        collector.drain_js_since(0.0),
        filters=[r"\[error\]"], ignored_patterns=[],
    )
    assert len(failed_net) == 2
    assert len(failed_js) == 1


def test_realworld_drop_noisy_health_polling() -> None:
    """Empty whitelist + blacklist для конкретных noisy-endpoints."""
    collector = BiDiLogCollector(clock=lambda: 0.0)
    collector.add_network({"method": "GET", "url": "/api/items"})
    collector.add_network({"method": "GET", "url": "/api/health"})
    collector.add_network({"method": "GET", "url": "/api/metrics"})
    collector.add_network({"method": "POST", "url": "/api/orders"})

    records = collector.drain_network_since(0.0)
    kept = BiDiLogCollector.filter_records(
        records, filters=[],
        ignored_patterns=[r"/api/(health|metrics)\b"],
    )
    assert len(kept) == 2
    assert all("health" not in r and "metrics" not in r for r in kept)


def test_realworld_whitelist_precedence_keeps_blacklisted() -> None:
    """Если record матчит whitelist - blacklist игнорируется (whitelist wins).

    Demonstrates the contract: user wanting to drop a subset from a
    permissive whitelist must adjust the whitelist itself, not rely on
    blacklist to override.
    """
    collector = BiDiLogCollector(clock=lambda: 0.0)
    collector.add_network({"method": "GET", "url": "/api/items"})
    collector.add_network({"method": "GET", "url": "/api/health"})

    records = collector.drain_network_since(0.0)
    kept = BiDiLogCollector.filter_records(
        records,
        filters=[r"/api/"],
        ignored_patterns=[r"/health"],
    )
    assert len(kept) == 2
    assert any("/api/health" in r for r in kept)


def test_realworld_pii_blacklist_drops_auth_tokens_from_log() -> None:
    """Real-world: blacklist по PII/secrets - drop record целиком, если палится."""
    collector = BiDiLogCollector(clock=lambda: 0.0)
    collector.add_network({
        "method": "POST", "url": "/api/login",
        "request_headers": {"Authorization": "Bearer eyJ0eXAi..."},
    })
    collector.add_network({"method": "GET", "url": "/api/items"})

    records = collector.drain_network_since(0.0)
    kept = BiDiLogCollector.filter_records(
        records, filters=[],
        ignored_patterns=[r"Authorization:\s*Bearer", r"/api/login"],
    )
    assert len(kept) == 1
    assert "/api/items" in kept[0]
