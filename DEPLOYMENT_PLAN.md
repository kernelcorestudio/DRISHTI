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
