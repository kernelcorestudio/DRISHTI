/*
 * GEOSERV
 * Copyright (c) 2022 SilentByte <https://silentbyte.com/>
 */

use std::collections::{BTreeMap, HashMap};
use std::fs::File;
use std::io::BufReader;
use std::path::Path;

use crate::api::SharedState;
use crate::kdbush::KDBush;

pub type GeoPoint = (f64, f64);

pub struct GeoIndex {
    index: KDBush,
    data: HashMap<usize, geojson::Feature>,
    heatmap: Vec<GeoPoint>,
}

impl std::fmt::Debug for GeoIndex {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(
            f,
            "[GeoIndex {} points, {} features]",
            self.index.len(),
            self.data.len()
        )
    }
}

impl GeoIndex {
    pub fn query_within_viewport(
        &self,
        ne_lat: f64,
        ne_lng: f64,
        sw_lat: f64,
        sw_lng: f64,
        limit: usize,
    ) -> Vec<&geojson::Feature> {
        let min_lat = sw_lat.min(ne_lat);
        let max_lat = sw_lat.max(ne_lat);
        let min_lng = sw_lng.min(ne_lng);
        let max_lng = sw_lng.max(ne_lng);

        let mut unique_features = BTreeMap::new();
        self.index
            .range_with_predicate(min_lat, min_lng, max_lat, max_lng, |id| {
                if let Some(feature) = self.data.get(&id) {
                    unique_features.entry(id).or_insert(feature);
                }

                unique_features.len() < limit
            });

        unique_features.values().take(limit).cloned().collect()
    }

    pub fn heatmap(&self) -> &[GeoPoint] {
        &self.heatmap
    }

    pub fn len(&self) -> usize {
        return self.data.len();
    }
}

const DEFAULT_NODE_SIZE: u8 = 64;

#[derive(Debug)]
pub struct GeoIndexBuilder {
    geo_index: GeoIndex,
    auto_index_counter: usize,
}

impl GeoIndexBuilder {
    pub fn new() -> Self {
        GeoIndexBuilder {
            geo_index: GeoIndex {
                index: KDBush::new(0, DEFAULT_NODE_SIZE),
                data: HashMap::new(),
                heatmap: Vec::new(),
            },
            auto_index_counter: 0,
        }
    }

    fn generate_id(&mut self) -> usize {
        let id = self.auto_index_counter;
        self.auto_index_counter += 1;
        id
    }

    fn add_bbox_points(&mut self, id: usize, bbox: &geojson::Bbox) -> anyhow::Result<()> {
        let (min_lng, min_lat, max_lng, max_lat) = match bbox.len() {
            4 => (bbox[0], bbox[1], bbox[2], bbox[3]),
            6 => (bbox[0], bbox[1], bbox[3], bbox[4]),
            other => anyhow::bail!("GeoJSON bbox has unexpected length {}", other),
        };

        for (lat, lng) in [
            (min_lat, min_lng),
            (min_lat, max_lng),
            (max_lat, max_lng),
            (max_lat, min_lng),
        ] {
            self.geo_index.index.add_point(id, lat, lng);
        }

        self.geo_index.heatmap.push((
            (min_lat + max_lat) / 2.0,
            (min_lng + max_lng) / 2.0,
        ));
        Ok(())
    }

    fn add_point_points(&mut self, id: usize, point: &geojson::PointType) -> anyhow::Result<()> {
        if point.len() < 2 {
            anyhow::bail!("Point geometry missing coordinates");
        }
        self.geo_index.index.add_point(id, point[1], point[0]);
        self.geo_index.heatmap.push((point[1], point[0]));
        Ok(())
    }

    pub fn add_features_from_file(mut self, path: &Path) -> anyhow::Result<Self> {
        let file = File::open(path)?;
        let reader = BufReader::new(file);
        let geo_data: geojson::GeoJson = serde_json::from_reader(reader)?;

        let feature_collection = match geo_data {
            geojson::GeoJson::FeatureCollection(fc) => fc,
            _ => anyhow::bail!("{} does not contain a feature collection", path.display()),
        };

        for feature in feature_collection.features {
            let id = self.generate_id();

            if let Some(bbox) = &feature.bbox {
                self.add_bbox_points(id, bbox)?;
            } else {
                let geom = feature.geometry.as_ref().ok_or_else(|| {
                    anyhow::anyhow!("{} contains a feature without geometry or bbox", path.display())
                })?;
                match &geom.value {
                    geojson::Value::Point(point) => self.add_point_points(id, point)?,
                    _ => anyhow::bail!("{} contains an unsupported feature type", path.display()),
                };
            }

            self.geo_index.data.insert(id, feature);
        }

        Ok(self)
    }

    pub fn build(mut self) -> GeoIndex {
        self.geo_index.index.build_index();
        self.geo_index
    }
}

/// Builds an index for every `<data_dir>/*/*.geojson` file, keyed by (group, name).
pub fn build_geo_indexes_from_directory_structure(
    data_dir: &str,
) -> anyhow::Result<HashMap<(String, String), GeoIndex>> {
    let root = Path::new(data_dir);
    if !root.exists() {
        anyhow::bail!("Data directory does not exist: {}", root.display());
    }

    let mut geo_indexes = HashMap::new();

    for group_entry in std::fs::read_dir(root)? {
        let group_entry = group_entry?;
        let group_path = group_entry.path();
        if !group_path.is_dir() {
            continue;
        }
        let group = group_entry.file_name().to_string_lossy().into_owned();

        for file_entry in std::fs::read_dir(&group_path)? {
            let file_entry = file_entry?;
            let path = file_entry.path();
            if !path.is_file() || path.extension().and_then(|s| s.to_str()) != Some("geojson") {
                continue;
            }
            let Some(name) = path.file_stem().and_then(|s| s.to_str()).map(str::to_owned) else {
                continue;
            };

            log::info!("Parsing {}", path.display());
            geo_indexes.insert(
                (group.clone(), name),
                GeoIndexBuilder::new().add_features_from_file(&path)?.build(),
            );
        }
    }

    Ok(geo_indexes)
}

/// Rebuilds all indexes from disk and swaps them into the shared state.
pub fn reload_geo_indexes(state: &SharedState) -> anyhow::Result<()> {
    let geo_indexes = build_geo_indexes_from_directory_structure(&state.data_dir)?;
    *state.geo_indexes.write().unwrap() = geo_indexes;
    Ok(())
}
