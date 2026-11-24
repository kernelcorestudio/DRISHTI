/*
 * DISASTER RESPONSE APP
 * Copyright (c) 2021 SilentByte <https://silentbyte.com/>
 */

export type Opaque<K, T> = T & { __TYPE__: K };
export type Uuid = Opaque<"Uuid", string>;

export interface ILatLng {
    lat: number;
    lng: number;
}

export interface ILayerData {
    urlTemplate: string;
    attributionHtml: string;
}

export interface IDisasterZone {
    id: Uuid;
    name: string;
    center: {
        lat: number;
        lng: number;
        zoom: number;
    };
    beforeLayer: ILayerData | null;
    afterLayer: ILayerData | null;
    amenitiesUrl: string | null;
    affectedStructuresUrl: string | null;
    unaffectedStructuresUrl: string | null;
    heatmapUrl: string | null;
}

// Mirrors the payloads of inference_api/main.py; the dashboard renders them without reshaping.
export interface IHealth {
    status: "ready" | "degraded";
    mode: string;
    data_dir: string;
    geoserv_url: string;
    geoserv_reachable: boolean;
    missing_models: string[];
    active_jobs: number;
    max_jobs: number;
}

export interface IModelMeta {
    model?: string;
    arch?: string;
    input_size?: number;
    codes?: string[];
    classes?: string[];
    footprint_class?: number;
    loss?: string;
    train_tiles?: number;
    valid_tiles?: number;
    valid_events?: string[];
    trained_on?: string;
    trained?: string;
    metrics?: { [key: string]: number };
}

export interface IModelInfo {
    role: "stage1" | "stage2";
    path: string;
    exists: boolean;
    size_mb: number | null;
    meta: IModelMeta;
}

export interface IZoneLayer {
    features: number;
    bytes: number;
    severity: { [key: string]: number };
}

export interface IZoneInventory {
    zone_id: string;
    layers: { [key: string]: IZoneLayer };
}

export interface IImageryRole {
    tiles: number;
    by_zoom: { [key: string]: number };
}

export interface IImageryInventory {
    zone_id: string;
    roles: { [key: string]: IImageryRole };
}

export interface IMinAreaPoint {
    min_area: number;
    mean_iou: number;
    polygons_per_tile: number;
}

export interface IEvaluation {
    measured_on: string;
    scenes: string[];
    footprint_iou_mean: number;
    footprint_iou_by_scene: { [key: string]: number };
    buildings_classified: number;
    min_area_sweep: IMinAreaPoint[];
    selected_min_area: number;
    tile_alignment_drgb_mean: number;
    notes: string[];
}

export interface IDiagnostics {
    mode: string;
    min_area: number;
    max_upload_mb: number;
    data_dir: string;
    geoserv_url: string;
    models: IModelInfo[];
    zones: IZoneInventory[];
    imagery: IImageryInventory[];
    queue: { active: number; max: number };
    evaluation: IEvaluation;
}

// Chart primitives live here (not inside the .vue files) so views can import them without
// pulling in a component module.
export interface IChartSegment {
    label: string;
    value: number;
    color: string;
}

export interface IChartBar {
    label: string;
    value: number;
    color?: string;
}

/** One ranked row of the per-zone damage list. `severe + moderate` is the affected total. */
export interface IZoneBarRow {
    label: string;
    total: number;
    severe: number;
    moderate: number;
}

export interface IChartPoint {
    label: string;
    value: number;
}

export type JobStatus = "queued" | "running" | "succeeded" | "failed";

export interface IJob {
    job_id: string;
    zone_id: string;
    status: JobStatus;
    created_at: string;
    started_at: string | null;
    finished_at: string | null;
    duration_seconds: number | null;
    tiles: number;
    affected_structures: number;
    unaffected_structures: number;
    severe_structures: number;
    moderate_structures: number;
    artifacts: string[];
    error: string | null;
    warning: string | null;
}

// ---------------------------------------------------------------------------
// NETRA Super-Resolution, Multi-Spectral & Blockchain Types
// ---------------------------------------------------------------------------

export interface ISRPreset {
    id: string;
    name: string;
    title?: string;
    description: string;
    bbox: number[];
    default_model?: string;
    source?: string;
}

export interface ISRMetrics {
    psnr?: number | null;
    ssim?: number | null;
    sam?: number | null;
    ergas?: number | null;
    niqe?: number | null;
    brisque?: number | null;
}

export interface IBlockchainRecord {
    tile_id: string;
    sha256: string;
    tx_hash?: string;
    block_number?: number;
    status: "verified" | "simulated" | "pending" | "failed";
    explorer_url?: string;
    timestamp?: string;
    mode?: string;
}

export interface ISRResult {
    status: string;
    model?: string;
    scale_factor?: number;
    inference_time_ms: number;
    lr_preview: string;
    sr_preview: string;
    hr_preview?: string | null;
    has_reference?: boolean;
    reference_tier_label?: string;
    confidence_heatmap_preview?: string;
    confidence_heatmap?: string;
    cloud_mask_preview?: string;
    mean_confidence?: number;
    hallucination_pct?: number;
    cloud_coverage_pct?: number;
    cloud_warning?: string | null;
    metrics?: ISRMetrics;
    usp_metrics?: {
        avg_confidence?: number;
        sam_degrees?: number;
        mean_uncertainty?: number;
        cycle_consistency_mae?: number;
        cloud_coverage_pct?: number;
    };
    blockchain_record?: IBlockchainRecord;
    blockchain_provenance?: any;
    metadata?: any;
}

export interface ISpectralLegendItem {
    label: string;
    color: string;
    threshold: string;
}

export interface ISpectralCoverageStats {
    category: string;
    threshold: string;
    area_km2: number;
    area_pct: number;
    total_aoi_km2: number;
    unit: string;
}

export interface ISpectralResult {
    status: string;
    mode: string;
    title: string;
    subtitle: string;
    description: string;
    bands_used: string[];
    is_index: boolean;
    legend?: ISpectralLegendItem[] | Record<string, any>;
    legend_items?: ISpectralLegendItem[];
    gradient_css?: string | null;
    stats?: {
        min: number;
        max: number;
        mean: number;
        std: number;
    };
    coverage_stats?: ISpectralCoverageStats;
    lr_preview: string;
    sr_preview?: string | null;
}

export interface IInfrastructureResult {
    status: string;
    building_count?: number;
    road_count?: number;
    total_road_length_km?: number;
    total_road_area_km2?: number;
    total_built_area_km2?: number;
    infrastructure_summary?: {
        buildings_count?: number;
        road_segments_count?: number;
        roads_length_km?: number;
        total_built_area_km2?: number;
    };
    geojson?: any;
    overlay_preview?: string;
    infrastructure_overlay?: string;
}

