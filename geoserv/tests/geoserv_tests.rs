use std::collections::HashSet;
use std::fs;
use std::path::PathBuf;
use std::sync::{Arc, RwLock};
use std::time::{SystemTime, UNIX_EPOCH};

use actix_web::{test as actix_test, web, App};
use geoserv::api::{self, GeoServState};
use geoserv::geodata::{build_geo_indexes_from_directory_structure, GeoIndexBuilder};
use geoserv::kdbush::KDBush;

fn make_temp_dir(label: &str) -> PathBuf {
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let dir = std::env::temp_dir().join(format!("geoserv_test_{}_{}", label, nanos));
    fs::create_dir_all(&dir).unwrap();
    dir
}

fn sample_polygons_geojson() -> &'static str {
    r#"{
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": "b1",
                "properties": { "severity": "severe", "damage_probability": 0.94 },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[-90.02, 29.95], [-90.019, 29.95], [-90.019, 29.951], [-90.02, 29.951], [-90.02, 29.95]]]
                },
                "bbox": [-90.02, 29.95, -90.019, 29.951]
            },
            {
                "type": "Feature",
                "id": "b2",
                "properties": { "severity": "moderate", "damage_probability": 0.65 },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[-90.01, 29.96], [-90.009, 29.96], [-90.009, 29.961], [-90.01, 29.961], [-90.01, 29.96]]]
                },
                "bbox": [-90.01, 29.96, -90.009, 29.961]
            },
            {
                "type": "Feature",
                "id": "b3-outside",
                "properties": { "severity": "none", "damage_probability": 0.12 },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[58.50, 23.58], [58.51, 23.58], [58.51, 23.59], [58.50, 23.59], [58.50, 23.58]]]
                },
                "bbox": [58.50, 23.58, 58.51, 23.59]
            }
        ]
    }"#
}

fn sample_amenities_geojson() -> &'static str {
    r#"{
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": { "name": "City Hospital", "amenity": "hospital" },
                "geometry": { "type": "Point", "coordinates": [-90.015, 29.955] }
            }
        ]
    }"#
}

#[test]
fn kdbush_range_within_and_empty_index() {
    let empty = KDBush::new(0, 8);
    assert!(empty.is_empty());
    let mut hits = Vec::new();
    empty.range(0.0, 0.0, 10.0, 10.0, |id| hits.push(id));
    empty.within(0.0, 0.0, 5.0, |id| hits.push(id));
    assert!(hits.is_empty());

    let points = vec![(29.95, -90.02), (29.96, -90.01), (23.58, 58.50)];
    let index = KDBush::create(points, 2);
    assert_eq!(index.len(), 3);

    let mut box_hits = HashSet::new();
    index.range(29.94, -90.03, 29.97, -90.0, |id| {
        box_hits.insert(id);
    });
    assert_eq!(box_hits, HashSet::from([0, 1]));

    let mut limited = Vec::new();
    index.range_with_predicate(29.94, -90.03, 29.97, -90.0, |id| {
        limited.push(id);
        limited.len() < 1
    });
    assert_eq!(limited.len(), 1);

    let mut radius_hits = Vec::new();
    index.within(29.95, -90.02, 0.02, |id| radius_hits.push(id));
    assert!(radius_hits.contains(&0));
    assert!(!radius_hits.contains(&2));
}

#[test]
fn geodata_loads_polygons_points_and_heatmap_centroids() {
    let root = make_temp_dir("load");
    let zone_dir = root.join("new-orleans");
    fs::create_dir_all(&zone_dir).unwrap();
    fs::write(zone_dir.join("structures-affected.geojson"), sample_polygons_geojson()).unwrap();
    fs::write(zone_dir.join("amenities.geojson"), sample_amenities_geojson()).unwrap();

    let indexes = build_geo_indexes_from_directory_structure(root.to_str().unwrap()).unwrap();
    assert_eq!(indexes.len(), 2);

    let affected = indexes.get(&("new-orleans".into(), "structures-affected".into())).unwrap();
    assert_eq!(affected.len(), 3);
    assert_eq!(affected.heatmap().len(), 3);

    // Centroid of first polygon bbox [-90.02, 29.95, -90.019, 29.951] -> (29.9505, -90.0195).
    let first_heat = affected.heatmap()[0];
    assert!((first_heat.0 - 29.9505).abs() < 1e-6);
    assert!((first_heat.1 - (-90.0195)).abs() < 1e-6);

    // Viewport around New Orleans must exclude Oman polygon b3-outside and deduplicate bbox corners.
    let in_view = affected.query_within_viewport(29.98, -90.0, 29.94, -90.03, 100);
    assert_eq!(in_view.len(), 2);

    // Limit = 1 restricts returned features.
    let capped = affected.query_within_viewport(29.98, -90.0, 29.94, -90.03, 1);
    assert_eq!(capped.len(), 1);

    let amenities = indexes.get(&("new-orleans".into(), "amenities".into())).unwrap();
    assert_eq!(amenities.len(), 1);
    assert_eq!(amenities.heatmap(), &[(29.955, -90.015)]);

    fs::remove_dir_all(&root).unwrap();
}

#[test]
fn geodata_rejects_invalid_geojson_and_handles_empty_datasets() {
    let root = make_temp_dir("invalid");

    // Empty directory yields an empty index map.
    let empty_indexes = build_geo_indexes_from_directory_structure(root.to_str().unwrap()).unwrap();
    assert!(empty_indexes.is_empty());

    // Empty FeatureCollection loads with 0 features and empty heatmap.
    let empty_fc_path = root.join("empty.geojson");
    fs::write(&empty_fc_path, r#"{"type":"FeatureCollection","features":[]}"#).unwrap();
    let empty_idx = GeoIndexBuilder::new()
        .add_features_from_file(&empty_fc_path)
        .unwrap()
        .build();
    assert_eq!(empty_idx.len(), 0);
    assert!(empty_idx.heatmap().is_empty());
    assert!(empty_idx.query_within_viewport(90.0, 180.0, -90.0, -180.0, 10).is_empty());

    // Malformed JSON -> Err.
    let bad_json_path = root.join("bad.geojson");
    fs::write(&bad_json_path, "{ not valid json").unwrap();
    assert!(GeoIndexBuilder::new().add_features_from_file(&bad_json_path).is_err());

    // Valid GeoJSON that is not a FeatureCollection -> Err.
    let non_fc_path = root.join("point.geojson");
    fs::write(&non_fc_path, r#"{"type":"Point","coordinates":[0.0,0.0]}"#).unwrap();
    assert!(GeoIndexBuilder::new().add_features_from_file(&non_fc_path).is_err());

    // Polygon missing bbox -> Err ("unsupported feature type").
    let no_bbox_poly = root.join("nobbox.geojson");
    fs::write(
        &no_bbox_poly,
        r#"{"type":"FeatureCollection","features":[{"type":"Feature","properties":{},"geometry":{"type":"Polygon","coordinates":[[[0,0],[1,0],[1,1],[0,0]]]}}]}"#,
    )
    .unwrap();
    assert!(GeoIndexBuilder::new().add_features_from_file(&no_bbox_poly).is_err());

    fs::remove_dir_all(&root).unwrap();
}

#[actix_web::test]
async fn http_routes_viewport_heatmap_and_reload_work() {
    let root = make_temp_dir("http");
    let data_dir = root.join("data");
    let zone_dir = data_dir.join("zone-one");
    fs::create_dir_all(&zone_dir).unwrap();
    fs::write(zone_dir.join("structures-affected.geojson"), sample_polygons_geojson()).unwrap();

    let zones_config_path = root.join("disaster-zones.json");
    fs::write(
        &zones_config_path,
        r#"[{"id":"1","name":"Zone One","center":{"lat":29.95,"lng":-90.02,"zoom":17}}]"#,
    )
    .unwrap();

    let indexes = build_geo_indexes_from_directory_structure(data_dir.to_str().unwrap()).unwrap();
    let config_val: serde_json::Value =
        serde_json::from_str(&fs::read_to_string(&zones_config_path).unwrap()).unwrap();

    let state = Arc::new(GeoServState {
        geo_indexes: RwLock::new(indexes),
        zones_config: RwLock::new(config_val),
        data_dir: data_dir.to_string_lossy().into_owned(),
        zones_config_path: zones_config_path.to_string_lossy().into_owned(),
    });

    let app = actix_test::init_service(
        App::new()
            .app_data(web::Data::new(state.clone()))
            .service(web::resource("/geo/{group}/{name}").route(web::get().to(api::geo_route)))
            .service(
                web::resource("/geo/{group}/{name}/heatmap")
                    .route(web::get().to(api::geo_heatmap_route)),
            )
            .service(web::resource("/disasters/zones").route(web::get().to(api::get_zones_route)))
            .service(web::resource("/disasters/reload").route(web::post().to(api::reload_zones_route))),
    )
    .await;

    // 1. Viewport query returns only features inside bounding box.
    let req = actix_test::TestRequest::get()
        .uri("/geo/zone-one/structures-affected?ne_lat=29.98&ne_lng=-90.0&sw_lat=29.94&sw_lng=-90.03&limit=10")
        .to_request();
    let features: Vec<serde_json::Value> = actix_test::call_and_read_body_json(&app, req).await;
    assert_eq!(features.len(), 2);

    // 2. Heatmap endpoint returns all feature centroids.
    let hm_req = actix_test::TestRequest::get()
        .uri("/geo/zone-one/structures-affected/heatmap")
        .to_request();
    let heatmap: Vec<Vec<f64>> = actix_test::call_and_read_body_json(&app, hm_req).await;
    assert_eq!(heatmap.len(), 3);

    // 3. Unknown layer returns 404.
    let missing_req = actix_test::TestRequest::get()
        .uri("/geo/zone-one/missing-layer?ne_lat=1&ne_lng=1&sw_lat=0&sw_lng=0")
        .to_request();
    let missing_resp = actix_test::call_service(&app, missing_req).await;
    assert_eq!(missing_resp.status().as_u16(), 404);

    // 4. Write a second zone on disk + update zones config, then trigger /disasters/reload.
    let zone2_dir = data_dir.join("zone-two");
    fs::create_dir_all(&zone2_dir).unwrap();
    fs::write(zone2_dir.join("amenities.geojson"), sample_amenities_geojson()).unwrap();
    fs::write(
        &zones_config_path,
        r#"[{"id":"1","name":"Zone One"},{"id":"2","name":"Zone Two"}]"#,
    )
    .unwrap();

    let reload_req = actix_test::TestRequest::post().uri("/disasters/reload").to_request();
    let reload_body: serde_json::Value = actix_test::call_and_read_body_json(&app, reload_req).await;
    assert_eq!(reload_body["status"], "reloaded");

    let zones_req = actix_test::TestRequest::get().uri("/disasters/zones").to_request();
    let zones: Vec<serde_json::Value> = actix_test::call_and_read_body_json(&app, zones_req).await;
    assert_eq!(zones.len(), 2);

    let zone2_req = actix_test::TestRequest::get()
        .uri("/geo/zone-two/amenities?ne_lat=30.0&ne_lng=-90.0&sw_lat=29.9&sw_lng=-90.1")
        .to_request();
    let zone2_features: Vec<serde_json::Value> = actix_test::call_and_read_body_json(&app, zone2_req).await;
    assert_eq!(zone2_features.len(), 1);

    // 6. Reload must still succeed even if zones_config_path does not exist on disk.
    fs::remove_file(&zones_config_path).unwrap();
    let reload_no_cfg = actix_test::TestRequest::post().uri("/disasters/reload").to_request();
    let reload_no_cfg_body: serde_json::Value =
        actix_test::call_and_read_body_json(&app, reload_no_cfg).await;
    assert_eq!(reload_no_cfg_body["status"], "reloaded");

    fs::remove_dir_all(&root).unwrap();
}

#[test]
fn kdbush_empty_create_and_null_geometry_do_not_panic() {
    let empty = KDBush::create(Vec::<(f64, f64)>::new(), 0);
    assert!(empty.is_empty());

    let root = make_temp_dir("edge");
    let null_geom = root.join("null_geom.geojson");
    fs::write(
        &null_geom,
        r#"{"type":"FeatureCollection","features":[{"type":"Feature","properties":{},"geometry":null}]}"#,
    )
    .unwrap();
    assert!(GeoIndexBuilder::new().add_features_from_file(&null_geom).is_err());

    let short_pt = root.join("short_point.geojson");
    fs::write(
        &short_pt,
        r#"{"type":"FeatureCollection","features":[{"type":"Feature","properties":{},"geometry":{"type":"Point","coordinates":[12.3]}}]}"#,
    )
    .unwrap();
    assert!(GeoIndexBuilder::new().add_features_from_file(&short_pt).is_err());

    fs::remove_dir_all(&root).unwrap();
}
