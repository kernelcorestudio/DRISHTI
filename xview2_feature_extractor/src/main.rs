/*
 * XVIEW2 FEATURE EXTRACTOR
 * Copyright (c) 2021 SilentByte <https://silentbyte.com/>
 */

use std::convert::TryFrom;
use std::path::{
    Path,
    PathBuf,
};

use argh::FromArgs;
use geo::algorithm::bounding_rect::BoundingRect;
use geo::algorithm::intersects::Intersects;
use image::{
    imageops,
    DynamicImage,
    ImageBuffer,
    Pixel,
    RgbImage,
};
use imageproc::drawing::Canvas;
use rayon::prelude::*;
use serde::Deserialize;

/// XView2 Feature Extractor.
#[derive(Debug, Clone, FromArgs)]
struct Args {
    /// the labels directory of the XView2 training data.
    #[argh(option)]
    labels_dir: String,

    /// the images directory of the XView2 training data.
    #[argh(option)]
    images_dir: String,

    /// the output directory where the images should be saved.
    #[argh(option)]
    output_dir: String,

    /// only load label files that start with the specified value.
    #[argh(option, default = r#""".into()"#)]
    labels_prefix: String,

    /// the size of the output image.
    #[argh(option, default = "256")]
    output_size: u32,
}

#[derive(Deserialize, Debug)]
struct GeoMetadata {
    img_name: String,
}

#[derive(Deserialize, Debug)]
struct GeoProperties {
    uid: String,
}

#[derive(Deserialize, Debug)]
struct GeoFeature {
    properties: GeoProperties,
    wkt: String,
}

#[derive(Deserialize, Debug)]
struct GeoFeatureCollection {
    xy: Vec<GeoFeature>,
}

#[derive(Deserialize, Debug)]
struct GeoData {
    metadata: GeoMetadata,
    features: GeoFeatureCollection,
}

fn parse_labels_file(path: &PathBuf) -> anyhow::Result<GeoData> {
    let file = std::fs::File::open(path)?;
    let reader = std::io::BufReader::new(file);

    Ok(serde_json::from_reader(reader)?)
}

fn process_feature(
    wkt: &str,
    source_image: &DynamicImage,
    output_path: &PathBuf,
    output_size: u32,
) -> anyhow::Result<()> {
    let polygon_data: wkt::Wkt<f64> = wkt::Wkt::from_str(wkt).map_err(anyhow::Error::msg)?;
    let polygon = geo::Polygon::try_from(polygon_data)
        .map_err(|_| anyhow::Error::msg("Failed to parse WKT"))?;

    let bbox = polygon
        .bounding_rect()
        .ok_or(anyhow::Error::msg("Failed to calculate bbox"))?;

    let image_width = Canvas::width(source_image);
    let image_height = Canvas::height(source_image);

    let left = bbox.min().x.max(0f64) as u32;
    let right = bbox.max().x.min(image_width as f64) as u32;
    let top = bbox.min().y.max(0f64) as u32;
    let bottom = bbox.max().y.min(image_height as f64) as u32;
    if right <= left || bottom <= top {
        return Err(anyhow::Error::msg("Feature bbox lies outside image bounds"));
    }

    let buf_width = (right - left).max(1);
    let buf_height = (bottom - top).max(1);
    let mut feature_image: RgbImage = ImageBuffer::new(buf_width, buf_height);

    for x in left..right {
        for y in top..bottom {
            if polygon.intersects(&geo::Point::from((x as f64 + 0.5, y as f64 + 0.5))) {
                let ix = x - left;
                let iy = y - top;
                if ix < feature_image.width() && iy < feature_image.height() {
                    feature_image.draw_pixel(
                        ix,
                        iy,
                        Canvas::get_pixel(source_image, x, y).to_rgb(),
                    );
                }
            }
        }
    }

    let feature_image_width = feature_image.width() as f64;
    let feature_image_height = feature_image.height() as f64;
    let aspect_ratio = feature_image_width / feature_image_height;

    let (scaled_width, scaled_height) = if aspect_ratio >= 1.0 {
        (output_size as f64, output_size as f64 / aspect_ratio)
    } else {
        (output_size as f64 * aspect_ratio, output_size as f64)
    };
    let scaled_w_u32 = (scaled_width.round() as u32).clamp(1, output_size);
    let scaled_h_u32 = (scaled_height.round() as u32).clamp(1, output_size);

    let scaled_feature_image = imageops::resize(
        &feature_image,
        scaled_w_u32,
        scaled_h_u32,
        imageops::FilterType::Gaussian,
    );

    let mut output_image: RgbImage = ImageBuffer::new(output_size, output_size);

    imageops::overlay(
        &mut output_image,
        &scaled_feature_image,
        (output_size - scaled_w_u32) / 2,
        (output_size - scaled_h_u32) / 2,
    );

    output_image.save(output_path)?;

    Ok(())
}

fn extract_features_from_file(args: &Args, path: &PathBuf) -> anyhow::Result<()> {
    let labels_data = parse_labels_file(path)?;
    let source_image_path = Path::new(&args.images_dir).join(labels_data.metadata.img_name);
    let source_image = image::open(source_image_path)?;

    let label_file_name = Path::new(
        path.file_name()
            .ok_or(anyhow::Error::msg("Could not determine file name"))?,
    )
    .with_extension("")
    .to_string_lossy()
    .into_owned();

    labels_data.features.xy.par_iter().for_each(|feature| {
        let output_path = Path::new(&args.output_dir).join(format!(
            "{}_{}.png",
            label_file_name, feature.properties.uid,
        ));

        log::debug!(
            "Thread #{} is processing {}:{}",
            rayon::current_thread_index().unwrap_or(0),
            label_file_name,
            feature.properties.uid,
        );

        if let Err(e) = process_feature(&feature.wkt, &source_image, &output_path, args.output_size)
        {
            log::error!(
                "Processing of {:?}:{} failed: {:?}",
                path,
                feature.properties.uid,
                e
            )
        }
    });
    Ok(())
}

fn main() -> anyhow::Result<()> {
    env_logger::init_from_env(
        env_logger::Env::default().filter_or(env_logger::DEFAULT_FILTER_ENV, "INFO"),
    );

    let args: Args = argh::from_env();
    std::fs::create_dir_all(&args.output_dir)?;
    let label_files = std::fs::read_dir(args.labels_dir.clone())?
        .into_iter()
        .filter_map(|f| match f {
            Ok(f) if f.path().is_file() => Some(f),
            Ok(_) => None,
            _ => {
                log::error!("Could not read directory entry");
                None
            }
        })
        .filter(|f| {
            f.path().extension().and_then(|s| s.to_str()) == Some("json")
                && match f.file_name().to_str() {
                    Some(file_name) => file_name.starts_with(&args.labels_prefix),
                    _ => {
                        log::error!("Cannot parse file name {:?}", f.file_name());
                        false
                    }
                }
        })
        .map(|f| f.path())
        .collect::<Vec<_>>();

    let n = label_files.len();
    label_files.par_iter().enumerate().for_each(|(i, f)| {
        log::info!("Processing [{: >4}/{: >4}] {:?}", i + 1, n, f);
        if let Err(e) = extract_features_from_file(&args, &f) {
            log::error!("Failed to process {:?}: {:?}", f, e);
        }
    });

    Ok(())
}
