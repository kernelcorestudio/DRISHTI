/*
 * GEOSERV
 * Copyright (c) 2022 SilentByte <https://silentbyte.com/>
 */

use std::collections::HashMap;
use std::sync::Arc;

use actix_web::{
    web,
    HttpResponse,
    Responder,
    Result as ActixResult,
};
use serde::Deserialize;

use crate::geodata::GeoIndex;
use std::sync::RwLock;

pub struct GeoServState {
    pub geo_indexes: RwLock<HashMap<(String, String), GeoIndex>>,
    pub zones_config: RwLock<serde_json::Value>,
    pub data_dir: String,
    pub zones_config_path: String,
}

pub type SharedState = Arc<GeoServState>;

#[derive(Deserialize, Debug)]
pub struct ViewportQueryParams {
    ne_lat: f64,
    ne_lng: f64,
    sw_lat: f64,
    sw_lng: f64,
    limit: Option<usize>,
}

impl std::fmt::Display for ViewportQueryParams {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(
            f,
            "({} {}, {} {})",
            self.ne_lat, self.ne_lng, self.sw_lat, self.sw_lng
        )
    }
}

pub async fn geo_route(
    state: web::Data<SharedState>,
    path: web::Path<(String, String)>,
    viewport: web::Query<ViewportQueryParams>,
) -> ActixResult<impl Responder> {
    let (group, name) = path.into_inner();
    let limit = viewport.limit.unwrap_or(100).min(10_000);
    let indexes = state.geo_indexes.read().unwrap();
    let features = indexes
        .get(&(group, name))
        .ok_or_else(|| actix_web::error::ErrorNotFound("no such geospatial data"))?
        .query_within_viewport(
            viewport.ne_lat,
            viewport.ne_lng,
            viewport.sw_lat,
            viewport.sw_lng,
            limit,
        );

    Ok(HttpResponse::Ok().json(&features))
}
pub async fn geo_heatmap_route(
    state: web::Data<SharedState>,
    path: web::Path<(String, String)>,
) -> ActixResult<impl Responder> {
    let (group, name) = path.into_inner();
    let indexes = state.geo_indexes.read().unwrap();
    let heatmap = indexes
        .get(&(group, name))
        .ok_or_else(|| actix_web::error::ErrorNotFound("no such geospatial data"))?
        .heatmap();

    Ok(HttpResponse::Ok().json(&heatmap))
}

pub async fn get_zones_route(
    state: web::Data<SharedState>,
) -> ActixResult<impl Responder> {
    let config = state.zones_config.read().unwrap();
    Ok(HttpResponse::Ok().json(&*config))
}

pub async fn reload_zones_route(
    state: web::Data<SharedState>,
) -> ActixResult<impl Responder> {
    // Reload logic to be called from main or we can implement it here.
    // For simplicity, we just reload the config file here.
    let config_data = std::fs::read_to_string(&state.zones_config_path)
        .map_err(|_| actix_web::error::ErrorInternalServerError("Failed to read config"))?;
    let config: serde_json::Value = serde_json::from_str(&config_data)
        .map_err(|_| actix_web::error::ErrorInternalServerError("Failed to parse config"))?;
    
    *state.zones_config.write().unwrap() = config;
    
    // Re-read the zones file and rebuild the geospatial indexes from disk.
    crate::geodata::reload_geo_indexes(&state).map_err(|_| actix_web::error::ErrorInternalServerError("Failed to reload indexes"))?;
    
    Ok(HttpResponse::Ok().json(serde_json::json!({"status": "reloaded"})))
}
