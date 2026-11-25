"""Turn the demo GeoTIFFs into XYZ tile pyramids the Vue app can serve itself.

The zones in `disaster-zones.json` point `beforeLayer` / `afterLayer` at a `{z}/{x}/{y}` template.
For the demo scenes those templates are written into `app/public/tiles/demo-<scene>/<role>/`, so
the same `npm run serve` that hosts the UI also hosts the imagery -- no tile server, no network.

Web Mercator maths is done by hand: the images are already north-up GeoTIFFs with a plain
degree-per-pixel affine, so a tile is just an axis-aligned crop in source pixels.
"""
import argparse
import math
from pathlib import Path

from PIL import Image

TILE = 256
WEB_MERCATOR_LAT_LIMIT = 85.0511287798066


def read_georeference(tif: Path):
    """(lng_left, lat_top, degrees_per_pixel_x, degrees_per_pixel_y) from the TIFF tags."""
    with Image.open(tif) as image:
        tags = image.tag_v2
        scale = tags[33550]  # ModelPixelScale
        tie = tags[33922]  # ModelTiePoint
        return float(tie[3]), float(tie[4]), abs(float(scale[0])), abs(float(scale[1]))


def lng_to_world_x(lng: float, world: float) -> float:
    return (lng + 180.0) / 360.0 * world


def lat_to_world_y(lat: float, world: float) -> float:
    lat = max(min(lat, WEB_MERCATOR_LAT_LIMIT), -WEB_MERCATOR_LAT_LIMIT)
    rad = math.radians(lat)
    return (1.0 - math.log(math.tan(rad) + 1.0 / math.cos(rad)) / math.pi) / 2.0 * world


def world_x_to_lng(x: float, world: float) -> float:
    return x / world * 360.0 - 180.0


def world_y_to_lat(y: float, world: float) -> float:
    return math.degrees(math.atan(math.sinh(math.pi * (1.0 - 2.0 * y / world))))


def write_pyramid(tif: Path, out_dir: Path, zooms):
    lng0, lat0, dx, dy = read_georeference(tif)
    with Image.open(tif) as image:
        source = image.convert("RGB")
    width, height = source.size
    lng1 = lng0 + width * dx
    lat1 = lat0 - height * dy

    written = 0
    for zoom in zooms:
        world = TILE * (1 << zoom)
        tile_x0 = int(math.floor(lng_to_world_x(lng0, world) / TILE))
        tile_x1 = int(math.floor(lng_to_world_x(lng1, world) / TILE))
        tile_y0 = int(math.floor(lat_to_world_y(lat0, world) / TILE))
        tile_y1 = int(math.floor(lat_to_world_y(lat1, world) / TILE))

        for tile_x in range(tile_x0, tile_x1 + 1):
            for tile_y in range(tile_y0, tile_y1 + 1):
                # Tile extent in degrees, then in source pixels.
                left = world_x_to_lng(tile_x * TILE, world)
                right = world_x_to_lng((tile_x + 1) * TILE, world)
                top = world_y_to_lat(tile_y * TILE, world)
                bottom = world_y_to_lat((tile_y + 1) * TILE, world)

                sx0, sx1 = (left - lng0) / dx, (right - lng0) / dx
                sy0, sy1 = (lat0 - top) / dy, (lat0 - bottom) / dy

                # Clip to the image; a tile hanging off the edge is only partly filled.
                cx0, cx1 = max(0.0, sx0), min(float(width), sx1)
                cy0, cy1 = max(0.0, sy0), min(float(height), sy1)
                if cx1 - cx0 < 0.5 or cy1 - cy0 < 0.5:
                    continue

                region = source.crop(
                    (int(math.floor(cx0)), int(math.floor(cy0)),
                     int(math.ceil(cx1)), int(math.ceil(cy1)))
                )
                span_x = (sx1 - sx0) or 1.0
                span_y = (sy1 - sy0) or 1.0
                # Destination rectangle of the clipped part, in tile pixels.
                dx0 = (math.floor(cx0) - sx0) / span_x * TILE
                dx1 = (math.ceil(cx1) - sx0) / span_x * TILE
                dy0 = (math.floor(cy0) - sy0) / span_y * TILE
                dy1 = (math.ceil(cy1) - sy0) / span_y * TILE

                target = Image.new("RGB", (max(1, round(dx1 - dx0)), max(1, round(dy1 - dy0))))
                target = region.resize(target.size, Image.LANCZOS)
                # Transparent outside the GeoTIFF so edge tiles blend into the OSM base layer
                # instead of showing a dark band at the pyramid boundary.
                canvas = Image.new("RGBA", (TILE, TILE), (0, 0, 0, 0))
                canvas.paste(target, (round(dx0), round(dy0)))

                path = out_dir / str(zoom) / str(tile_x)
                path.mkdir(parents=True, exist_ok=True)
                canvas.save(path / f"{tile_y}.png", optimize=True)
                written += 1
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tiles", default="../demo_geotiff", help="directory of demo GeoTIFFs")
    parser.add_argument("--out", default="../app/public/tiles", help="output root")
    parser.add_argument("--zooms", default="15,16,17,18,19")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    tiles = Path(args.tiles).resolve()
    out_root = Path(args.out).resolve()
    zooms = [int(value) for value in args.zooms.split(",")]

    for tif in sorted(tiles.glob("*.tif")):
        role = "after" if tif.stem.endswith("_after") else "before"
        scene = tif.stem[: -len(f"_{role}")]
        destination = out_root / f"demo-{scene}" / role
        if destination.exists() and not args.force:
            print(f"{destination.relative_to(out_root)}: exists, skipping (use --force)")
            continue
        count = write_pyramid(tif, destination, zooms)
        lng, lat, _, _ = read_georeference(tif)
        print(f"{destination.relative_to(out_root)}: {count} tile(s)  anchor {lng:.5f},{lat:.5f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
