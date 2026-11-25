/*
 * GEOSERV
 * Copyright (c) 2022 SilentByte <https://silentbyte.com/>
 */

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

    /// the images directory of the XView2 training data.
    #[argh(option, default = "8088")]
    port: u16,

    /// the directory where the GeoJSON files are located.
    #[argh(option)]
    data_dir: String,

    /// the number of worker threads to use.
    #[argh(option, default = "4")]
    workers: usize,
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
    let config_path = "disaster-zones.json".to_string();
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
            .wrap(Cors::default().allow_any_origin())
            .wrap(Compress::default())
            .app_data(web::Data::new(state.clone()))
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
