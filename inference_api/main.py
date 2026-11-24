"""
RAHAT live inference API.

Accepts one before/after GeoTIFF tile pair for a zone, queues the footprint + damage
pipeline (see infer.py) and publishes the resulting GeoJSON to GeoServ. Inference takes
minutes, so the request returns immediately with a job id and the work happens on a
background worker, one job at a time.

    POST /predict/disaster?zone_id=<zone>   multipart: before_image, after_image
    GET  /jobs/{job_id}                     poll status, counts and artifacts
    GET  /jobs                              most recent jobs, newest first
    GET  /health                            mode, model files, GeoServ reachability
    GET  /diagnostics                       read-only snapshot the dashboard renders

Configuration (environment variables):

    RAHAT_INFER_MODE=real|demo   demo writes synthetic detections instead of running the
                                 models, which is how the endpoint is exercised without a GPU
    RAHAT_DATA_DIR               GeoServ data directory (<data-dir>/<zone>/*.geojson)
    RAHAT_WORK_DIR               where uploads are kept (default ./work)
    RAHAT_MODEL_DIR              directory holding the two exported fastai learners
    RAHAT_GEOSERV_URL            default http://127.0.0.1:8088
    RAHAT_DEVICE                 torch device ("cpu", "cuda", "0"); empty uses the export's
    RAHAT_MAX_UPLOAD_MB          per-file upload cap (default 512)
    RAHAT_MAX_JOBS               queued + running jobs allowed at once (default 4)

Large scenes still have to be cut into tiles on a shared before/after grid first, with
data_gen/prepare_inference/create_tiles.py; this endpoint takes the tile pair, not a
30,000 pixel wide scene.
"""

import json
import logging
import os
import re
import shutil
import sys
import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = PACKAGE_DIR.parent
if str(PACKAGE_DIR) not in sys.path:
    sys.path.insert(0, str(PACKAGE_DIR))

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_DIR / ".env")
except ImportError:
    pass

from jobs import Job, JobQueue, JobQueueFull

logging.basicConfig(
    level=os.environ.get("RAHAT_LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
)
logger = logging.getLogger("inference_api")

ALLOWED_SUFFIXES = {".tif", ".tiff", ".gtiff"}
TIFF_MAGIC_HEADERS = (b"II*\x00", b"MM\x00*", b"II+\x00", b"MM\x00+")
WINDOWS_RESERVED_ZONE_NAMES = {
    "con", "prn", "aux", "nul",
    *(f"com{i}" for i in range(1, 10)),
    *(f"lpt{i}" for i in range(1, 10)),
}
ZONE_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
CHUNK_SIZE = 1 << 20
DEMO_STRUCTURES = 168


def _resolve_dir_env(var_name: str, default: Path, anchor: Path) -> Path:
    raw = os.environ.get(var_name, "").strip()
    if not raw:
        return default.resolve()
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = anchor / candidate
    return candidate.resolve()


class Settings:
    def __init__(self) -> None:
        self.mode = os.environ.get("RAHAT_INFER_MODE", "real").strip().lower()
        self.data_dir = _resolve_dir_env("RAHAT_DATA_DIR", PROJECT_DIR / "geoserv" / "test_data", PROJECT_DIR)
        self.work_dir = _resolve_dir_env("RAHAT_WORK_DIR", PACKAGE_DIR / "work", PACKAGE_DIR)
        self.model_dir = _resolve_dir_env("RAHAT_MODEL_DIR", PACKAGE_DIR / "models", PACKAGE_DIR)
        self.geoserv_url = os.environ.get("RAHAT_GEOSERV_URL", "http://127.0.0.1:8088").rstrip("/")
        self.device = os.environ.get("RAHAT_DEVICE", "").strip()
        self.max_upload_bytes = max(1, int(float(os.environ.get("RAHAT_MAX_UPLOAD_MB", "512")) * 1024 * 1024))
        self.max_jobs = max(1, int(os.environ.get("RAHAT_MAX_JOBS", "4")))
        # Polygons smaller than this (in 384-space mask pixels) are treated as speckle.
        # 20 is the measured optimum against xBD ground truth; see infer.DEFAULT_MIN_AREA.
        self.min_area = float(os.environ.get("RAHAT_MIN_AREA", "20"))

        if self.mode not in ("real", "demo"):
            raise ValueError(f"RAHAT_INFER_MODE must be 'real' or 'demo', got {self.mode!r}")

    @property
    def footprint_model(self) -> Path:
        return self.model_dir / "predict_footprint_fine_tuned.pkl"

    @property
    def damage_model(self) -> Path:
        # Retrained on Kaggle (4 xBD subtypes); exported with learn.export().
        return self.model_dir / "predict_damage_unfrozen.pkl"

    def missing_models(self) -> List[str]:
        # load_learner reads `<name>.pkl`, so the suffix has to be part of the check.
        return [str(path) for path in (self.footprint_model, self.damage_model) if not path.exists()]


settings = Settings()
queue = JobQueue(max_pending=settings.max_jobs)

app = FastAPI(
    title="RAHAT Live Inference API",
    description=(
        "Queues the RAHAT building footprint and damage pipeline for an uploaded "
        "before/after tile pair and publishes the GeoJSON to GeoServ."
    ),
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

core_router = APIRouter()

# Super-Resolution, Spectral Analysis & Blockchain Provenance (NETRA Integration)
try:
    if str(PACKAGE_DIR) not in sys.path:
        sys.path.insert(0, str(PACKAGE_DIR))
    from backend.api.routes import router as sr_router

    # /sr serves requests forwarded by Vue dev server proxy (which strips /api)
    app.include_router(sr_router, prefix="/sr", tags=["Super Resolution"])
    # /api/sr and /api serve direct or legacy requests
    app.include_router(sr_router, prefix="/api/sr", tags=["Super Resolution (Direct)"])
    app.include_router(sr_router, prefix="/api", tags=["NETRA API Compatibility"])
    logger.info("Super-Resolution & Spectral Analysis router registered successfully")
except Exception as sr_err:
    logger.warning("Could not register Super-Resolution router: %s", sr_err)


class JobResponse(BaseModel):
    job_id: str
    zone_id: str
    status: str
    created_at: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    tiles: int = 0
    affected_structures: int = 0
    unaffected_structures: int = 0
    severe_structures: int = 0
    moderate_structures: int = 0
    artifacts: List[str] = []
    error: Optional[str] = None
    warning: Optional[str] = None


def load_infer():
    """Imports infer.py lazily so the API can start (and report health) without torch."""
    if str(PACKAGE_DIR) not in sys.path:
        sys.path.insert(0, str(PACKAGE_DIR))

    import infer  # noqa: PLC0415 - intentional: heavy module, imported on first job

    return infer


def save_upload(upload: UploadFile, destination: Path, max_bytes: int) -> int:
    total = 0
    header = b""
    destination.parent.mkdir(parents=True, exist_ok=True)
    with open(destination, "wb") as output:
        while True:
            chunk = upload.file.read(CHUNK_SIZE)
            if not chunk:
                break
            if len(header) < 4:
                header += chunk[: 4 - len(header)]
            total += len(chunk)
            if total > max_bytes:
                output.close()
                destination.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=413,
                    detail=(
                        f"{upload.filename} exceeds the {max_bytes // (1024 * 1024)} MB upload limit"
                    ),
                )
            output.write(chunk)

    if total == 0:
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=f"{upload.filename} is empty")
    if header not in TIFF_MAGIC_HEADERS:
        destination.unlink(missing_ok=True)
        raise HTTPException(
            status_code=400,
            detail=f"{upload.filename} does not have a valid TIFF header",
        )

    return total


def validate_upload(upload: UploadFile) -> None:
    suffix = Path(upload.filename or "").suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(
            status_code=400,
            detail=f"{upload.filename} is not a GeoTIFF (expected one of {sorted(ALLOWED_SUFFIXES)})",
        )


def run_demo_inference(infer, job: Job, before_tile: Path, after_tile: Path) -> None:
    """Writes synthetic detections anchored inside the uploaded tile's georeference."""
    transform = infer.GeoTransform.from_geotiff(before_tile)
    infer.GeoTransform.from_geotiff(after_tile)

    from PIL import Image
    with Image.open(before_tile) as img:
        width, height = img.size

    # Place the 12x14 synthetic grid starting near 15% inset from top-left so polygons stay inside the tile
    start_lng = transform.x_offset + transform.x_scale * width * 0.15
    start_lat = transform.y_offset + transform.y_scale * height * 0.85

    features = infer.demo_features(
        center_lat=start_lat,
        center_lng=start_lng,
        count=DEMO_STRUCTURES,
        zone=job.zone_id,
    )
    affected = [f for f in features if f["properties"]["class"] == infer.DAMAGED_LABEL]
    unaffected = [f for f in features if f["properties"]["class"] == infer.UNDAMAGED_LABEL]

    zone_dir = settings.data_dir / job.zone_id
    infer.write_geojson(affected, zone_dir / "structures-affected.geojson")
    infer.write_geojson(unaffected, zone_dir / "structures-unaffected.geojson")

    job.tiles = 1
    job.affected = len(affected)
    job.unaffected = len(unaffected)
    job.severe = sum(1 for f in affected if f["properties"]["severity"] == "severe")
    job.moderate = sum(1 for f in affected if f["properties"]["severity"] == "moderate")


def run_real_inference(infer, job: Job, before_tile: Path, after_tile: Path) -> None:
    arguments = [
        "--before", str(before_tile),
        "--after", str(after_tile),
        "--zone", job.zone_id,
        "--data-dir", str(settings.data_dir),
        "--footprint-model", str(settings.footprint_model),
        "--damage-model", str(settings.damage_model),
        "--min-area", str(settings.min_area),
        # The API reloads GeoServ once, after the artifacts are on disk.
        "--no-reload",
    ]
    if settings.device:
        arguments += ["--device", settings.device]

    args = infer.build_parser().parse_args(arguments)
    stats = infer.run(args)

    job.tiles = stats.tiles
    job.affected = stats.affected
    job.unaffected = stats.unaffected
    job.severe = stats.severe
    job.moderate = stats.moderate
    if stats.failures:
        raise RuntimeError(f"{stats.failures} building(s) could not be classified")


def execute_job(job: Job, before_tile: Path, after_tile: Path) -> None:
    infer = load_infer()

    if settings.mode == "demo":
        run_demo_inference(infer, job, before_tile, after_tile)
    else:
        run_real_inference(infer, job, before_tile, after_tile)

    job.artifacts = [
        str(settings.data_dir / job.zone_id / "structures-affected.geojson"),
        str(settings.data_dir / job.zone_id / "structures-unaffected.geojson"),
    ]

    try:
        infer.reload_geoserv(settings.geoserv_url)
    except Exception as error:  # noqa: BLE001 - the artifacts are already on disk
        # The GeoJSON is what the map reads; a GeoServ that is down only means the reload has
        # to be repeated, so the job keeps its counts and reports the problem as a warning.
        job.warning = f"artifacts written but GeoServ reload failed: {error}"
        logger.warning("job %s could not reload GeoServ: %s", job.id, error)
    else:
        logger.info("job %s published %s to GeoServ", job.id, job.zone_id)


@app.get("/", include_in_schema=False)
def read_root():
    return {
        "service": "RAHAT Live Inference API",
        "docs": "/docs",
        "health": "/health",
        "submit": "POST /predict/disaster?zone_id=<zone>",
    }


@core_router.get("/health")
def health():
    missing = [] if settings.mode == "demo" else settings.missing_models()
    reachable = True
    try:
        import urllib.request

        with urllib.request.urlopen(f"{settings.geoserv_url}/disasters/zones", timeout=2) as response:
            reachable = response.status == 200
    except Exception as error:  # noqa: BLE001 - reported, not raised
        logger.debug("GeoServ health probe failed: %s", error)
        reachable = False

    ready = settings.data_dir.is_dir() and not missing and reachable
    return {
        "status": "ready" if ready else "degraded",
        "mode": settings.mode,
        "data_dir": str(settings.data_dir),
        "geoserv_url": settings.geoserv_url,
        "geoserv_reachable": reachable,
        "missing_models": missing,
        "active_jobs": queue.active_count(),
        "max_jobs": queue.max_pending,
    }


TILE_ROOT = PROJECT_DIR / "app" / "public" / "tiles"
DIAGNOSTIC_LAYERS = ("structures-affected", "structures-unaffected", "amenities")

# Measured on the four demo scenes against xBD ground truth, kept next to the Kaggle validation
# numbers in the meta files so the dashboard never makes the models look better than they are.
EVALUATION = {
    "measured_on": "2026-11-07",
    "scenes": [
        "hurricane-harvey_00000146",
        "hurricane-matthew_00000156",
        "hurricane-michael_00000247",
        "palu-tsunami_00000118",
    ],
    "footprint_iou_mean": 0.408,
    "footprint_iou_by_scene": {
        "hurricane-harvey_00000146": 0.425,
        "hurricane-matthew_00000156": 0.385,
        "hurricane-michael_00000247": 0.317,
        "palu-tsunami_00000118": 0.505,
    },
    "buildings_classified": 908,
    "min_area_sweep": [
        {"min_area": 400, "mean_iou": 0.082, "polygons_per_tile": 7},
        {"min_area": 200, "mean_iou": 0.180, "polygons_per_tile": 24},
        {"min_area": 120, "mean_iou": 0.294, "polygons_per_tile": 61},
        {"min_area": 60, "mean_iou": 0.417, "polygons_per_tile": 121},
        {"min_area": 20, "mean_iou": 0.473, "polygons_per_tile": 184},
        {"min_area": 6, "mean_iou": 0.487, "polygons_per_tile": 233},
    ],
    "selected_min_area": 20,
    "tile_alignment_drgb_mean": 5.6,
    "notes": [
        "Footprint IoU 0.408 on the demo scenes vs 0.5289 on the Kaggle validation split: recall "
        "drops under tree canopy in dense scenes.",
        "min_area is applied in the 384 px mask space, not in tile pixels, which is why the old "
        "400 default discarded almost every real building.",
    ],
}


def read_json_file(path: Path) -> Optional[dict]:
    """Returns the parsed JSON, or None when the file is missing or truncated."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as error:  # noqa: BLE001 - a broken artifact must not break the dashboard
        logger.debug("could not read %s: %s", path, error)
        return None


def model_inventory() -> List[dict]:
    """Both learners with their export metadata, so the UI can show arch and metrics."""
    inventory = []
    for role, path in (("stage1", settings.footprint_model), ("stage2", settings.damage_model)):
        exists = path.exists()
        inventory.append({
            "role": role,
            "path": str(path),
            "exists": exists,
            "size_mb": round(path.stat().st_size / (1024 * 1024), 1) if exists else None,
            "meta": read_json_file(path.with_name(f"{role}_meta.json")) or {},
        })
    return inventory


def zone_inventory() -> List[dict]:
    """Per-zone GeoJSON artefacts on disk: feature counts and severity split per layer."""
    zones = []
    if not settings.data_dir.is_dir():
        return zones

    for zone_dir in sorted(path for path in settings.data_dir.iterdir() if path.is_dir()):
        layers = {}
        for layer in DIAGNOSTIC_LAYERS:
            path = zone_dir / f"{layer}.geojson"
            if not path.exists():
                continue
            parsed = read_json_file(path)
            features = parsed.get("features") if isinstance(parsed, dict) else None
            features = features if isinstance(features, list) else []
            severity = {}
            for feature in features:
                if not isinstance(feature, dict):
                    continue
                label = (feature.get("properties") or {}).get("severity")
                if label:
                    severity[label] = severity.get(label, 0) + 1
            layers[layer] = {
                "features": len(features),
                "bytes": path.stat().st_size,
                "severity": severity,
            }
        zones.append({"zone_id": zone_dir.name, "layers": layers})
    return zones


def imagery_inventory() -> List[dict]:
    """XYZ tiles the Vue app serves itself, counted per zone, role and zoom."""
    inventories = []
    if not TILE_ROOT.is_dir():
        return inventories

    for zone_dir in sorted(path for path in TILE_ROOT.iterdir() if path.is_dir()):
        roles = {}
        for role_dir in sorted(path for path in zone_dir.iterdir() if path.is_dir()):
            by_zoom = {}
            for tile in role_dir.rglob("*.png"):
                zoom = tile.parent.parent.name
                by_zoom[zoom] = by_zoom.get(zoom, 0) + 1
            roles[role_dir.name] = {
                "tiles": sum(by_zoom.values()),
                "by_zoom": {
                    zoom: by_zoom[zoom]
                    for zoom in sorted(by_zoom, key=lambda z: (0, int(z)) if z.isdigit() else (1, z))
                },
            }
        inventories.append({"zone_id": zone_dir.name, "roles": roles})
    return inventories


@core_router.get("/diagnostics")
def diagnostics():
    """Everything the dashboard shows, in one read-only call."""
    return {
        "mode": settings.mode,
        "min_area": settings.min_area,
        "max_upload_mb": round(settings.max_upload_bytes / (1024 * 1024)),
        "data_dir": str(settings.data_dir),
        "geoserv_url": settings.geoserv_url,
        "models": model_inventory(),
        "zones": zone_inventory(),
        "imagery": imagery_inventory(),
        "queue": {"active": queue.active_count(), "max": queue.max_pending},
        "evaluation": EVALUATION,
    }


@core_router.post("/predict/disaster", status_code=202, response_model=JobResponse)
def predict_disaster(
    zone_id: str,
    before_image: UploadFile = File(...),
    after_image: UploadFile = File(...),
):
    """Queues inference for one tile pair. Returns 202 with the job to poll."""
    if not ZONE_ID_PATTERN.match(zone_id) or zone_id.split(".")[0].lower() in WINDOWS_RESERVED_ZONE_NAMES:
        raise HTTPException(
            status_code=400,
            detail=(
                "zone_id must be 1-64 characters of lowercase letters, digits, '.', '_' or '-', "
                "starting with a letter or digit and not a reserved OS device name"
            ),
        )

    if settings.mode == "real":
        missing = settings.missing_models()
        if missing:
            raise HTTPException(
                status_code=503,
                detail=(
                    "model files are missing: "
                    + ", ".join(missing)
                    + ". Export both learners from the notebooks, or set RAHAT_INFER_MODE=demo."
                ),
            )

    validate_upload(before_image)
    validate_upload(after_image)

    job_id = str(uuid.uuid4())
    job_dir = settings.work_dir / job_id
    before_tile = job_dir / "before.tif"
    after_tile = job_dir / "after.tif"

    try:
        save_upload(before_image, before_tile, settings.max_upload_bytes)
        save_upload(after_image, after_tile, settings.max_upload_bytes)

        def worker(job: Job) -> None:
            execute_job(job, before_tile, after_tile)

        try:
            job = queue.submit(zone_id, worker)
        except JobQueueFull as error:
            raise HTTPException(status_code=429, detail=str(error))
    except Exception:
        shutil.rmtree(job_dir, ignore_errors=True)
        raise

    logger.info(
        "queued job %s for zone %s (%s mode, %.1f KB before / %.1f KB after)",
        job.id, zone_id, settings.mode,
        before_tile.stat().st_size / 1024, after_tile.stat().st_size / 1024,
    )
    return JobResponse(**job.to_dict())


@core_router.get("/jobs", response_model=List[JobResponse])
def list_jobs(limit: int = 20):
    return [JobResponse(**data) for data in queue.list_snapshots(limit=max(1, min(limit, 100)))]


@core_router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str):
    data = queue.snapshot(job_id)
    if data is None:
        raise HTTPException(status_code=404, detail=f"no such job: {job_id}")
    return JobResponse(**data)


app.include_router(core_router)
app.include_router(core_router, prefix="/api", include_in_schema=False)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=os.environ.get("RAHAT_API_HOST", "127.0.0.1"),
        port=int(os.environ.get("RAHAT_API_PORT", "8099")),
    )
