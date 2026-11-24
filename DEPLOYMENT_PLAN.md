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
