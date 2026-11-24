# DEPLOYMENT.md — DRISHTI / RAHAT Deployment Guide

Step-by-step installation, configuration, startup, and verification instructions for the three-service **DRISHTI / RAHAT** platform.

## 1. System Requirements

- **OS**: Windows 10/11 or Linux (verified on Windows with PowerShell & Rust/Node/Python 3.11).
- **CPU / RAM**: Minimum 4 cores, 8 GB RAM (`RAHAT_DEVICE=cpu`).
- **GPU (optional)**: NVIDIA CUDA-capable GPU for accelerated Stage-1/Stage-2 PyTorch inference.
- **Storage**: >= 2 GB free space for Node dependencies, Rust build artifacts, FastAI model checkpoints (`~352 MB`), and uploaded GeoTIFF jobs.
