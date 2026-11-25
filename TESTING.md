# TESTING.md — DRISHTI / RAHAT Automated Testing Guide

Non-invasive test suite documentation covering the Python Inference API, Rust GeoServ spatial server, and Vue 2 frontend.

## 1. Testing Frameworks

| Service | Framework / Runner | Compatibility Notes |
| --- | --- | --- |
| Python Inference API | `pytest 9.2.0` + `httpx 0.28.1` (`ASGITransport`) | Compatible with Python `3.11.9` and FastAPI `0.103.1` |
| Inference Self-Test | Built-in `infer.py --self-test` | Standard library + NumPy/Shapely/PIL |
| Rust GeoServ | `cargo test` + `actix_web::test` | Uses `geoserv` crate library target (`src/lib.rs`) |
| Vue 2 Frontend | `@vue/cli-plugin-unit-jest@^4.5.19` + `@vue/test-utils@^1.3.6` | Compatible with Vue `2.6.11`, TS `4.1`, Vuetify `2.4` |

## 2. Test Directory Structure

```text
inference_api/tests/
├── conftest.py              # SyncASGIClient, in-memory GeoTIFF helper, isolated tmp_path fixture
├── test_api.py              # FastAPI endpoint & demo E2E tests
└── test_jobs_and_infer.py   # JobQueue, GeoTransform, polygonization & 4-class damage mapping

geoserv/tests/
└── geoserv_tests.rs         # KDBush, GeoIndexBuilder, invalid GeoJSON & Actix HTTP route tests

app/
├── jest.config.js           # TypeScript + Babel Vue 2 Jest preset
└── tests/unit/
    ├── setup.ts             # Vuetify registration, matchMedia & rAF jsdom shims
    ├── dashboard.spec.ts    # DashboardView KPIs, diagnostics & alert rendering
    ├── router.spec.ts       # All 10 routes, wildcard redirect, App nav rail & error state
    ├── inference.spec.ts    # ApiRequestError, UploadForm validation, polling & JobTable
    └── map.spec.ts          # MapView Leaflet panes, layer cycling & GeoJSON loading
```

## 3. Test Execution Commands

### Python Inference API

```powershell
.\inference_api\.venv311\Scripts\python.exe .\inference_api\infer.py --self-test
.\inference_api\.venv311\Scripts\python.exe -m pytest .\inference_api\tests -v
```

### Rust GeoServ

```powershell
cd geoserv
cargo test --tests
```

### Vue Frontend

```powershell
cd app
npx vue-cli-service test:unit --runInBand --verbose
npx vue-cli-service lint tests/unit/*.ts
```

## 4. Tested Functionalities

### A. Python Inference API (`inference_api/tests/`)

- `GET /health`: Verifies `degraded` state when GeoServ is unreachable or models are missing in `real` mode, and `ready` state in `demo` mode when GeoServ is reachable.
- `GET /diagnostics`: Validates inventory counts (`zones`, `models`, `imagery`, `queue`, `evaluation`) against isolated temporary artifacts.
- `POST /predict/disaster`: Verifies HTTP `202` + UUID4 `job_id`, invalid `zone_id` (`400`), missing models (`503`), non-GeoTIFF extensions (`400`), empty files (`400`), oversized files (`413`), and full queue (`429`).
- `GET /jobs` & `GET /jobs/{job_id}`: Verifies job polling to `succeeded`, RFC 7946 GeoJSON output (`bbox`, severity counts), and `404` for unknown IDs.
- `JobQueue` & `infer.py`: Verifies serialized worker execution, failure capture, `GeoTransform`, `mask_to_polygons`, `write_geojson`, and 4-subtype `damage_scores` mapping.

### B. Rust GeoServ (`geoserv/tests/geoserv_tests.rs` & `src/lib.rs`)

- `KDBush`: Range queries, radius search (`within`), predicate early-stopping, and empty index safety.
- `GeoIndexBuilder`: Polygon `bbox` indexing, `Point` amenity indexing, deduplication, and `limit` enforcement.
- Error & Empty Handling: Empty directories, empty `FeatureCollection`, malformed JSON, non-collection GeoJSON, and `Polygon` missing `bbox`.
- Heatmap & HTTP Routes: Centroid calculation, `/geo/{group}/{name}`, `/geo/{group}/{name}/heatmap`, `404` on unknown layers, and live `/disasters/reload` pickup of newly written disk files.

### C. Vue Frontend (`app/tests/unit/`)

- `DashboardView`: Renders KPI cards, evaluation IoU (`0.408`), offline tile totals (`42`), zone breakdowns, and store `serviceError` alerts.
- `Router` & `App.vue`: Resolves all 10 routes plus `@lat,lng,zoomz`, wildcard `* -> /`, 10 sidebar nav items, and API unreachable error reporting.
- `UploadForm`, `JobTable`, & `modules/api.ts`: GeoTIFF extension and size validation, `ApiRequestError` wrapping, live progress bar polling to `succeeded`, and failed job display.
- `MapView`: Leaflet pane creation (`basemap`, `structures`), `before -> after -> none` layer cycling, and GeoJSON/heatmap layer loading.
