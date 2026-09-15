"""Regression tests for per-user and per-group request throttling."""

import json
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from astrbot_plugin_get_px.main import GetPxPlugin


def _plugin(*, user_seconds: int = 0, group_seconds: int = 0) -> GetPxPlugin:
    plugin = object.__new__(GetPxPlugin)
    plugin.config = {
        "runtime": {
            "rate_limit_seconds": user_seconds,
            "group_rate_limit_seconds": group_seconds,
        }
    }
    plugin._last_request = {}
    plugin._last_group_request = {}
    return plugin


def test_user_rate_limit_accepts_configured_3600_second_maximum() -> None:
    plugin = _plugin(user_seconds=3600)

    with patch(
        "astrbot_plugin_get_px.main.time.monotonic", side_effect=[10000.0, 10001.0]
    ):
        assert plugin._check_rate_limit("user-1") == 0
        assert plugin._check_rate_limit("user-1") == 3600


def test_group_rate_limit_is_shared_by_members_of_the_same_group() -> None:
    plugin = _plugin(group_seconds=300)

    with patch(
        "astrbot_plugin_get_px.main.time.monotonic", side_effect=[10000.0, 10010.0]
    ):
        assert plugin._check_rate_limit("user-1", "group-1") == 0
        assert plugin._check_rate_limit("user-2", "group-1") == 291


def test_group_rate_limit_does_not_affect_private_or_other_group_requests() -> None:
    plugin = _plugin(group_seconds=300)

    with patch(
        "astrbot_plugin_get_px.main.time.monotonic",
        side_effect=[10000.0, 10001.0, 10002.0, 10003.0],
    ):
        assert plugin._check_rate_limit("user-1", "group-1") == 0
        assert plugin._check_rate_limit("user-2", "") == 0
        assert plugin._check_rate_limit("user-3", "group-2") == 0
        assert plugin._check_rate_limit("user-4", "group-1") == 298


def test_runtime_rate_limit_schema_exposes_both_0_to_3600_sliders() -> None:
    schema_path = Path(__file__).resolve().parents[1] / "_conf_schema.json"
    runtime = json.loads(schema_path.read_text(encoding="utf-8"))["runtime"]["items"]

    assert runtime["rate_limit_seconds"]["slider"] == {
        "min": 0,
        "max": 3600,
        "step": 1,
    }
    assert runtime["group_rate_limit_seconds"] == {
        "description": "群请求频率限制（秒）",
        "type": "int",
        "default": 0,
        "slider": {"min": 0, "max": 3600, "step": 1},
        "hint": "同一群内两次请求的最小间隔，设为 0 禁用。防止群内刷屏。",
    }
