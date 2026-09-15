"""Regression tests for configurable image message construction."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from astrbot_plugin_get_px.pixiv.search import SearchMixin


class _Harness(SearchMixin):
    def __init__(self, value: object):
        self.value = value

    def _cfg_str(self, key: str, default: str = "") -> str:
        assert key == "image_send_method"
        return str(self.value or default)


@pytest.mark.parametrize(
    ("configured", "expected"),
    [("url", "url"), ("file", "file"), ("byte", "byte"), ("invalid", "file")],
)
def test_image_send_method_accepts_supported_values_and_falls_back(
    configured, expected
):
    assert _Harness(configured)._image_send_method() == expected


@pytest.mark.asyncio
async def test_image_component_uses_url_without_local_file_access() -> None:
    component = await _Harness("url")._build_image_component(
        "https://example.com/image.jpg", "url"
    )

    assert component.file == "https://example.com/image.jpg"
    assert component.path == ""


@pytest.mark.asyncio
async def test_image_component_uses_file_path(tmp_path: Path) -> None:
    image_path = tmp_path / "image.jpg"
    image_path.write_bytes(b"image-data")

    component = await _Harness("file")._build_image_component(
        str(image_path), "file"
    )

    assert component.path == str(image_path)
    assert component.file.startswith("file://")


@pytest.mark.asyncio
async def test_image_component_uses_base64_bytes(tmp_path: Path) -> None:
    image_path = tmp_path / "image.jpg"
    image_path.write_bytes(b"image-data")

    component = await _Harness("byte")._build_image_component(
        str(image_path), "byte"
    )

    assert component.file == "base64://aW1hZ2UtZGF0YQ=="
    assert component.path == ""


def test_image_send_method_schema_matches_reference_options() -> None:
    schema_path = Path(__file__).resolve().parents[1] / "_conf_schema.json"
    item = json.loads(schema_path.read_text(encoding="utf-8"))["pixiv_source"][
        "items"
    ]["image_send_method"]

    assert item == {
        "description": "图片发送方式",
        "type": "string",
        "default": "file",
        "options": ["url", "file", "byte"],
        "hint": (
            "url=直接通过 URL 发送（最快，不下载），file=下载后通过文件路径发送，"
            "byte=下载后通过 Base64 发送。URL 模式不执行文件大小检查和原图自动降级。"
        ),
    }
