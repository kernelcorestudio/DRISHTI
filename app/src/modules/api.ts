/*
 * DISASTER RESPONSE APP
 * Copyright (c) 2021 SilentByte <https://silentbyte.com/>
 */

import {
    IDiagnostics,
    IDisasterZone,
    IHealth,
    IInfrastructureResult,
    IJob,
    ISRPreset,
    ISRResult,
    ISpectralResult,
} from "@/models";

// The inference API has no CORS middleware, so the browser always goes through the dev server
// proxy configured in vue.config.js ("/api" -> http://127.0.0.1:8099).
const API_BASE = "/api";
const DEFAULT_TIMEOUT_MS = 15000;

export class ApiRequestError extends Error {
    public constructor(message: string) {
        super(message);
        this.name = "ApiRequestError";
    }
}

async function requestJson<T>(
    path: string,
    init?: RequestInit,
    timeoutMs: number = DEFAULT_TIMEOUT_MS,
): Promise<T> {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);

    try {
        const response = await fetch(`${API_BASE}${path}`, {
            ...init,
            signal: controller.signal,
        });

        if(!response.ok) {
            const detail = (await response.text()).slice(0, 400);
            throw new ApiRequestError(`${response.status} ${response.statusText}${detail ? `: ${detail}` : ""}`);
        }

        return (await response.json()) as T;
    } catch(error) {
        if(error instanceof ApiRequestError) {
            throw error;
        }

        const message = error instanceof Error && error.name === "AbortError"
            ? `no response after ${Math.round(timeoutMs / 1000)}s`
            : String(error);

        throw new ApiRequestError(message);
    } finally {
        clearTimeout(timer);
    }
}

export function fetchHealth(): Promise<IHealth> {
    return requestJson<IHealth>("/health", undefined, 5000);
}

export function fetchDiagnostics(): Promise<IDiagnostics> {
    // This call walks the tile and GeoJSON directories, so it gets a longer timeout.
    return requestJson<IDiagnostics>("/diagnostics", undefined, 30000);
}

export function fetchJobs(limit = 20): Promise<IJob[]> {
    return requestJson<IJob[]>(`/jobs?limit=${limit}`, undefined, 5000);
}

export function fetchJob(jobId: string): Promise<IJob> {
    return requestJson<IJob>(`/jobs/${encodeURIComponent(jobId)}`, undefined, 5000);
}

export function submitInference(zoneId: string, before: File, after: File): Promise<IJob> {
    const body = new FormData();
    body.append("before_image", before);
    body.append("after_image", after);

    // Uploads carry whole tiles, so the request itself is allowed minutes; the inference
    // happens in the queue after it returns.
    return requestJson<IJob>(
        `/predict/disaster?zone_id=${encodeURIComponent(zoneId)}`,
        {method: "POST", body},
        300000,
    );
}

export function isTerminalJob(job: IJob): boolean {
    return job.status === "succeeded" || job.status === "failed";
}

export function statusColor(status: string): string {
    switch(status) {
        case "succeeded":
        case "ready":
            return "success";

        case "running":
            return "accent";

        case "queued":
            return "warning";

        case "failed":
        case "degraded":
            return "error";

        default:
            return "disabled";
    }
}

/** Turns ".../geo/<scene>/structures-affected" into "<scene>", the id the API uses for a zone. */
export function sceneIdFromLayerUrl(url: string | null): string | null {
    if(!url) {
        return null;
    }

    const match = /\/geo\/([^/]+)\//.exec(url);
    return match ? match[1] : null;
}

/**
 * Every zone can expose its layers in any order, so try the three known layers and take the
 * first scene id that resolves.
 */
export function zoneSceneId(zone: IDisasterZone): string | null {
    return sceneIdFromLayerUrl(zone.affectedStructuresUrl)
        || sceneIdFromLayerUrl(zone.heatmapUrl)
        || sceneIdFromLayerUrl(zone.amenitiesUrl);
}

export function zoneBySceneId(
    zones: IDisasterZone[],
    sceneId: string,
): IDisasterZone | undefined {
    return zones.find(zone => zoneSceneId(zone) === sceneId);
}

// ---------------------------------------------------------------------------
// NETRA Super-Resolution & Spectral API Methods
// ---------------------------------------------------------------------------

export async function fetchSRPresets(): Promise<ISRPreset[]> {
    const res = await requestJson<{ status: string; presets: ISRPreset[] }>("/sr/presets", undefined, 5000);
    return (res.presets || []).map(p => ({
        ...p,
        name: p.name || p.title || p.id,
    }));
}

export function fetchSRTile(presetId?: string, bbox?: number[]): Promise<any> {
    return requestJson<any>(
        "/sr/fetch-tile",
        {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                preset_id: presetId,
                aoi_id: presetId || "custom_aoi",
                bbox,
            }),
        },
        60000,
    );
}

export function runSuperResolution(params: {
    model_name?: string;
    scale_factor?: number;
    mc_samples?: number;
    apply_sharpen?: boolean;
    use_tiling?: boolean;
}): Promise<ISRResult> {
    const samples = params.mc_samples || 8;
    const sharpen = Boolean(params.apply_sharpen);
    return requestJson<ISRResult>(
        "/sr/superresolve",
        {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                model_name: params.model_name || "hat",
                scale_factor: params.scale_factor || 4,
                num_mc_samples: samples,
                mc_samples: samples,
                apply_realesrgan_sharpen: sharpen,
                apply_unsharp: sharpen,
                use_tiling: params.use_tiling !== false,
            }),
        },
        120000,
    );
}

export function detectInfrastructure(): Promise<IInfrastructureResult> {
    return requestJson<IInfrastructureResult>(
        "/sr/detect-infrastructure",
        {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({}),
        },
        60000,
    );
}

export function fetchSpectralVisualization(mode: string, applySharpen = false): Promise<ISpectralResult> {
    return requestJson<ISpectralResult>(
        "/sr/visualize",
        {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                mode: mode || "true_color",
                apply_realesrgan_sharpen: applySharpen,
            }),
        },
        30000,
    );
}

export function fetchBlockchainStatus(): Promise<any> {
    return requestJson<any>("/sr/blockchain/status", undefined, 5000);
}

export function registerTileOnChain(tileId?: string): Promise<any> {
    return requestJson<any>(
        "/sr/blockchain/register",
        {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ tile_id: tileId || null }),
        },
        15000,
    );
}

export function srDownloadUrl(itemType: "geotiff" | "sr" | "geojson" | "confidence" | "lr"): string {
    return `${API_BASE}/sr/download/${encodeURIComponent(itemType)}`;
}

