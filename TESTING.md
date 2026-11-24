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
