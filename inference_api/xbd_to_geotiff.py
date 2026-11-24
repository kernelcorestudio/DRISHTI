"""Turns xBD tile pairs (PNG + label JSON) into the georeferenced GeoTIFFs infer.py expects.

xBD ships 1024x1024 PNGs whose polygons live in pixel coordinates, but the label files carry
the same buildings twice: `features.xy` (pixels) and `features.lng_lat` (degrees). Pairing the
two gives both the pixel scale and the origin, so every tile lands on its real coordinates and
nothing has to be invented.

The inference pipeline opens a north-up GeoTIFF and reads the same two tags GDAL writes:

    33550  ModelPixelScale  - degrees per pixel, x and y
    33922  ModelTiePoint    - longitude/latitude of the top-left pixel corner

This script writes those tags itself, so no GDAL or rasterio is involved. If a label file has
no `lng_lat` block it falls back to `metadata.pan_resolution` and a grid around an anchor.

    python xbd_to_geotiff.py --source ..\\rahat-demo-tiles --out ..\\demo_geotiff
"""

import argparse
import json
import math
import statistics
import sys
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
from PIL import Image, TiffImagePlugin

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import infer

METERS_PER_DEGREE = 111_320.0
# Fallback only: xBD tiles are pan-sharpened WorldView / GeoEye crops, so 0.4-0.8 m/px is usual.
DEFAULT_PIXEL_SCALE = 0.5
TAG_PIXEL_SCALE = 33550
TAG_TIE_POINT = 33922
TIFF_DOUBLE = 12
# A 1024 px tile is a few hundred metres to a couple of kilometres wide; anything else is a bug.
MIN_TILE_METERS, MAX_TILE_METERS = 100.0, 5000.0

Point = Tuple[float, float]


def wkt_first_point(wkt: str) -> Optional[Point]:
    body = wkt[wkt.find("((") + 2 :] if "((" in wkt else wkt
    numbers = body.replace("(", " ").replace(")", " ").replace(",", " ").split()
    if len(numbers) < 2:
        return None
    return float(numbers[0]), float(numbers[1])


def label_georeference(label_json: Optional[Path]) -> Optional[Tuple[float, float, float, float]]:
    """Derives (scale_x_deg, scale_y_deg, tie_lng, tie_lat) from the label's own coordinates.

    Each feature has the same polygon in pixels and in degrees, so (lng2 - lng1) / (x2 - x1)
    is the longitude step per pixel. Distant pairs are used and the median is taken so a single
    odd polygon cannot skew the scale.
    """
    if label_json is None or not label_json.is_file():
        return None
    try:
        features = (json.loads(label_json.read_text(encoding="utf-8")).get("features") or {})
    except (json.JSONDecodeError, OSError):
        return None

    pairs = []
    for xy_feature, ll_feature in zip(features.get("xy", []), features.get("lng_lat", [])):
        pixel = wkt_first_point(xy_feature.get("wkt", ""))
        degree = wkt_first_point(ll_feature.get("wkt", ""))
        if pixel and degree:
            pairs.append((pixel, degree))
    if len(pairs) < 3:
        return None

    (x0, y0), (lng0, lat0) = pairs[0]
    scale_x, scale_y = [], []
    for (x, y), (lng, lat) in pairs[1:]:
        if abs(x - x0) > 100:
            scale_x.append((lng - lng0) / (x - x0))
        if abs(y - y0) > 100:
            scale_y.append((lat - lat0) / (y - y0))
    if not scale_x or not scale_y:
        return None

    step_x = statistics.median(scale_x)
    step_y = statistics.median(scale_y)  # negative: rows run north -> south
    if step_x <= 0 or step_y >= 0:
        return None
    return step_x, step_y, lng0 - step_x * x0, lat0 - step_y * y0


def read_pixel_scale(label_json: Optional[Path], fallback: float) -> Tuple[float, str]:
    """Metres per pixel, used only when the label files have no usable `lng_lat` block.

    `metadata.gsd` is not the tile resolution: it is four times larger than `pan_resolution` in
    every tile checked (2.07 vs 0.52, 2.82 vs 0.70, ...), i.e. it describes the multispectral
    product while the images are pan-sharpened. Taking it at face value inflates every building.
    """
    if label_json is None or not label_json.is_file():
        return fallback, "default"
    try:
        metadata = json.loads(label_json.read_text(encoding="utf-8")).get("metadata") or {}
    except (json.JSONDecodeError, OSError):
        return fallback, "default"
    for key in ("pan_resolution", "gsd"):
        try:
            value = float(metadata[key])
        except (KeyError, TypeError, ValueError):
            continue
        if 0.05 <= value <= 5.0:
            return value, key
    return fallback, "default"


def write_geotiff(
    rgb: np.ndarray,
    destination: Path,
    tie_lng: float,
    tie_lat: float,
    degrees_per_pixel_x: float,
    degrees_per_pixel_y: float,
) -> None:
    tags = TiffImagePlugin.ImageFileDirectory_v2()
    tags[TAG_PIXEL_SCALE] = (degrees_per_pixel_x, degrees_per_pixel_y, 0.0)
    tags.tagtype[TAG_PIXEL_SCALE] = TIFF_DOUBLE
    tags[TAG_TIE_POINT] = (0.0, 0.0, 0.0, float(tie_lng), float(tie_lat), 0.0)
    tags.tagtype[TAG_TIE_POINT] = TIFF_DOUBLE
    destination.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgb).save(destination, tiffinfo=tags)


def collect_pairs(source: Path) -> List[Tuple[str, Path, Path, Optional[Path]]]:
    """Finds `*_pre_disaster.png` / `*_post_disaster.png` pairs, wherever they were unpacked.

    Kaggle bundles can end up holding the same tile twice (a leftover `train/images/` copy next
    to the flat files). Keep the shallowest copy per tile so one scene never overwrites another.
    """
    shallowest = {}
    for pre_png in sorted(source.rglob("*_pre_disaster.png")):
        base = pre_png.name[: -len("_pre_disaster.png")]
        post_png = pre_png.with_name(f"{base}_post_disaster.png")
        if not post_png.is_file():
            continue
        depth = len(pre_png.relative_to(source).parts)
        if base in shallowest and shallowest[base][0] <= depth:
            print(f"  duplicate ignored: {pre_png.relative_to(source)}")
            continue
        label = next(iter(pre_png.parent.glob(f"{base}_post_disaster.json")), None)
        shallowest[base] = (depth, base, pre_png, post_png, label)
    return [row[1:] for _, row in sorted(shallowest.items())]


def report(destination: Path) -> str:
    """Re-opens a written tile through the pipeline's own reader and sanity-checks its size."""
    transform = infer.GeoTransform.from_geotiff(destination)
    with Image.open(destination) as image:
        width, height = image.size
    corner_lng = transform.x_offset + transform.x_scale * width
    corner_lat = transform.y_offset + transform.y_scale * height
    metres_x = (corner_lng - transform.x_offset) * METERS_PER_DEGREE * math.cos(
        math.radians(transform.y_offset)
    )
    metres_y = (transform.y_offset - corner_lat) * METERS_PER_DEGREE
    if not (MIN_TILE_METERS <= metres_x <= MAX_TILE_METERS):
        raise infer.InferenceError(
            f"{destination.name}: written footprint is {metres_x:.0f} m wide, outside the "
            f"{MIN_TILE_METERS:.0f}-{MAX_TILE_METERS:.0f} m a 1024 px xBD tile can span"
        )
    return (
        f"top-left (lon, lat) = ({transform.x_offset:.6f}, {transform.y_offset:.6f}) | "
        f"{metres_x:.0f} x {metres_y:.0f} m"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", type=Path, required=True,
                        help="folder holding the downloaded xBD tile bundle")
    parser.add_argument("--out", type=Path, default=None,
                        help="where the GeoTIFFs go (default: <source>/geotiff)")
    parser.add_argument("--anchor-lng", type=float, default=-90.0715,
                        help="fallback grid origin when a label has no lng_lat block")
    parser.add_argument("--anchor-lat", type=float, default=29.954,
                        help="fallback grid origin when a label has no lng_lat block")
    parser.add_argument("--pixel-scale", type=float, default=DEFAULT_PIXEL_SCALE,
                        help="metres per pixel to use when a label file has no usable scale")
    parser.add_argument("--spacing", type=float, default=1.4,
                        help="fallback grid spacing as a multiple of the tile width")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    source = args.source.resolve()
    out_dir = (args.out or (source / "geotiff")).resolve()

    pairs = collect_pairs(source)
    if not pairs:
        raise SystemExit(f"no *_pre_disaster.png / *_post_disaster.png pairs under {source}")
    print(f"{len(pairs)} tile pair(s) -> {out_dir}")

    manifest = []
    for index, (base, pre_png, post_png, post_json) in enumerate(pairs):
        geo = label_georeference(post_json) or label_georeference(
            post_json.with_name(f"{base}_pre_disaster.json") if post_json else None
        )
        metres_per_pixel, scale_source = read_pixel_scale(post_json, args.pixel_scale)

        if geo:
            step_x, step_y, tie_lng, tie_lat = geo
            origin = "label lng_lat"
            # Cross-check: the degree step should agree with the documented pan resolution.
            implied = abs(step_y) * METERS_PER_DEGREE
            if not (0.5 * metres_per_pixel <= implied <= 2.0 * metres_per_pixel):
                print(f"  warning: {base}: label implies {implied:.2f} m/px but "
                      f"{scale_source} says {metres_per_pixel:.2f} m/px")
        else:
            step_x = (metres_per_pixel / METERS_PER_DEGREE) / math.cos(
                math.radians(args.anchor_lat)
            )
            step_y = -metres_per_pixel / METERS_PER_DEGREE
            origin = f"anchor grid + {scale_source}"
            columns = max(1, math.ceil(math.sqrt(len(pairs))))
            row, column = divmod(index, columns)
            with Image.open(pre_png) as image:
                width, height = image.size
            tie_lng = args.anchor_lng + column * width * step_x * args.spacing
            tie_lat = args.anchor_lat + row * height * step_y * args.spacing

        for role, png in (("before", pre_png), ("after", post_png)):
            with Image.open(png) as image:
                rgb = np.asarray(image.convert("RGB"))
            destination = out_dir / f"{base}_{role}.tif"
            write_geotiff(rgb, destination, tie_lng, tie_lat, step_x, abs(step_y))
            note = report(destination)
            print(f"  {destination.name:<44} {origin}  {note}")
            manifest.append({
                "scene": base,
                "role": role,
                "path": str(destination),
                "georeference": origin,
                "degrees_per_pixel": [step_x, abs(step_y)],
                "tie_point": [tie_lng, tie_lat],
                "width": rgb.shape[1],
                "height": rgb.shape[0],
            })

    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"wrote {len(manifest)} GeoTIFF(s) + manifest.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
