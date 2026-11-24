/*
 * DISASTER RESPONSE APP
 * Copyright (c) 2021 SilentByte <https://silentbyte.com/>
 */

import { IDisasterZone } from "@/models";

const GEOSERV_ZONES_URL = "http://127.0.0.1:8088/disasters/zones";

/**
 * GeoServ re-reads the data directory on every reload, so it is the live source. The static
 * JSON is only the fallback for when the Rust service is not running.
 */
export async function fetchDisasterZones(): Promise<IDisasterZone[]> {
    try {
        const response = await fetch(GEOSERV_ZONES_URL);
        if(response.ok) {
            return await response.json();
        }
    } catch(error) {
        console.warn("GeoServ zones unavailable, falling back to disaster-zones.json", error);
    }

    const base = process.env.BASE_URL || "/";
    const normalizedBase = base.endsWith("/") ? base : `${base}/`;
    const response = await fetch(`${normalizedBase}disaster-zones.json`);
    if(!response.ok) {
        throw new Error(`Failed to load disaster-zones.json: ${response.status} ${response.statusText}`);
    }
    return await response.json();
}
