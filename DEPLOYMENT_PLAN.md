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
