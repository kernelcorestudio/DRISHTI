# TESTING.md — DRISHTI / RAHAT Automated Testing Guide

Non-invasive test suite documentation covering the Python Inference API, Rust GeoServ spatial server, and Vue 2 frontend.

## 1. Testing Frameworks

| Service | Framework / Runner | Compatibility Notes |
| --- | --- | --- |
| Python Inference API | `pytest 9.2.0` + `httpx 0.28.1` (`ASGITransport`) | Compatible with Python `3.11.9` and FastAPI `0.103.1` |
| Inference Self-Test | Built-in `infer.py --self-test` | Standard library + NumPy/Shapely/PIL |
| Rust GeoServ | `cargo test` + `actix_web::test` | Uses `geoserv` crate library target (`src/lib.rs`) |
| Vue 2 Frontend | `@vue/cli-plugin-unit-jest@^4.5.19` + `@vue/test-utils@^1.3.6` | Compatible with Vue `2.6.11`, TS `4.1`, Vuetify `2.4` |
