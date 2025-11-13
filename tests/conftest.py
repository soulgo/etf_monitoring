"""
Pytest fixtures for testing configuration and adapters.
"""

import json
import pytest
from pathlib import Path


@pytest.fixture
def tmp_config_path(tmp_path: Path) -> Path:
    path = tmp_path / "config.json"
    return path


@pytest.fixture
def write_config(tmp_config_path: Path):
    def _write(data: dict):
        tmp_config_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return tmp_config_path
    return _write

