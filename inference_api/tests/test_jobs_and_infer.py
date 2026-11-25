"""Unit tests for JobQueue lifecycle, GeoTransform, mask polygonization, and GeoJSON output."""

import json
import math
import threading
import time
import uuid
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import torch

import infer
from jobs import Job, JobQueue, JobQueueFull, JobStatus


def test_job_queue_uuid_and_lifecycle():
    queue = JobQueue(max_pending=2)
    release = threading.Event()

    def worker(job: Job) -> None:
        release.wait(timeout=2.0)
        job.tiles = 1
        job.affected = 5
        job.unaffected = 10

    submitted = queue.submit("new-orleans", worker)
    parsed_uuid = uuid.UUID(submitted.id)
    assert str(parsed_uuid) == submitted.id
    assert parsed_uuid.version == 4

    # Wait briefly for worker thread to enter RUNNING state while release is unset.
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline and submitted.status == JobStatus.QUEUED:
        time.sleep(0.01)
    assert submitted.status in (JobStatus.QUEUED, JobStatus.RUNNING)

    release.set()
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline and submitted.status != JobStatus.SUCCEEDED:
        time.sleep(0.01)

    assert submitted.status == JobStatus.SUCCEEDED
    assert submitted.finished_at is not None
    assert submitted.duration_seconds is not None
    assert queue.active_count() == 0
    assert queue.get(submitted.id) is submitted
    assert queue.list(limit=5)[0].id == submitted.id


def test_job_queue_failure_and_capacity_limit():
    queue = JobQueue(max_pending=1)
    gate = threading.Event()

    def blocking_worker(_job: Job) -> None:
        gate.wait(timeout=2.0)

    first = queue.submit("zone-a", blocking_worker)
    with pytest.raises(JobQueueFull):
        queue.submit("zone-b", blocking_worker)

    gate.set()
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline and first.status != JobStatus.SUCCEEDED:
        time.sleep(0.01)

    def failing_worker(_job: Job) -> None:
        raise ValueError("corrupted tile")

    failed = queue.submit("zone-c", failing_worker)
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline and failed.status == JobStatus.QUEUED or failed.status == JobStatus.RUNNING:
        time.sleep(0.01)

    assert failed.status == JobStatus.FAILED
    assert failed.error == "ValueError: corrupted tile"


def test_geotransform_mask_and_geojson_contract(tmp_path: Path):
    from conftest import make_geotiff_bytes

    tiff_path = tmp_path / "sample.tif"
    tiff_path.write_bytes(make_geotiff_bytes(lon=-90.0, lat=30.0, scale=1e-4))

    transform = infer.GeoTransform.from_geotiff(tiff_path)
    lon, lat = transform.pixel_to_lonlat(100, 50, ratio=1.0)
    assert math.isclose(lon, -89.99)
    assert math.isclose(lat, 29.995)

    plain_tif = tmp_path / "not_geo.tif"
    from PIL import Image
    Image.new("RGB", (16, 16)).save(plain_tif, format="TIFF")
    with pytest.raises(infer.InferenceError):
        infer.GeoTransform.from_geotiff(plain_tif)

    mask = np.zeros((100, 100), dtype=np.uint8)
    mask[20:50, 20:50] = infer.FOOTPRINT_CLASS
    mask[0:4, 0:4] = infer.FOOTPRINT_CLASS
    polygons = infer.mask_to_polygons(mask, min_area=50.0)
    assert len(polygons) == 1

    ring = infer.project_ring(polygons[0], transform, ratio=1.0)
    assert ring[0] == ring[-1]
    assert len(ring) >= 4

    features = infer.demo_features(center_lat=29.96, center_lng=-90.10, count=12, zone="unit-zone")
    out_path = tmp_path / "out" / "structures-affected.geojson"
    count = infer.write_geojson(features, out_path)
    assert count == 12

    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["type"] == "FeatureCollection"
    for feat in payload["features"]:
        assert feat["type"] == "Feature"
        assert len(feat["bbox"]) == 4
        assert feat["bbox"][0] < feat["bbox"][2]
        assert feat["bbox"][1] < feat["bbox"][3]
        assert feat["properties"]["severity"] in ("severe", "moderate", "none")
        assert 0.0 <= feat["properties"]["damage_probability"] <= 1.0
        assert 0.0 <= feat["properties"]["confidence"] <= 1.0


def test_damage_scores_four_class_vocab_mapping():
    class DummyModel(torch.nn.Module):
        def __init__(self, logits):
            super().__init__()
            self.anchor = torch.nn.Parameter(torch.zeros(1))
            self._logits = torch.tensor([logits], dtype=torch.float32)

        def forward(self, _x):
            return self._logits

    vocab = ["destroyed", "major-damage", "minor-damage", "no-damage"]
    severe_learner = SimpleNamespace(
        model=DummyModel([6.0, 0.1, 0.1, 0.1]),
        dls=SimpleNamespace(vocab=vocab),
    )
    crop = np.zeros((32, 32, 3), dtype=np.uint8)
    severe_res = infer.damage_scores(severe_learner, crop)
    assert severe_res["class"] == infer.DAMAGED_LABEL
    assert severe_res["severity"] == "severe"
    assert severe_res["damage_class"] == "destroyed"

    moderate_learner = SimpleNamespace(
        model=DummyModel([0.1, 2.5, 2.4, 0.2]),
        dls=SimpleNamespace(vocab=vocab),
    )
    moderate_res = infer.damage_scores(moderate_learner, crop)
    assert moderate_res["class"] == infer.DAMAGED_LABEL
    assert moderate_res["severity"] == "moderate"
    assert moderate_res["damage_class"] == "major-damage"
