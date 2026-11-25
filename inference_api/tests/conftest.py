"""Shared fixtures and ASGI client helpers for RAHAT inference API tests."""

import asyncio
import io
import json
import sys
from pathlib import Path
from typing import Any, Dict

import httpx
import numpy as np
import pytest
from PIL import Image, TiffImagePlugin

INFERENCE_API_DIR = Path(__file__).resolve().parents[1]
if str(INFERENCE_API_DIR) not in sys.path:
    sys.path.insert(0, str(INFERENCE_API_DIR))

import main  # noqa: E402
from jobs import JobQueue  # noqa: E402


class SyncASGIClient:
    """Synchronous wrapper over httpx.ASGITransport for FastAPI + httpx>=0.28 compatibility."""

    def __init__(self, app: Any) -> None:
        self.app = app

    def request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        async def _send() -> httpx.Response:
            transport = httpx.ASGITransport(app=self.app)
            async with httpx.AsyncClient(
                transport=transport,
                base_url="http://testserver",
            ) as client:
                return await client.request(method, url, **kwargs)

        return asyncio.run(_send())

    def get(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("POST", url, **kwargs)


def make_geotiff_bytes(
    width: int = 64,
    height: int = 64,
    lon: float = -90.02,
    lat: float = 29.96,
    scale: float = 1e-5,
) -> bytes:
    """Builds a minimal north-up GeoTIFF in memory with ModelTiePoint/ModelPixelScale tags."""
    rgb = np.zeros((height, width, 3), dtype=np.uint8)
    rgb[16:48, 16:48] = (200, 180, 160)
    image = Image.fromarray(rgb, mode="RGB")

    info = TiffImagePlugin.ImageFileDirectory_v2()
    info[33922] = (0.0, 0.0, 0.0, float(lon), float(lat), 0.0)
    info[33550] = (float(scale), float(scale), 0.0)

    buffer = io.BytesIO()
    image.save(buffer, format="TIFF", tiffinfo=info)
    return buffer.getvalue()


@pytest.fixture()
def isolated_api(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Dict[str, Any]:
    """Isolates main.settings and main.queue to temporary directories for each test."""
    data_dir = tmp_path / "data"
    work_dir = tmp_path / "work"
    model_dir = tmp_path / "models"
    tile_root = tmp_path / "tiles"
    data_dir.mkdir()
    work_dir.mkdir()
    model_dir.mkdir()
    tile_root.mkdir()

    # Seed one zone with valid affected/unaffected GeoJSON so /diagnostics has real counts.
    demo_zone = data_dir / "test-zone"
    demo_zone.mkdir()
    (demo_zone / "structures-affected.geojson").write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {"type": "Feature", "properties": {"severity": "severe"}},
                    {"type": "Feature", "properties": {"severity": "moderate"}},
                ],
            }
        ),
        encoding="utf-8",
    )
    (demo_zone / "structures-unaffected.geojson").write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {"type": "Feature", "properties": {"severity": "none"}},
                ],
            }
        ),
        encoding="utf-8",
    )

    # Seed one offline tile so imagery_inventory() exercises zoom parsing.
    tile_path = tile_root / "test-zone" / "before" / "17" / "10"
    tile_path.mkdir(parents=True)
    Image.new("RGB", (8, 8), (120, 140, 160)).save(tile_path / "20.png")

    monkeypatch.setattr(main.settings, "mode", "demo")
    monkeypatch.setattr(main.settings, "data_dir", data_dir)
    monkeypatch.setattr(main.settings, "work_dir", work_dir)
    monkeypatch.setattr(main.settings, "model_dir", model_dir)
    monkeypatch.setattr(main.settings, "geoserv_url", "http://127.0.0.1:59999")
    monkeypatch.setattr(main.settings, "max_upload_bytes", 10 * 1024 * 1024)
    monkeypatch.setattr(main.settings, "max_jobs", 4)
    monkeypatch.setattr(main.settings, "min_area", 20.0)
    monkeypatch.setattr(main, "TILE_ROOT", tile_root)
    monkeypatch.setattr(main, "queue", JobQueue(max_pending=4))

    return {
        "client": SyncASGIClient(main.app),
        "data_dir": data_dir,
        "work_dir": work_dir,
        "model_dir": model_dir,
        "tile_root": tile_root,
    }
