"""
RAHAT inference pipeline.

Takes a before/after GeoTIFF pair (or two directories of tiles that were generated on a
common grid by data_gen/prepare_inference/create_tiles.py), runs the two FastAI models:

    stage 1 - UNet building footprint segmentation (predict_footprint_fine_tuned)
    stage 2 - building damage classifier           (predict_damage_unfrozen)

and writes per-zone GeoJSON that GeoServ can serve directly:

    <data-dir>/<zone>/structures-affected.geojson
    <data-dir>/<zone>/structures-unaffected.geojson

Every feature carries a `severity` and a `damage_probability` so the front-end can colour
and rank buildings instead of showing a flat damaged/undamaged split.

Usage (real run):

    python infer.py \
        --before-dir tiles/before --after-dir tiles/after \
        --before-id 105001001E0A3300 --after-id 10300100C540A500 \
        --zone new-orleans \
        --data-dir ../geoserv/test_data \
        --footprint-model models/predict_footprint_fine_tuned \
        --damage-model models/predict_damage_unfrozen \
        --geoserv http://127.0.0.1:8088

Usage (no models required):

    python infer.py --self-test                 # verify geometry + GeoJSON + reload path
    python infer.py --demo --data-dir ../geoserv/test_data --zone new-orleans

Both models are exported from the notebooks in nbs/ (`learn.export(path)`); fastai is only
imported when a real run starts, so --self-test and --demo work on a bare environment.
"""

import argparse
import json
import logging
import math
import random
import sys
import tempfile
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Sequence, Tuple

import numpy as np
from PIL import Image
from shapely.geometry import Polygon

LOG = logging.getLogger("infer")

# Class layout used by data_gen/stage_1/generate_stage_1_data.py. Note that the comment there
# ("1 = footprint, 2 = contact, 3 = boundary") does not match what the encoder actually builds:
# the np.where() chain leaves 3 = building interior, 2 = contact, 1 = boundary. stage_1's
# SegmentationDataLoaders codes confirm it and inference.ipynb contours class 3, so class 3 it is.
FOOTPRINT_CLASS = 3
# The retrained export (Kaggle, 2026-11-08) keeps the same four codes and takes 384 px squished
# tiles; stage1_meta.json in models/ records the measured footprint IoU (0.529).
STAGE1_CODES = ["background", "border", "contact", "footprint"]
FOOTPRINT_SIZE = 384

# Stage 2 is trained on the four original xBD subtypes, so severity now comes from the
# predicted class instead of a probability cutoff. The thresholds below survive for the
# synthetic demo features, the self test and legacy binary exports.
SEVERE_THRESHOLD = 0.85
MODERATE_THRESHOLD = 0.50

DAMAGED_LABEL = "damaged"
UNDAMAGED_LABEL = "undamaged"
NO_DAMAGE_LABEL = "no-damage"

# The stage 2 export normalises with fastai's imagenet_stats; stage2_meta.json records them.
IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)

# Vocabulary of the retrained stage 2 export (nbs/ on Kaggle):
#   ['destroyed', 'major-damage', 'minor-damage', 'no-damage']
# minor and major collapse into one "moderate" tier: they are not separable at this data
# scale (cross-event macro F1 for major-damage was 0.11), so the UI gets three levels.
DAMAGE_SEVERITY = {
    "destroyed": "severe",
    "major-damage": "moderate",
    "minor-damage": "moderate",
    "no-damage": "none",
}
DEMO_DAMAGE_CLASS = {"severe": "destroyed", "moderate": "major-damage", "none": "no-damage"}

# The stage 2 training crops were cut with this margin around the polygon bounding box.
DEFAULT_CROP_MARGIN = 2

# Smallest polygon (in 384-space mask pixels) kept as a building. Measured against xBD ground
# truth on four 1024 px tiles: 20 gives mean IoU 0.473 at precision 0.881, while the old 400
# (intended for tile pixels, but applied to the 384 px mask) kept only 7 buildings per tile and
# scored 0.082. A 150 m2 house is ~85 px2 here, so 20 is roughly a 35 m2 shed.
DEFAULT_MIN_AREA = 20.0


class InferenceError(RuntimeError):
    """Raised for problems the operator has to fix (missing model, missing tags, ...)."""


# ---------------------------------------------------------------------------------------------
# Geo transforms
# ---------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class GeoTransform:
    """Maps pixel coordinates of one tile into EPSG:4326.

    Built from two TIFF tags:
        33922  ModelTiePoint  - (i, j, k, x, y, z) tie point
        33550  ModelPixelScale - (scaleX, scaleY, scaleZ)
    """

    x_offset: float
    x_scale: float
    y_offset: float
    y_scale: float

    @classmethod
    def from_geotiff(cls, path: Path) -> "GeoTransform":
        try:
            with Image.open(path) as image:
                tags = image.tag_v2 if hasattr(image, "tag_v2") else image.tag
                try:
                    tie_point = tags[33922]
                    pixel_scale = tags[33550]
                except KeyError as error:
                    raise InferenceError(
                        f"{path} has no ModelTiePoint/ModelPixelScale tags ({error}); "
                        "it is not a north-up GeoTIFF, so it cannot be georeferenced"
                    )
        except InferenceError:
            raise
        except Exception as error:
            raise InferenceError(f"{path} could not be read as a GeoTIFF: {error}") from error

        try:
            x_offset = float(tie_point[3])
            y_offset = float(tie_point[4])
            x_scale = float(pixel_scale[0])
            y_scale = -abs(float(pixel_scale[1]))
        except (IndexError, TypeError, ValueError) as error:
            raise InferenceError(f"{path} has malformed GeoTIFF tags: {error}") from error

        if not (all(math.isfinite(v) for v in (x_offset, y_offset, x_scale, y_scale)) and x_scale > 0 and y_scale < 0):
            raise InferenceError(f"{path} has invalid ModelPixelScale/ModelTiePoint values")

        return cls(
            x_offset=x_offset,
            x_scale=x_scale,
            y_offset=y_offset,
            y_scale=y_scale,
        )

    def pixel_to_lonlat(
        self,
        x: float,
        y: float,
        ratio: float = 1.0,
        ratio_y: Optional[float] = None,
    ) -> Tuple[float, float]:
        """Converts a pixel coordinate of the *model* mask into (lon, lat).

        `x` is the column, `y` is the row, in model-output space. `ratio` (and optional `ratio_y`
        for non-square tiles) undoes the resize the model applied.
        """
        ry = ratio_y if ratio_y is not None else ratio
        lon = self.x_offset + self.x_scale * x * (1.0 / ratio)
        lat = self.y_offset + self.y_scale * y * (1.0 / ry)
        return lon, lat


# ---------------------------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------------------------


def mask_to_polygons(
    mask: np.ndarray,
    min_area: float = DEFAULT_MIN_AREA,
    simplify: float = 1.0,
) -> List[Polygon]:
    """Extracts building rings from a segmentation mask.

    Coordinates are stored in (x=column, y=row) order, which is the opposite of
    skimage.measure.find_contours' (row, column) output.
    """
    from skimage import measure

    binary = np.where(mask == FOOTPRINT_CLASS, 255, 0).astype(np.uint8)
    h, w = binary.shape[:2]
    padded = np.pad(binary, pad_width=1, mode="constant", constant_values=0)
    polygons: List[Polygon] = []

    for contour in measure.find_contours(padded, 1.0):
        ring = [
            (min(max(float(point[1]) - 1.0, 0.0), float(w)), min(max(float(point[0]) - 1.0, 0.0), float(h)))
            for point in contour
        ]
        try:
            polygon = Polygon(ring).simplify(simplify)
            if not polygon.is_valid:
                polygon = polygon.buffer(0)
        except (ValueError, TypeError):
            # Simplification can degenerate a tiny contour below three points.
            continue
        if isinstance(polygon, Polygon) and polygon.is_valid and not polygon.is_empty and polygon.area > min_area:
            polygons.append(polygon)

    return polygons


def polygon_bbox(polygon: Polygon) -> List[float]:
    min_x, min_y, max_x, max_y = polygon.bounds
    return [min_x, min_y, max_x, max_y]


def project_ring(
    polygon: Polygon,
    transform: GeoTransform,
    ratio: float,
    ratio_y: Optional[float] = None,
) -> List[List[float]]:
    """Projects a pixel-space ring into a closed [lon, lat] ring."""
    ring = [
        list(transform.pixel_to_lonlat(x, y, ratio, ratio_y=ratio_y))
        for x, y in polygon.exterior.coords
    ]
    if ring and ring[0] != ring[-1]:
        ring.append(list(ring[0]))
    return ring


# ---------------------------------------------------------------------------------------------
# Damage classification
# ---------------------------------------------------------------------------------------------


def severity_for(probability: float) -> str:
    if probability >= SEVERE_THRESHOLD:
        return "severe"
    if probability >= MODERATE_THRESHOLD:
        return "moderate"
    return "none"


def cut_crop(
    after_rgb: np.ndarray,
    polygon: Polygon,
    output_size: int,
    mode: str = "bbox",
    margin: int = DEFAULT_CROP_MARGIN,
) -> np.ndarray:
    """Cuts the building out of the after image.

    `bbox` mode mirrors xview2_feature_extractor, which produced the stage 2 training set:
    crop to the polygon bounding box, black out everything outside the ring, then pad to a
    square canvas with the aspect ratio preserved.

    `full` mode mirrors nbs/inference.ipynb instead: mask the polygon over the whole tile.
    """
    import cv2

    height, width = after_rgb.shape[:2]
    ring = np.array(
        [[[int(round(x)), int(round(y))]] for x, y in polygon.exterior.coords],
        dtype=np.int32,
    )

    if mode == "bbox":
        min_x, min_y, max_x, max_y = [int(round(v)) for v in polygon.bounds]
        # Same margin the training crops were generated with (data_gen / Kaggle cells).
        min_x, min_y = max(min_x - margin, 0), max(min_y - margin, 0)
        max_x, max_y = min(max_x + margin, width - 1), min(max_y + margin, height - 1)
        if max_x <= min_x or max_y <= min_y:
            return np.zeros((output_size, output_size, 3), dtype=np.uint8)

        canvas = np.zeros_like(after_rgb)
        cv2.fillPoly(canvas, [ring], (255, 255, 255))
        crop = cv2.bitwise_and(after_rgb, canvas)[min_y:max_y + 1, min_x:max_x + 1]

        crop_height, crop_width = crop.shape[:2]
        scale = output_size / max(crop_height, crop_width)
        scaled = cv2.resize(
            crop,
            (max(1, int(round(crop_width * scale))), max(1, int(round(crop_height * scale)))),
            interpolation=cv2.INTER_AREA,
        )
        output = np.zeros((output_size, output_size, 3), dtype=np.uint8)
        offset_y = (output_size - scaled.shape[0]) // 2
        offset_x = (output_size - scaled.shape[1]) // 2
        output[offset_y:offset_y + scaled.shape[0], offset_x:offset_x + scaled.shape[1]] = scaled
        return output

    canvas = np.zeros_like(after_rgb)
    cv2.fillPoly(canvas, [ring], (255, 255, 255))
    masked = cv2.bitwise_and(after_rgb, canvas)
    return cv2.resize(masked, (output_size, output_size), interpolation=cv2.INTER_AREA)


def footprint_class_mask(learn, image) -> np.ndarray:
    """uint8 RGB tile -> FOOTPRINT_SIZE square class mask (values 0..3) from stage 1.

    Two things are spelled out instead of going through `learn.predict`:
      * the exported loss (`CombinedLoss`, defined inside the Kaggle notebook) has no
        `decodes`, so `predict` returns raw 4-channel logits rather than a class mask;
      * the pickled transforms cannot run outside the exporting interpreter, the same
        reason documented on `crop_to_tensor`.

    Training used `Resize(FOOTPRINT_SIZE, method="squish")`, i.e. a plain aspect-ignoring
    resize, so `cv2.resize` reproduces the same input the model was fitted on.
    """
    import cv2
    import torch

    array = np.asarray(image.convert("RGB") if hasattr(image, "convert") else image)
    array = np.asarray(array, dtype=np.float32)
    if array.ndim == 2:
        array = np.stack([array] * 3, axis=-1)
    array = cv2.resize(array[..., :3], (FOOTPRINT_SIZE, FOOTPRINT_SIZE),
                       interpolation=cv2.INTER_AREA)
    array = (array / 255.0 - IMAGENET_MEAN) / IMAGENET_STD
    tensor = torch.from_numpy(array).permute(2, 0, 1).unsqueeze(0).contiguous()

    model = learn.model
    device = next(model.parameters()).device
    with torch.no_grad():
        logits = model(tensor.to(device)).float()
    return logits.argmax(dim=1)[0].cpu().numpy().astype(np.uint8)


def crop_to_tensor(image) -> "torch.Tensor":
    """uint8 RGB crop -> the normalised NCHW float tensor the stage 2 body expects.

    The preprocessing is spelled out here instead of going through `learn.predict`
    because the exported DataLoaders carry transforms that were pickled on Python 3.13 /
    Linux; running them on a different interpreter trips fasttransform's dispatch
    (`SystemError: no locals when deleting 'TensorImage'`). Using only the weights keeps
    the archive loadable on any OS / Python combination.
    """
    import torch

    array = np.asarray(image, dtype=np.float32)
    if array.ndim == 2:
        array = np.stack([array] * 3, axis=-1)
    array = array[..., :3] / 255.0
    array = (array - IMAGENET_MEAN) / IMAGENET_STD
    return torch.from_numpy(array).permute(2, 0, 1).unsqueeze(0).contiguous()


def damage_scores(learn, image) -> Dict:
    """Runs the stage 2 classifier and translates its classes into the UI contract.

    Returns the damaged/undamaged split, the severity tier, the raw class label and
    P(not no-damage). With the four-subtype vocabulary a name lookup replaces the old
    `probabilities[-1]` fallback, which silently read P(no-damage) as P(damaged).
    """
    import torch

    vocabulary = [str(label) for label in (getattr(learn.dls, "vocab", []) or [])]
    model = learn.model
    device = next(model.parameters()).device
    with torch.no_grad():
        logits = model(crop_to_tensor(image).to(device)).float()
        probabilities = torch.softmax(logits, dim=1)[0].cpu().numpy().astype(float)

    index = int(probabilities.argmax())
    label = vocabulary[index] if index < len(vocabulary) else str(index)
    confidence = float(probabilities[index])

    if all(name in vocabulary for name in DAMAGE_SEVERITY):
        # Four-subtype export. The tier is decided on the three-level contract the model was
        # actually evaluated against (macro F1 0.389 on the held-out event), not on the
        # argmax of four classes: minor and major each win rarely, but together they are a
        # strong signal, so summing them first is what the product promises.
        destroyed_p = float(probabilities[vocabulary.index("destroyed")])
        no_damage_p = float(probabilities[vocabulary.index(NO_DAMAGE_LABEL)])
        damaged_p = max(0.0, 1.0 - destroyed_p - no_damage_p)
        severity, confidence = max(
            (("severe", destroyed_p), ("moderate", damaged_p), ("none", no_damage_p)),
            key=lambda tier: tier[1],
        )
        if severity == "none":
            label = NO_DAMAGE_LABEL
        elif severity == "severe":
            label = "destroyed"
        else:  # keep the finer subtype as a diagnostic, not as the contract
            label = max(
                ("minor-damage", "major-damage"),
                key=lambda name: probabilities[vocabulary.index(name)],
            )
        probability = 1.0 - no_damage_p
    elif len(vocabulary) == 2:
        # Legacy binary export: keep the old probability thresholds working.
        damaged_index = vocabulary.index(DAMAGED_LABEL) if DAMAGED_LABEL in vocabulary else -1
        severity = severity_for(float(probabilities[damaged_index]))
        label = DAMAGED_LABEL if severity != "none" else UNDAMAGED_LABEL
        probability = confidence
    else:
        severity = severity_for(confidence)
        probability = confidence

    return {
        "class": UNDAMAGED_LABEL if severity == "none" else DAMAGED_LABEL,
        "severity": severity,
        "damage_class": label,
        "damage_probability": round(probability, 4),
        "confidence": round(confidence, 4),
    }


# ---------------------------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------------------------


@dataclass
class RunStats:
    tiles: int = 0
    candidates: int = 0
    affected: int = 0
    unaffected: int = 0
    severe: int = 0
    moderate: int = 0
    failures: int = 0
    started_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )


def export_path(path: Path) -> Path:
    """load_learner() appends `.pkl` when not present, so preserve dotted names cleanly."""
    return path if path.suffix == ".pkl" else Path(f"{path}.pkl")


def load_learners(footprint_model: Path, damage_model: Path, device: Optional[str]):
    # Kaggle exports are pickled on Python 3.13 / Linux; see compat.py for what that breaks.
    from compat import ensure_pickle_compatibility

    ensure_pickle_compatibility()

    try:
        from fastai.learner import load_learner
    except ImportError as error:  # pragma: no cover - environment dependent
        raise InferenceError(
            "fastai is not installed. Create the notebook environment with "
            "`conda env create -f nbs/ml_env_sagemaker.yml` (see README.md) and rerun."
        ) from error

    for model_path in (footprint_model, damage_model):
        if not export_path(model_path).exists():
            raise InferenceError(
                f"model not found: {export_path(model_path)}. Export it from the matching "
                "notebook with `learn.export(...)` and copy the resulting file here."
            )

    LOG.info("loading stage 1 (footprint) from %s", export_path(footprint_model))
    stage_1 = load_learner(export_path(footprint_model))
    LOG.info("loading stage 2 (damage) from %s", export_path(damage_model))
    stage_2 = load_learner(export_path(damage_model))

    if device:
        device = device.strip()
        if device.isdigit():
            device = f"cuda:{device}"
        for learn in (stage_1, stage_2):
            learn.model = learn.model.to(device)
    for learn in (stage_1, stage_2):
        learn.model.eval()

    return stage_1, stage_2


def pair_tiles(
    before: Sequence[Path],
    after_dir: Path,
    before_id: str,
    after_id: str,
) -> Iterator[Tuple[Path, Path]]:
    """Pairs before tiles with their after counterpart on the shared tiling grid."""
    for before_tile in before:
        after_name = before_tile.name
        if before_id and after_id and before_id in after_name:
            after_name = after_name.replace(before_id, after_id)

        after_tile = after_dir / after_name
        if not after_tile.exists():
            LOG.warning("no after tile for %s (looked for %s)", before_tile, after_tile.name)
            continue
        yield before_tile, after_tile


def process_tile(
    before_tile: Path,
    after_tile: Path,
    stage_1,
    stage_2,
    args: argparse.Namespace,
    stats: RunStats,
    zone: str,
) -> List[Dict]:
    transform = GeoTransform.from_geotiff(before_tile)

    try:
        with Image.open(before_tile) as before_image:
            before_rgb = np.array(before_image.convert("RGB"))
        with Image.open(after_tile) as after_image:
            after_rgb = np.array(after_image.convert("RGB"))
    except Exception as error:
        raise InferenceError(f"failed to read tile pair ({before_tile}, {after_tile}): {error}") from error

    footprint_mask = footprint_class_mask(stage_1, before_rgb)
    ratio_x = footprint_mask.shape[1] / max(before_rgb.shape[1], 1)
    ratio_y = footprint_mask.shape[0] / max(before_rgb.shape[0], 1)
    polygons = mask_to_polygons(footprint_mask, args.min_area, args.simplify)
    LOG.info("%s: %d candidate building(s)", before_tile.name, len(polygons))

    from shapely.affinity import scale as scale_polygon
    after_scale_x = after_rgb.shape[1] / max(footprint_mask.shape[1], 1)
    after_scale_y = after_rgb.shape[0] / max(footprint_mask.shape[0], 1)

    features: List[Dict] = []
    for index, polygon in enumerate(polygons):
        stats.candidates += 1
        try:
            after_polygon = scale_polygon(
                polygon,
                xfact=after_scale_x,
                yfact=after_scale_y,
                origin=(0, 0),
            )
            crop = cut_crop(
                after_rgb, after_polygon, args.crop_size, args.crop_mode, args.crop_margin
            )
            scores = damage_scores(stage_2, crop)
        except Exception as error:  # keep going: one bad building must not kill the tile
            LOG.error("%s polygon %d failed: %s", before_tile.name, index, error)
            stats.failures += 1
            continue

        affected = scores["class"] == DAMAGED_LABEL
        ring = project_ring(polygon, transform, ratio_x, ratio_y=ratio_y)
        ring_lons = [point[0] for point in ring]
        ring_lats = [point[1] for point in ring]

        features.append(
            {
                "type": "Feature",
                "id": str(uuid.uuid4()),
                "properties": {
                    "class": scores["class"],
                    "severity": scores["severity"],
                    "damage_class": scores["damage_class"],
                    "damage_probability": scores["damage_probability"],
                    "confidence": scores["confidence"],
                    "area_px": round(polygon.area, 1),
                    "zone": zone,
                    "tile": before_tile.stem,
                    "footprint_index": index,
                    "generated_at": stats.started_at,
                },
                "geometry": {"type": "Polygon", "coordinates": [ring]},
                # GeoServ indexes bbox corners and refuses features without one.
                "bbox": [min(ring_lons), min(ring_lats), max(ring_lons), max(ring_lats)],
            }
        )

    return features


def write_geojson(features: Iterable[Dict], path: Path) -> int:
    collection = {"type": "FeatureCollection", "features": list(features)}
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f"{path.name}.{uuid.uuid4().hex[:8]}.tmp")
    with open(temp_path, "w", encoding="utf-8") as file:
        json.dump(collection, file, separators=(",", ":"))
    temp_path.replace(path)
    return len(collection["features"])


def reload_geoserv(base_url: str, timeout: float = 30.0) -> Dict:
    import requests

    url = f"{base_url.rstrip('/')}/disasters/reload"
    LOG.info("POST %s", url)
    try:
        response = requests.post(url, timeout=timeout)
    except requests.RequestException as error:
        raise InferenceError(f"failed to reach {url}: {error}") from error
    if not response.ok:
        raise InferenceError(f"{url} returned {response.status_code}: {response.text[:200]}")
    return response.json()


def run(args: argparse.Namespace) -> RunStats:
    zone = args.zone
    data_dir = Path(args.data_dir)
    stats = RunStats()

    if args.before and args.after:
        before_tiles = [Path(args.before)]
        pairs = [(Path(args.before), Path(args.after))]
    else:
        before_tiles = sorted(Path(args.before_dir).glob(args.pattern))
        pairs = list(pair_tiles(before_tiles, Path(args.after_dir), args.before_id, args.after_id))

    if not before_tiles:
        raise InferenceError(f"no tiles matched {args.pattern!r} in {args.before_dir}")
    if not pairs:
        raise InferenceError(f"no matching after tiles found in {args.after_dir}")

    LOG.info("%d tile pair(s) to process", len(pairs))
    stage_1, stage_2 = load_learners(
        Path(args.footprint_model), Path(args.damage_model), args.device
    )

    affected: List[Dict] = []
    unaffected: List[Dict] = []
    for before_tile, after_tile in pairs:
        stats.tiles += 1
        features = process_tile(before_tile, after_tile, stage_1, stage_2, args, stats, zone)
        for feature in features:
            if feature["properties"]["class"] == DAMAGED_LABEL:
                affected.append(feature)
            else:
                unaffected.append(feature)

    stats.affected = len(affected)
    stats.unaffected = len(unaffected)
    stats.severe = sum(1 for f in affected if f["properties"]["severity"] == "severe")
    stats.moderate = sum(1 for f in affected if f["properties"]["severity"] == "moderate")

    zone_dir = data_dir / zone
    write_geojson(affected, zone_dir / "structures-affected.geojson")
    write_geojson(unaffected, zone_dir / "structures-unaffected.geojson")

    LOG.info(
        "wrote %s: %d affected (%d severe, %d moderate), %d unaffected, %d failure(s)",
        zone_dir,
        stats.affected,
        stats.severe,
        stats.moderate,
        stats.unaffected,
        stats.failures,
    )

    if args.geoserv and not args.no_reload:
        reload_geoserv(args.geoserv, args.reload_timeout)

    return stats


# ---------------------------------------------------------------------------------------------
# Demo data and self test (no models required)
# ---------------------------------------------------------------------------------------------


def demo_features(
    center_lat: float,
    center_lng: float,
    count: int,
    zone: str = "demo",
    seed: int = 7,
) -> List[Dict]:
    """Synthetic buildings used to exercise the UI without imagery or models."""
    rng = random.Random(seed)
    features: List[Dict] = []
    for index in range(count):
        row, column = divmod(index, 12)
        lat = center_lat + row * 0.0009
        lng = center_lng + column * 0.0009
        size = 0.00028

        ring = [[lng, lat], [lng + size, lat], [lng + size, lat + size], [lng, lat + size]]
        ring.append(ring[0])

        # Skew the distribution towards undamaged, like a real event.
        probability = rng.choice(
            [rng.uniform(0.02, 0.45), rng.uniform(0.3, 0.6), rng.uniform(0.86, 0.99)]
        )
        severity = severity_for(probability)
        affected = severity != "none"

        features.append(
            {
                "type": "Feature",
                "id": str(uuid.uuid4()),
                "properties": {
                    "class": DAMAGED_LABEL if affected else UNDAMAGED_LABEL,
                    "severity": severity,
                    "damage_class": DEMO_DAMAGE_CLASS[severity],
                    "damage_probability": round(probability, 4),
                    "confidence": round(max(probability, 1.0 - probability), 4),
                    "area_px": rng.randint(250, 900),
                    "zone": zone,
                    "tile": f"{zone}-demo",
                    "footprint_index": index,
                    "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                },
                "geometry": {"type": "Polygon", "coordinates": [ring]},
                "bbox": [min(p[0] for p in ring), min(p[1] for p in ring),
                         max(p[0] for p in ring), max(p[1] for p in ring)],
            }
        )
    return features


def emit_demo(args: argparse.Namespace) -> int:
    zones = {
        "new-orleans": (29.960, -90.100),
        "oman": (23.592, 58.520),
    }
    for zone, (lat, lng) in zones.items():
        features = demo_features(lat, lng, args.demo_count, zone=zone)
        affected = [f for f in features if f["properties"]["class"] == DAMAGED_LABEL]
        unaffected = [f for f in features if f["properties"]["class"] == UNDAMAGED_LABEL]
        zone_dir = Path(args.data_dir) / zone
        write_geojson(affected, zone_dir / "structures-affected.geojson")
        write_geojson(unaffected, zone_dir / "structures-unaffected.geojson")
        severe = sum(1 for f in affected if f["properties"]["severity"] == "severe")
        LOG.info(
            "demo %s: %d affected (%d severe), %d unaffected",
            zone,
            len(affected),
            severe,
            len(unaffected),
        )

    if args.geoserv and not args.no_reload:
        reload_geoserv(args.geoserv, args.reload_timeout)
    return 0


def self_test(args: argparse.Namespace) -> int:
    checks: List[Tuple[str, bool, str]] = []

    def check(name: str, condition: bool, detail: str = "") -> None:
        checks.append((name, bool(condition), detail))

    # 1. Geotransform + projection round trip.
    transform = GeoTransform(x_offset=-90.0, x_scale=1e-4, y_offset=30.0, y_scale=-1e-4)
    lon, lat = transform.pixel_to_lonlat(0, 0)
    check("origin maps to tie point", math.isclose(lon, -90.0) and math.isclose(lat, 30.0),
          f"{lon}, {lat}")
    lon, lat = transform.pixel_to_lonlat(100, 100)
    check("pixel +100 moves east and south",
          math.isclose(lon, -90.0 + 0.01) and math.isclose(lat, 30.0 - 0.01), f"{lon}, {lat}")
    lon, lat = transform.pixel_to_lonlat(100, 100, ratio=2.0)
    check("ratio scales pixel size", math.isclose(lon, -90.0 + 0.005), f"{lon}, {lat}")

    # 2. Mask -> polygons on a real synthetic mask.
    mask = np.zeros((120, 120), dtype=np.uint8)
    mask[10:40, 10:40] = FOOTPRINT_CLASS
    mask[60:100, 70:110] = FOOTPRINT_CLASS
    mask[0:5, 0:5] = FOOTPRINT_CLASS  # below the area threshold, must be dropped
    polygons = mask_to_polygons(mask, min_area=100.0)
    check("two buildings detected", len(polygons) == 2, f"got {len(polygons)}")
    if polygons:
        bounds = polygons[0].bounds
        check("first polygon is near its mask block", 8 < bounds[0] < 14 and 8 < bounds[1] < 14,
              str(bounds))

    # 3. Pixel ring -> lon/lat ring, with a valid bbox.
    if polygons:
        ring = project_ring(polygons[0], transform, 1.0)
        check("ring is closed", ring[0] == ring[-1], f"{len(ring)} points")
        lons = [p[0] for p in ring]
        lats = [p[1] for p in ring]
        check("ring is geographically sane",
              -180 < min(lons) < 180 and -90 < min(lats) < 90, f"{min(lons)}, {min(lats)}")
        check("bbox spans the ring", max(lons) > min(lons) and max(lats) > min(lats))
    else:
        check("ring is closed", False, "no polygons detected")
        check("ring is geographically sane", False, "no polygons detected")
        check("bbox spans the ring", False, "no polygons detected")

    # 4. Severity tiers.
    check("0.99 is severe", severity_for(0.99) == "severe")
    check("0.60 is moderate", severity_for(0.60) == "moderate")
    check("0.10 is none", severity_for(0.10) == "none")

    # 4b. Four-subtype export -> three product tiers.
    check("every trained class has a tier", set(DAMAGE_SEVERITY) == {
        "destroyed", "major-damage", "minor-damage", "no-damage"})
    check("destroyed is severe", DAMAGE_SEVERITY["destroyed"] == "severe")
    check("minor and major share moderate",
          DAMAGE_SEVERITY["minor-damage"] == DAMAGE_SEVERITY["major-damage"] == "moderate")

    # 4c. Stage 1 export contract: four logit channels, class 3 is the footprint.
    check("stage 1 keeps the four-code layout",
          len(STAGE1_CODES) == 4 and STAGE1_CODES[FOOTPRINT_CLASS] == "footprint",
          str(STAGE1_CODES))
    stage1_logits = np.zeros((4, 6, 6), dtype=np.float32)
    stage1_logits[FOOTPRINT_CLASS] = 5.0
    check("argmax over the 4 logit channels yields the footprint class",
          int(stage1_logits.argmax(axis=0)[0, 0]) == FOOTPRINT_CLASS)

    # 5. GeoJSON shape, including the bbox GeoServ depends on.
    features = demo_features(29.96, -90.10, 24)
    with tempfile.TemporaryDirectory() as temporary_directory:
        output = Path(temporary_directory) / "zone" / "structures-affected.geojson"
        written = write_geojson(features, output)
        payload = json.loads(output.read_text(encoding="utf-8"))
        check("features written", written == len(features) and payload["type"] == "FeatureCollection",
              str(written))
        check("every feature has a bbox", all("bbox" in f for f in payload["features"]))
        check("every feature has severity and probability",
              all("severity" in f["properties"] and "damage_probability" in f["properties"]
                  for f in payload["features"]))
        check("classes and severities agree",
              all((f["properties"]["class"] == UNDAMAGED_LABEL)
                  == (f["properties"]["severity"] == "none")
                  for f in payload["features"]))

    # 6. Live GeoServ reload, if one is reachable.
    if args.geoserv:
        try:
            result = reload_geoserv(args.geoserv, args.reload_timeout)
            check("geoserv reload", result.get("status") == "reloaded", str(result))
        except Exception as error:
            check("geoserv reload", False, str(error))

    width = max(len(name) for name, _, _ in checks)
    failed = 0
    for name, passed, detail in checks:
        status = "PASS" if passed else "FAIL"
        if not passed:
            failed += 1
        print(f"[{status}] {name.ljust(width)}  {detail}".rstrip())

    print(f"\n{len(checks) - failed}/{len(checks)} checks passed")
    return 0 if failed == 0 else 1


# ---------------------------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="infer.py",
        description="Run the RAHAT building footprint + damage pipeline and publish GeoJSON.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    source = parser.add_argument_group("input imagery")
    source.add_argument("--before", help="single before GeoTIFF tile")
    source.add_argument("--after", help="single after GeoTIFF tile")
    source.add_argument("--before-dir", help="directory of before tiles")
    source.add_argument("--after-dir", help="directory of after tiles")
    source.add_argument("--pattern", default="*.tif", help="glob for --before-dir")
    source.add_argument("--before-id", default="", help="image id in before file names")
    source.add_argument("--after-id", default="", help="image id to substitute for --before-id")

    models = parser.add_argument_group("models")
    models.add_argument("--footprint-model", default="predict_footprint_fine_tuned")
    models.add_argument("--damage-model", default="predict_damage_unfrozen")
    models.add_argument("--device", default="", help="torch device, e.g. cpu, cuda, 0")

    output = parser.add_argument_group("output")
    output.add_argument("--zone", default="new-orleans", help="GeoServ group / zone name")
    output.add_argument("--data-dir", default=str(Path(__file__).resolve().parent.parent
                                                  / "geoserv" / "test_data"),
                        help="GeoServ data directory (<data-dir>/<zone>/*.geojson)")
    output.add_argument("--geoserv", default="", help="GeoServ base URL, e.g. http://127.0.0.1:8088")
    output.add_argument("--no-reload", action="store_true", help="do not call /disasters/reload")
    output.add_argument("--reload-timeout", type=float, default=30.0)

    tuning = parser.add_argument_group("tuning")
    tuning.add_argument("--min-area", type=float, default=DEFAULT_MIN_AREA,
                        help="discard polygons smaller than this many pixels")
    tuning.add_argument("--simplify", type=float, default=1.0,
                        help="shapely simplify tolerance in pixels")
    tuning.add_argument("--crop-size", type=int, default=256,
                        help="edge of the square crop fed to the damage model")
    tuning.add_argument("--crop-mode", choices=("bbox", "full"), default="bbox",
                        help="bbox matches xview2_feature_extractor, full matches the notebook")
    tuning.add_argument("--crop-margin", type=int, default=DEFAULT_CROP_MARGIN,
                        help="pixels added around the polygon bbox, matching the training crops")
    tuning.add_argument("--severe-threshold", type=float, default=None,
                        help="override the 0.85 severe cutoff")
    tuning.add_argument("--moderate-threshold", type=float, default=None,
                        help="override the 0.50 moderate cutoff")
    tuning.add_argument("--verbose", action="store_true")

    offline = parser.add_argument_group("offline modes")
    offline.add_argument("--demo", action="store_true",
                         help="write synthetic demo zones; no models or imagery needed")
    offline.add_argument("--demo-count", type=int, default=168)
    offline.add_argument("--self-test", action="store_true",
                         help="verify geometry, GeoJSON and reload without models")

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    global SEVERE_THRESHOLD, MODERATE_THRESHOLD
    if args.severe_threshold is not None:
        SEVERE_THRESHOLD = args.severe_threshold
    if args.moderate_threshold is not None:
        MODERATE_THRESHOLD = args.moderate_threshold
    if MODERATE_THRESHOLD > SEVERE_THRESHOLD:
        parser.error("--moderate-threshold cannot exceed --severe-threshold")

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )

    try:
        if args.self_test:
            return self_test(args)
        if args.demo:
            return emit_demo(args)
        if not (args.before and args.after) and not (args.before_dir and args.after_dir):
            parser.error("provide --before/--after or --before-dir/--after-dir "
                         "(or use --self-test / --demo)")
        stats = run(args)
        return 0 if stats.failures == 0 else 1
    except InferenceError as error:
        LOG.error("%s", error)
        return 2


if __name__ == "__main__":
    sys.exit(main())
