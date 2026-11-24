# DRISHTI / RAHAT Deployment Plan

Production and local rollout plan for **DRISHTI** (*Disaster Response Intelligence System with Hallucination-aware Trust Indicators*), unifying **RAHAT** (Rescue Allocation & Hazard Assessment Tool) and **NETRA** (Sentinel-2 Super-Resolution & Spectral Mapping).

## 1. Executive Scope & Objectives

- Preserve the existing three-service runtime topology without breaking working endpoints or GeoJSON contracts.
- Standardize environment variables via `.env.example` with zero hardcoded credentials.
- Ensure deterministic startup order, health verification, and clear fallback behavior when optional ML/Web3 packages or GPU hardware are absent.

## 2. Target Architecture Overview

```text
Browser (:8080)
  ├── /api/*  ──► Vue Dev/Reverse Proxy ──► FastAPI Inference & SR API (:8099)
  │                                              ├── writes GeoJSON ──► geoserv/test_data/<zone>/
  │                                              └── POST /disasters/reload ──► GeoServ (:8088)
  └── /geo/*, /disasters/* ─────────────────► Rust Actix-Web GeoServ (:8088)
```

## 3. Service Port & Protocol Matrix

| Service | Directory | Port | Protocol | Primary Role |
| --- | --- | --- | --- | --- |
| Vue 2 SPA | `app/` | `8080` | HTTP | 10-workspace UI, offline XYZ tiles, `/api` proxy |
| Rust GeoServ | `geoserv/` | `8088` | HTTP | KDBush spatial GeoJSON & heatmap server |
| Python Inference API | `inference_api/` | `8099` | HTTP | Serialized job queue, Stage-1/2 inference, optional SR router |

## 4. Hardware & Capacity Baseline

- **Minimum CPU runtime**: 4 vCPU, 8 GB RAM (`RAHAT_DEVICE=cpu`, single-worker job queue).
- **Recommended GPU runtime**: NVIDIA CUDA GPU with >= 8 GB VRAM for Stage-1 UNet (`384x384`) and Stage-2 ResNet34 (`256x256`) crops.
- **Disk footprint**: ~53 MB offline map tiles (`app/public/tiles`), ~352 MB FastAI learners (`inference_api/models/*.pkl`), plus workspace uploads (`inference_api/work/`) and optional ONNX/PyTorch SR weights (`weights/`).

## 5. Verified Software Toolchain

| Component | Verified Local Version | Notes |
| --- | --- | --- |
| Python | `3.11.9` (`inference_api/.venv311`) | Required for FastAPI `0.103.1`, PyTorch `2.15.0`, fastai `2.8.12` |
| Rust / Cargo | `rustc 1.97.1` / `cargo 1.97.1` | Builds `geoserv` and `xview2_feature_extractor` |
| Node.js / npm | `v24.14.0` / `npm 11.16.0` | Uses `NODE_OPTIONS=--openssl-legacy-provider` for Webpack 4 |
| Yarn (optional) | `1.22.22` | Alternative frontend package runner |

## 6. Environment Variable Contract

### Core Inference API (`inference_api/main.py`)

- `RAHAT_INFER_MODE`: `real` (run models) or `demo` (synthetic GeoJSON detections).
- `RAHAT_DATA_DIR`: GeoServ zone directory (default `./geoserv/test_data`).
- `RAHAT_WORK_DIR`: Upload staging directory (default `./inference_api/work`).
- `RAHAT_MODEL_DIR`: Learner export directory (default `./inference_api/models`).
- `RAHAT_GEOSERV_URL`: GeoServ base URL (default `http://127.0.0.1:8088`).
- `RAHAT_DEVICE`, `RAHAT_API_HOST`, `RAHAT_API_PORT`, `RAHAT_MAX_UPLOAD_MB`, `RAHAT_MAX_JOBS`, `RAHAT_MIN_AREA`, `RAHAT_LOG_LEVEL`.

### NETRA SR, Copernicus CDSE & Blockchain (`inference_api/backend/`)

- `RAHAT_ROOT`: Optional explicit project root override.
- `KMP_DUPLICATE_LIB_OK`: Set `TRUE` on Windows to prevent duplicate OpenMP initialization conflicts.
- `SH_CLIENT_ID`, `SH_CLIENT_SECRET`, `SH_BASE_URL`, `SH_TOKEN_URL`: Copernicus Data Space Ecosystem OAuth2 credentials.
- `POLYGON_AMOY_RPC`, `POLYGON_CHAIN_ID` (`80002`), `CONTRACT_ADDRESS`, `POLYGON_WALLET_ADDRESS`, `POLYGON_PRIVATE_KEY`, `POLYGONSCAN_BASE_URL`.
- `VUE_APP_ABSOLUTE_URL`: Optional frontend prefix for static public asset URLs.

## 7. Storage Layout & Artifact Boundaries

| Path | Tracked in Git | Purpose |
| --- | --- | --- |
| `geoserv/test_data/` | Yes (demo scenes) | Per-zone `structures-affected.geojson`, `structures-unaffected.geojson`, `amenities.geojson` |
| `app/public/tiles/` | Yes (`833` files) | Offline XYZ PNG tiles for Palu, Harvey, Michael, Matthew |
| `inference_api/models/*.json` | Yes | Stage-1 & Stage-2 evaluation metadata rendered by Dashboard |
| `inference_api/models/*.pkl` | No (gitignored) | Exported FastAI Stage-1 (`236.65 MB`) & Stage-2 (`115.68 MB`) models |
| `inference_api/work/` | No (gitignored) | Per-job uploaded `before.tif` / `after.tif` pairs |
| `weights/`, `cache/`, `outputs/` | No (gitignored) | Optional SR ONNX/PyTorch weights, CDSE tile cache, and JSON provenance ledger |

## 8. Rollout Phase 1 — Rust GeoServ (`:8088`)

1. Verify `geoserv/test_data/` contains the 6 indexed zone folders and `geoserv/disaster-zones.json`.
2. Build and launch GeoServ:
   ```powershell
   cd geoserv
   cargo build --release
   cargo run --release -- --data-dir test_data --hostname 127.0.0.1 --port 8088
   ```
3. Confirm startup logs list feature counts for every `(group, layer)` pair.

## 9. Rollout Phase 2 — Python Inference API (`:8099`)

1. Create/activate Python `3.11` virtual environment (`inference_api/.venv311`).
2. Install core dependencies from `inference_api/requirements.txt`.
3. Confirm `predict_footprint_fine_tuned.pkl` and `predict_damage_unfrozen.pkl` exist in `inference_api/models/` (or set `RAHAT_INFER_MODE=demo` for smoke runs without weights).
4. Start Uvicorn from `inference_api/`:
   ```powershell
   cd inference_api
   .\.venv311\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8099
   ```

## 10. Rollout Phase 3 — Optional NETRA SR & Spectral Enablement

- `inference_api/main.py` mounts `backend.api.routes` (`/sr`, `/api/sr`, `/api`) inside a `try/except` block.
- When optional packages (`onnxruntime`, `sentinelhub`, `spyndex`, `leafmap`, `pyiqa`, `web3`, `python-dotenv`) are absent, core RAHAT routes stay active while SR modules enter documented fallback mode.
- Install full root `requirements.txt` and populate `weights/` + `.env` CDSE keys when deploying live Sentinel-2 10m -> 2.5m enhancement.

## 11. Rollout Phase 4 — Blockchain Provenance (`TileProvenance.sol`)

- Smart contract source and ABI live in `contracts/TileProvenance.sol` and `contracts/TileProvenance.json`.
- When `POLYGON_PRIVATE_KEY` and `CONTRACT_ADDRESS` are configured in `.env`, `ProvenanceManager` submits geo-tagged SHA-256 transactions on Polygon Amoy (`chainId=80002`).
- When `web3` or wallet credentials are omitted, `ProvenanceManager` writes version-chained records to `cache/blockchain_ledger.json`.

## 12. Rollout Phase 5 — Vue 2 Frontend (`:8080`)

1. Install dependencies in `app/` using `npm ci`.
2. Development server (with `/api` proxy to `127.0.0.1:8099` via `app/vue.config.js`):
   ```powershell
   cd app
   npm run serve
   ```
3. Production static bundle output (`app/dist/`):
   ```powershell
   npm run build
   ```

## 13. Pre-Flight Readiness Gates

- [ ] `.env` created from `.env.example`; real secrets never committed to Git.
- [ ] `geoserv/test_data/` and `geoserv/disaster-zones.json` readable on disk.
- [ ] `app/public/tiles/` (`833` PNGs) present for offline demo zones.
- [ ] Ports `8080`, `8088`, and `8099` free from conflicting stale processes.
- [ ] `infer.py --self-test` passes `20/20` checks prior to service startup.

## 14. Startup Sequence

1. **Start GeoServ first (`:8088`)** so `/disasters/zones` and `/disasters/reload` are ready when the API initializes health checks.
2. **Start Inference API second (`:8099`)** and verify `GET /health` reports `geoserv_reachable: true`.
3. **Start Vue SPA third (`:8080`)** (or serve `app/dist/` behind a reverse proxy forwarding `/api/*` -> `:8099` and GeoServ endpoints -> `:8088`).

## 15. Post-Startup Health & Diagnostics Checks

```powershell
curl.exe -s http://127.0.0.1:8088/disasters/zones
curl.exe -s http://127.0.0.1:8099/health
curl.exe -s http://127.0.0.1:8099/diagnostics
curl.exe -I http://127.0.0.1:8080/
```

- `/health` must return `status: "ready"` (`geoserv_reachable: true`, `missing_models: []`).
- `/diagnostics` must list non-empty `zones`, `models`, and `imagery` inventories.

## 16. End-to-End Smoke Validation Workflow

1. Submit a north-up georeferenced `before.tif` + `after.tif` pair via `/inference` UI or `POST /predict/disaster?zone_id=<zone>`.
2. Confirm HTTP `202` with a valid UUID4 `job_id`.
3. Poll `GET /jobs/{job_id}` until `status == "succeeded"`.
4. Verify `structures-affected.geojson` and `structures-unaffected.geojson` exist under `RAHAT_DATA_DIR/<zone>/` with valid `bbox` arrays.
5. Confirm GeoServ `/geo/<zone>/structures-affected` returns the updated polygons and Leaflet renders them on `/map`.

## 17. Logging & Observability

- **Python API**: Python `logging` configured via `RAHAT_LOG_LEVEL` (`INFO` default); logs job queueing, model load latency, and GeoServ reload outcomes to stdout.
- **Rust GeoServ**: `env_logger` (`RUST_LOG=info` default) + Actix `Logger::default()` access logs.
- **Vue SPA**: `App.vue` polls `/health`, `/diagnostics`, and `/jobs` every `10s` and surfaces connection failures in `serviceError` banners.

## 18. Queue & Inference Parameter Tuning

- `RAHAT_MAX_UPLOAD_MB=512`: Protects memory during multipart GeoTIFF ingestion (returns HTTP `413` above limit).
- `RAHAT_MAX_JOBS=4`: Limits queued + running jobs in `JobQueue` (returns HTTP `429` when full; worker semaphore serializes GPU/CPU execution `1` job at a time).
- `RAHAT_MIN_AREA=20`: Tuned minimum building area in `384x384` mask pixels (`EVALUATION` measured mean IoU `0.473` at `min_area=20` vs `0.082` at `400`).

## 19. CPU vs CUDA Execution Strategy

- FastAI exports (`predict_footprint_fine_tuned.pkl`, `predict_damage_unfrozen.pkl`) were exported on Python `3.13` / Linux; `inference_api/compat.py` patches cross-OS `PosixPath` / pickle compatibility at load time.
- Set `RAHAT_DEVICE=cpu` on CPU-only servers or `RAHAT_DEVICE=cuda` / `0` on NVIDIA GPU hosts.
- First real job loads both learners (~352 MB total); subsequent jobs reuse or run per invocation depending on CLI/worker path.

## 20. Offline Imagery & Basemap Strategy

- The 4 xBD demo scenes serve local XYZ tiles from `/tiles/<scene>/{before,after}/{z}/{x}/{y}.png` (`z15`–`z17`) shipped inside `app/public/tiles/`.
- `new-orleans` and `oman` in `geoserv/disaster-zones.json` point to `https://disavu.silentbyte.com/tiles/...` (external Maxar tiles) and OpenStreetMap base tiles require outbound internet unless proxied/mirrored.

## 21. Production Reverse-Proxy Architecture

In production, replace `vue-cli-service serve` (`:8080`) with Nginx/Caddy serving the compiled `app/dist/` bundle:

- Serve static SPA assets (`/` with `try_files $uri $uri/ /index.html` for Vue Router `history` mode).
- Proxy `/api/` (stripping `/api` prefix) to `http://127.0.0.1:8099/`.
- Proxy `/geo/` and `/disasters/` to `http://127.0.0.1:8088/` (or expose GeoServ directly on `:8088` with CORS).
