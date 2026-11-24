# DEPLOYMENT.md — DRISHTI / RAHAT Deployment Guide

Step-by-step installation, configuration, startup, and verification instructions for the three-service **DRISHTI / RAHAT** platform.

## 1. System Requirements

- **OS**: Windows 10/11 or Linux (verified on Windows with PowerShell & Rust/Node/Python 3.11).
- **CPU / RAM**: Minimum 4 cores, 8 GB RAM (`RAHAT_DEVICE=cpu`).
- **GPU (optional)**: NVIDIA CUDA-capable GPU for accelerated Stage-1/Stage-2 PyTorch inference.
- **Storage**: >= 2 GB free space for Node dependencies, Rust build artifacts, FastAI model checkpoints (`~352 MB`), and uploaded GeoTIFF jobs.

## 2. Required Software

- **Python**: `3.11` (verified `Python 3.11.9` in `inference_api/.venv311`).
- **Rust & Cargo**: Stable toolchain `1.70+` (verified `cargo 1.97.1`, `rustc 1.97.1`).
- **Node.js & npm**: Node `16+` (verified `v24.14.0`, `npm 11.16.0`; webpack scripts automatically pass `--openssl-legacy-provider`).

## 3. Dependency Installation

### Python Inference API (`inference_api/`)

```powershell
cd inference_api
python -m venv .venv311
.\.venv311\Scripts\python.exe -m pip install -r requirements.txt
```

> Note: Core RAHAT requires `fastapi`, `uvicorn`, `torch`, `fastai`, `cloudpickle`, `shapely`, `pillow`, `scikit-image`, `opencv-python-headless`, and `requests`. Optional NETRA SR features use `onnxruntime`, `sentinelhub`, `spyndex`, `leafmap`, `pyiqa`, `web3`, and `python-dotenv` (also listed in root `requirements.txt`).

### Rust GeoServ (`geoserv/`)

Dependencies are locked in `geoserv/Cargo.toml` and `geoserv/Cargo.lock`:

```powershell
cd geoserv
cargo build --release
```

### Vue Frontend (`app/`)

Dependencies are locked in `app/package.json` and `app/package-lock.json`:

```powershell
cd app
npm ci
```

## 4. Environment Configuration

Copy `.env.example` to `.env` at the repository root and adjust values for your host:

```powershell
Copy-Item .env.example .env
```

Keep real credentials (`SH_CLIENT_ID`, `SH_CLIENT_SECRET`, `POLYGON_PRIVATE_KEY`) strictly inside `.env` (gitignored).
