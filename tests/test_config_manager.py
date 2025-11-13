"""
Tests for ConfigManager: load/save/sanitize/merge.
"""

import json
from pathlib import Path

import pytest

from src.config.manager import ConfigManager


def test_create_default_when_missing(tmp_config_path: Path):
    mgr = ConfigManager()
    assert mgr.load(str(tmp_config_path)) is True
    assert tmp_config_path.exists()
    data = json.loads(tmp_config_path.read_text(encoding="utf-8"))
    assert "config_version" in data


def test_load_invalid_json_fallback(tmp_path: Path):
    cfg = tmp_path / "broken.json"
    cfg.write_text("{ invalid json", encoding="utf-8")
    mgr = ConfigManager()
    ok = mgr.load(str(cfg))
    assert ok is False
    all_cfg = mgr.get_all()
    assert all_cfg["config_version"] == "1.0"


def test_sanitize_https_and_bounds(write_config):
    cfg = {
        "api_config": {
            "primary": {"name": "eastmoney", "base_url": "http://push2.eastmoney.com/api/qt/stock/get", "timeout": 5},
            "retry_count": 10,
            "failover_threshold": 100
        },
        "refresh_interval": 1,
        "floating_window": {"size": [50, 500]}
    }
    path = write_config(cfg)
    mgr = ConfigManager()
    mgr.load(str(path))
    merged = mgr.get_all()
    assert merged["api_config"]["primary"]["base_url"].startswith("https://")
    assert 0 <= merged["api_config"]["retry_count"] <= 5
    assert 1 <= merged["api_config"]["failover_threshold"] <= 10
    assert 3 <= merged["refresh_interval"] <= 30
    w, h = merged["floating_window"]["size"]
    assert 200 <= w <= 800
    assert 40 <= h <= 200


def test_atomic_save(write_config):
    cfg = {"log_level": "DEBUG"}
    path = write_config(cfg)
    mgr = ConfigManager()
    mgr.load(str(path))
    mgr.set("log_level", "INFO")
    saved = mgr.save()
    assert saved is True
    assert path.exists()
    assert path.suffix == ".json"
    assert not (path.with_suffix(".tmp")).exists()

