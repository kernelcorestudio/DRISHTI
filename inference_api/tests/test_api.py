"""API integration tests for FastAPI endpoints in inference_api/main.py."""

import json
import time
import urllib.request
import uuid
from pathlib import Path

import pytest

import infer
import main
from conftest import make_geotiff_bytes
from jobs import JobQueue


def test_health_degraded_and_ready(isolated_api, monkeypatch):
    client = isolated_api["client"]

    # Default test geoserv URL is unreachable -> degraded.
    res_down = client.get("/health")
    assert res_down.status_code == 200
    body_down = res_down.json()
    assert body_down["status"] == "degraded"
    assert body_down["mode"] == "demo"
    assert body_down["geoserv_reachable"] is False

    # Simulate reachable GeoServ -> ready in demo mode.
    class FakeResp:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **kw: FakeResp())
    res_ready = client.get("/health")
    assert res_ready.status_code == 200
    body_ready = res_ready.json()
    assert body_ready["status"] == "ready"
    assert body_ready["geoserv_reachable"] is True
    assert body_ready["missing_models"] == []

    # Real mode with empty model_dir -> degraded with two missing_models.
    monkeypatch.setattr(main.settings, "mode", "real")
    res_missing = client.get("/health")
    assert res_missing.status_code == 200
    body_missing = res_missing.json()
    assert body_missing["status"] == "degraded"
    assert len(body_missing["missing_models"]) == 2


def test_diagnostics_endpoint_reports_inventory(isolated_api):
    client = isolated_api["client"]
    res = client.get("/diagnostics")
    assert res.status_code == 200
    data = res.json()

    assert data["mode"] == "demo"
    assert data["min_area"] == 20.0
    assert data["max_upload_mb"] == 10
    assert len(data["models"]) == 2
    assert data["queue"] == {"active": 0, "max": 4}

    assert len(data["zones"]) == 1
    zone = data["zones"][0]
    assert zone["zone_id"] == "test-zone"
    assert zone["layers"]["structures-affected"]["features"] == 2
    assert zone["layers"]["structures-affected"]["severity"] == {"severe": 1, "moderate": 1}
    assert zone["layers"]["structures-unaffected"]["features"] == 1

    assert len(data["imagery"]) == 1
    assert data["imagery"][0]["roles"]["before"]["tiles"] == 1
    assert data["imagery"][0]["roles"]["before"]["by_zoom"] == {"17": 1}
    assert "footprint_iou_mean" in data["evaluation"]


def test_predict_disaster_validation_errors(isolated_api, monkeypatch):
    client = isolated_api["client"]
    tiff = make_geotiff_bytes()

    # Invalid zone_id patterns -> 400.
    for bad_zone in ("../escape", "BadUpper", "-leading-dash"):
        res = client.post(
            f"/predict/disaster?zone_id={bad_zone}",
            files={
                "before_image": ("before.tif", tiff, "image/tiff"),
                "after_image": ("after.tif", tiff, "image/tiff"),
            },
        )
        assert res.status_code == 400

    # Real mode without model files -> 503.
    monkeypatch.setattr(main.settings, "mode", "real")
    res_503 = client.post(
        "/predict/disaster?zone_id=valid-zone",
        files={
            "before_image": ("before.tif", tiff, "image/tiff"),
            "after_image": ("after.tif", tiff, "image/tiff"),
        },
    )
    assert res_503.status_code == 503
    monkeypatch.setattr(main.settings, "mode", "demo")

    # Non-GeoTIFF extension -> 400.
    res_ext = client.post(
        "/predict/disaster?zone_id=valid-zone",
        files={
            "before_image": ("before.png", b"pngbytes", "image/png"),
            "after_image": ("after.tif", tiff, "image/tiff"),
        },
    )
    assert res_ext.status_code == 400

    # Empty GeoTIFF upload -> 400.
    res_empty = client.post(
        "/predict/disaster?zone_id=valid-zone",
        files={
            "before_image": ("before.tif", b"", "image/tiff"),
            "after_image": ("after.tif", tiff, "image/tiff"),
        },
    )
    assert res_empty.status_code == 400

    # Oversized upload -> 413.
    monkeypatch.setattr(main.settings, "max_upload_bytes", 128)
    res_big = client.post(
        "/predict/disaster?zone_id=valid-zone",
        files={
            "before_image": ("before.tif", tiff, "image/tiff"),
            "after_image": ("after.tif", tiff, "image/tiff"),
        },
    )
    assert res_big.status_code == 413


def test_predict_disaster_demo_e2e_and_job_polling(isolated_api, monkeypatch):
    client = isolated_api["client"]
    data_dir: Path = isolated_api["data_dir"]
    tiff = make_geotiff_bytes(lon=-95.63, lat=29.84)

    reload_calls = []
    monkeypatch.setattr(
        infer,
        "reload_geoserv",
        lambda url, timeout=30.0: reload_calls.append(url) or {"status": "reloaded"},
    )

    submit = client.post(
        "/predict/disaster?zone_id=demo-run-zone",
        files={
            "before_image": ("before.tif", tiff, "image/tiff"),
            "after_image": ("after.tif", tiff, "image/tiff"),
        },
    )
    assert submit.status_code == 202
    job_data = submit.json()
    job_id = job_data["job_id"]
    assert str(uuid.UUID(job_id)) == job_id
    assert job_data["zone_id"] == "demo-run-zone"

    # Poll until worker thread finishes.
    deadline = time.monotonic() + 5.0
    final_job = job_data
    while time.monotonic() < deadline:
        poll = client.get(f"/jobs/{job_id}")
        assert poll.status_code == 200
        final_job = poll.json()
        if final_job["status"] in ("succeeded", "failed"):
            break
        time.sleep(0.05)

    assert final_job["status"] == "succeeded"
    assert final_job["tiles"] == 1
    assert final_job["affected_structures"] + final_job["unaffected_structures"] == main.DEMO_STRUCTURES
    assert final_job["warning"] is None
    assert reload_calls == ["http://127.0.0.1:59999"]

    affected_path = data_dir / "demo-run-zone" / "structures-affected.geojson"
    unaffected_path = data_dir / "demo-run-zone" / "structures-unaffected.geojson"
    assert affected_path.exists()
    assert unaffected_path.exists()

    affected_geojson = json.loads(affected_path.read_text(encoding="utf-8"))
    unaffected_geojson = json.loads(unaffected_path.read_text(encoding="utf-8"))
    assert affected_geojson["type"] == "FeatureCollection"
    assert len(affected_geojson["features"]) == final_job["affected_structures"]
    assert len(unaffected_geojson["features"]) == final_job["unaffected_structures"]
    assert all("bbox" in f and len(f["bbox"]) == 4 for f in affected_geojson["features"])

    # Verify /jobs lists the completed job and unknown IDs return 404.
    jobs_res = client.get("/jobs?limit=5")
    assert jobs_res.status_code == 200
    assert any(item["job_id"] == job_id for item in jobs_res.json())
    assert client.get("/jobs/nonexistent-id").status_code == 404


def test_predict_disaster_queue_full_returns_429(isolated_api, monkeypatch):
    client = isolated_api["client"]
    tiff = make_geotiff_bytes()

    saturated = JobQueue(max_pending=0)
    monkeypatch.setattr(main, "queue", saturated)

    res = client.post(
        "/predict/disaster?zone_id=busy-zone",
        files={
            "before_image": ("before.tif", tiff, "image/tiff"),
            "after_image": ("after.tif", tiff, "image/tiff"),
        },
    )
    assert res.status_code == 429
