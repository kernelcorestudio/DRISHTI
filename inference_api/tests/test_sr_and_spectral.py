"""Regression tests for NETRA SR, Spectral Indices, GeoTIFF export, Blockchain, and core RAHAT edge cases."""

import io
import json
import sys
from pathlib import Path

import numpy as np
import pytest
import tifffile

INFERENCE_API_DIR = Path(__file__).resolve().parents[1]
if str(INFERENCE_API_DIR) not in sys.path:
    sys.path.insert(0, str(INFERENCE_API_DIR))

import infer  # noqa: E402
import main  # noqa: E402
from backend.api import routes as sr_routes  # noqa: E402
from backend.models.sr_engine import SREngine  # noqa: E402
from backend.spectral.spectral_indices import spectral_engine  # noqa: E402
from conftest import make_geotiff_bytes  # noqa: E402


def test_spectral_fallback_without_spyndex(monkeypatch):
    import backend.spectral.spectral_indices as spectral_mod

    monkeypatch.setattr(spectral_mod, "spyndex", None)
    bands = {
        "B02": np.full((8, 8), 0.1, dtype=np.float32),
        "B03": np.full((8, 8), 0.3, dtype=np.float32),
        "B04": np.full((8, 8), 0.2, dtype=np.float32),
        "B08": np.full((8, 8), 0.6, dtype=np.float32),
        "B11": np.full((8, 8), 0.4, dtype=np.float32),
        "B12": np.full((8, 8), 0.15, dtype=np.float32),
    }

    ndvi = spectral_engine.compute_index("ndvi", bands)
    ndwi = spectral_engine.compute_index("ndwi", bands)
    ndbi = spectral_engine.compute_index("ndbi", bands)
    nbr = spectral_engine.compute_index("nbr", bands)

    assert ndvi.shape == (8, 8) and np.allclose(ndvi, 0.5, atol=1e-4)
    assert np.allclose(ndwi, -1.0 / 3.0, atol=1e-4)
    assert np.allclose(ndbi, -0.2, atol=1e-4)
    assert np.allclose(nbr, 0.6, atol=1e-4)


def test_sr_engine_unsharp_and_model_switches():
    engine = SREngine(scale_factor=4, model_name="hat")
    uint8_img = np.full((16, 16, 3), 120, dtype=np.uint8)
    sharpened = engine.apply_unsharp_mask(uint8_img, radius=1.0, amount=1.2)
    assert sharpened.dtype == np.float32
    assert float(sharpened.max()) < 0.6  # Must not saturate 120/255 to 1.0

    small_lr = np.random.RandomState(42).rand(16, 16, 3).astype(np.float32) * 0.4 + 0.1
    for name in ("carn", "srm_net", "swinir", "hat"):
        engine.switch_model(model_name=name, scale_factor=4)
        out = engine.predict(small_lr, use_tiling=False)
        assert out.shape == (64, 64, 3), f"{name} produced {out.shape}"
        assert 0.0 <= float(out.min()) <= float(out.max()) <= 1.0


def test_sr_spectral_infra_geotiff_and_blockchain_flow(isolated_api, monkeypatch):
    client = isolated_api["client"]

    # Deterministic small synthetic 10-band tile so the test never waits for network/large tiling
    small_tile = np.full((16, 16, 10), 0.2, dtype=np.float32)
    small_tile[:, :, 0] = 0.15  # B04
    small_tile[:, :, 1] = 0.25  # B03
    small_tile[:, :, 2] = 0.10  # B02
    small_tile[:, :, 3] = 0.55  # B08

    monkeypatch.setattr(
        sr_routes.copernicus_client,
        "fetch_sentinel2_tile",
        lambda *a, **kw: (small_tile, {"source": "test_cache", "bbox": [75.3, 30.55, 75.36, 30.6]}),
    )

    presets_res = client.get("/api/sr/presets")
    assert presets_res.status_code == 200
    presets = presets_res.json()["presets"]
    assert presets and "name" in presets[0] and "title" in presets[0]

    # Fetch without explicit bbox (frontend contract)
    fetch_res = client.post("/api/sr/fetch-tile", json={"preset_id": "punjab_agri"})
    assert fetch_res.status_code == 200
    fetch_data = fetch_res.json()
    assert fetch_data["lr_preview"].startswith("data:image/png;base64,")
    assert fetch_data["preview_base64"] == fetch_data["lr_preview"]

    # Run SR with mc_samples alias and unsharp/sharpen toggle
    sr_res = client.post(
        "/api/sr/superresolve",
        json={"model_name": "srm_net", "scale_factor": 4, "mc_samples": 2, "apply_unsharp": True},
    )
    assert sr_res.status_code == 200
    sr_data = sr_res.json()
    assert sr_data["sr_preview"].startswith("data:image/png;base64,")
    assert sr_data["confidence_heatmap_preview"].startswith("data:image/png;base64,")
    assert 0.0 <= sr_data["mean_confidence"] <= 1.0
    assert sr_data["blockchain_record"]["sha256"].startswith("0x")

    # Blockchain verification against current session must MATCH
    verify_res = client.get("/api/sr/blockchain/verify/punjab_agri")
    assert verify_res.status_code == 200
    assert verify_res.json()["result"]["status"] == "MATCH"

    # Spectral visualize must return legend_items list + gradient_css
    vis_res = client.post("/api/sr/visualize", json={"mode": "ndvi", "apply_realesrgan_sharpen": False})
    assert vis_res.status_code == 200
    vis_data = vis_res.json()
    assert isinstance(vis_data["legend_items"], list) and len(vis_data["legend_items"]) == 3
    assert "linear-gradient" in (vis_data["gradient_css"] or "")

    # Infrastructure detection must include total_built_area_km2 and aliases
    infra_res = client.post("/api/sr/detect-infrastructure", json={})
    assert infra_res.status_code == 200
    infra_data = infra_res.json()
    assert "total_built_area_km2" in infra_data
    assert "building_count" in infra_data
    assert "total_road_length_km" in infra_data

    # GeoTIFF download via tifffile (zero GDAL) must return valid multi-band float32 TIFF
    tif_res = client.get("/api/sr/download/geotiff")
    assert tif_res.status_code == 200
    assert tif_res.headers["content-type"].startswith("image/tiff")
    arr = tifffile.imread(io.BytesIO(tif_res.content))
    assert arr.shape[:2] == (64, 64)


def test_core_inference_edge_cases_and_api_prefix(isolated_api, tmp_path: Path):
    client = isolated_api["client"]
    data_dir: Path = isolated_api["data_dir"]

    # Non-dict GeoJSON (list literal) must not crash /diagnostics
    bad_zone = data_dir / "weird-zone"
    bad_zone.mkdir()
    (bad_zone / "structures-affected.geojson").write_text("[]", encoding="utf-8")

    diag = client.get("/api/diagnostics")
    assert diag.status_code == 200

    # Invalid TIFF bytes with .tif extension must return 400 and leave no orphan work dir
    bad_res = client.post(
        "/api/predict/disaster?zone_id=valid-zone",
        files={
            "before_image": ("before.tif", b"not-a-tiff", "image/tiff"),
            "after_image": ("after.tif", make_geotiff_bytes(), "image/tiff"),
        },
    )
    assert bad_res.status_code == 400
    assert list(main.settings.work_dir.iterdir()) == []

    # Dotted model stem must still resolve .pkl suffix
    assert infer.export_path(Path("v1.2_model")) == Path("v1.2_model.pkl")

    # Padded mask_to_polygons detects buildings touching tile edges and projects non-square ratios
    edge_mask = np.zeros((40, 80), dtype=np.uint8)
    edge_mask[0:20, 0:25] = infer.FOOTPRINT_CLASS
    polys = infer.mask_to_polygons(edge_mask, min_area=50.0)
    assert len(polys) == 1
    tf = infer.GeoTransform(x_offset=10.0, x_scale=0.001, y_offset=20.0, y_scale=-0.001)
    lon, lat = tf.pixel_to_lonlat(80.0, 40.0, ratio=2.0, ratio_y=1.0)
    assert np.isclose(lon, 10.04) and np.isclose(lat, 19.96)
