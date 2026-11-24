# DRISHTI / RAHAT Deployment Plan

Production and local rollout plan for **DRISHTI** (*Disaster Response Intelligence System with Hallucination-aware Trust Indicators*), unifying **RAHAT** (Rescue Allocation & Hazard Assessment Tool) and **NETRA** (Sentinel-2 Super-Resolution & Spectral Mapping).

## 1. Executive Scope & Objectives

- Preserve the existing three-service runtime topology without breaking working endpoints or GeoJSON contracts.
- Standardize environment variables via `.env.example` with zero hardcoded credentials.
- Ensure deterministic startup order, health verification, and clear fallback behavior when optional ML/Web3 packages or GPU hardware are absent.
