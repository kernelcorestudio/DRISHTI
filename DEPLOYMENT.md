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
