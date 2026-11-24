/*
 * GEOSERV
 * Copyright (c) 2022 SilentByte <https://silentbyte.com/>
 */

use std::path::Path;
use std::sync::{Arc, RwLock};

use actix_cors::Cors;
use actix_web::middleware::{
    Compress,
    Logger,
};
use actix_web::{
    web,
    App,
    HttpServer,
};
use argh::FromArgs;
use geoserv::api::{self, GeoServState};
use geoserv::geodata::build_geo_indexes_from_directory_structure;
use itertools::Itertools;

/// GeoServ.
#[derive(Debug, Clone, FromArgs)]
struct Args {
    /// the hostname on which the server will start listening.
    #[argh(option, default = r#""127.0.0.1".into()"#)]
    hostname: String,

    /// the port on which the server will listen.
    #[argh(option, default = "8088")]
    port: u16,

    /// the directory where the GeoJSON files are located.
    #[argh(option)]
    data_dir: String,

    /// optional path to disaster-zones.json configuration.
    #[argh(option)]
    zones_config: Option<String>,

    /// the number of worker threads to use.
    #[argh(option, default = "4")]
    workers: usize,
}

fn resolve_zones_config_path(data_dir: &str, explicit: Option<String>) -> String {
    if let Some(path) = explicit {
        return path;
    }
    let cwd_cfg = Path::new("disaster-zones.json");
    if cwd_cfg.exists() {
        return cwd_cfg.to_string_lossy().into_owned();
    }
    if let Some(parent) = Path::new(data_dir).parent() {
        let sibling = parent.join("disaster-zones.json");
        if sibling.exists() {
            return sibling.to_string_lossy().into_owned();
        }
    }
    cwd_cfg.to_string_lossy().into_owned()
}

#[actix_web::main]
async fn main() -> anyhow::Result<()> {
    env_logger::init_from_env(
        env_logger::Env::default().filter_or(env_logger::DEFAULT_FILTER_ENV, "INFO"),
    );

    let args: Args = argh::from_env();
    let bind_address = format!("{}:{}", args.hostname, args.port);

    log::info!(
        "Starting GeoServ on {}, serving {}",
        bind_address,
        args.data_dir
    );

    let geo_indexes = build_geo_indexes_from_directory_structure(&args.data_dir)?;
    let config_path = resolve_zones_config_path(&args.data_dir, args.zones_config);
    let config_data = std::fs::read_to_string(&config_path)
        .unwrap_or_else(|_| "[]".to_string());
    let zones_config: serde_json::Value = serde_json::from_str(&config_data)?;

    let state = Arc::new(GeoServState {
        geo_indexes: RwLock::new(geo_indexes),
        zones_config: RwLock::new(zones_config),
        data_dir: args.data_dir.clone(),
        zones_config_path: config_path,
    });

    log::info!("The following geospatial data is available:");
    state.geo_indexes.read().unwrap()
        .iter()
        .map(|(k, v)| format!("{}/{}: {} feature(s)", k.0, k.1, v.len()))
        .sorted()
        .for_each(|e| log::info!("{}", e));

    HttpServer::new(move || {
        App::new()
            .wrap(Logger::default())
            .wrap(Cors::permissive())
            .wrap(Compress::default())
            .app_data(web::Data::new(state.clone()))
            .service(web::resource("/health").route(web::get().to(api::health_route)))
            .service(web::resource("/geo/{group}/{name}").route(web::get().to(api::geo_route)))
            .service(
                web::resource("/geo/{group}/{name}/heatmap")
                    .route(web::get().to(api::geo_heatmap_route)),
            )
            .service(web::resource("/disasters/zones").route(web::get().to(api::get_zones_route)))
            .service(web::resource("/disasters/reload").route(web::post().to(api::reload_zones_route)))
    })
    .workers(args.workers)
    .bind(bind_address)
    .map_err(|e| anyhow::anyhow!(e))?
    .run()
    .await?;

    Ok(())
}
