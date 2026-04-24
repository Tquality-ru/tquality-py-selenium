"""Тесты для CLI-команд tquality-selenium-config."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tquality_selenium.cli import main
from tquality_selenium.schema import SELENIUM_SCHEMA_URL


def test_init_creates_config_with_core_and_selenium_defaults(tmp_path: Path) -> None:
    exit_code = main(["init", "--path", str(tmp_path)])

    assert exit_code == 0
    config_file = tmp_path / "config.json"
    assert config_file.exists()

    data = json.loads(config_file.read_text(encoding="utf-8"))
    assert data["$schema"] == SELENIUM_SCHEMA_URL
    # Поля ядра
    assert data["base_url"] == "http://localhost"
    assert data["default_timeout"] == 10.0
    assert data["log_dir"] == "logs"
    assert data["highlight_elements"] is False
    # Selenium-специфичные поля - per-browser блоки + selector + screencast
    assert data["browser"] == "chrome"
    for key in ("chrome", "firefox", "edge", "safari", "undetected_chrome"):
        assert data[key]["headless"] is True
        assert data[key]["page_load_timeout"] == 30.0
        assert data[key]["window_width"] == 1920
        assert data[key]["window_height"] == 1080
    assert data["screencast"]["fps"] == 10
    assert data["screencast"]["frame_interval"] == 0.2


def test_init_refuses_to_overwrite_without_force(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    config_file = tmp_path / "config.json"
    config_file.write_text('{"base_url": "https://custom"}', encoding="utf-8")

    exit_code = main(["init", "--path", str(tmp_path)])

    assert exit_code == 1
    assert "уже существует" in capsys.readouterr().err
    assert config_file.read_text(encoding="utf-8") == '{"base_url": "https://custom"}'


def test_init_overwrites_with_force(tmp_path: Path) -> None:
    config_file = tmp_path / "config.json"
    config_file.write_text('{"base_url": "https://custom"}', encoding="utf-8")

    exit_code = main(["init", "--path", str(tmp_path), "--force"])

    assert exit_code == 0
    data = json.loads(config_file.read_text(encoding="utf-8"))
    assert data["base_url"] == "http://localhost"
    assert data["browser"] == "chrome"


def test_schema_writes_file(tmp_path: Path) -> None:
    exit_code = main(["schema", "--path", str(tmp_path)])

    assert exit_code == 0
    schema_file = tmp_path / "schema" / "config.schema.json"
    assert schema_file.exists()

    data = json.loads(schema_file.read_text(encoding="utf-8"))
    assert data["$id"] == SELENIUM_SCHEMA_URL
    assert "base_url" in data["properties"]
    assert "browser" in data["properties"]
