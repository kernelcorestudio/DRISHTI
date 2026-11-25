<!--
    DISASTER RESPONSE APP
    Copyright (c) 2021 SilentByte <https://silentbyte.com/>
-->

<template>
    <div class="page">
        <div class="grid grid--kpi">
            <StatCard label="buildings in scope" :value="counts.total" :hint="scopeHint" />
            <StatCard label="severe damage" :value="counts.severe" tone="bad" :hint="percentLabel(counts.severe)" />
            <StatCard label="moderate damage" :value="counts.moderate" tone="warn" :hint="percentLabel(counts.moderate)" />
            <StatCard label="intact" :value="counts.intact" tone="good" :hint="percentLabel(counts.intact)" />
        </div>

        <div class="scope-bar">
            <span class="bar-label">count area</span>

            <v-btn-toggle v-model="scopeMode" mandatory dense class="scope-toggle">
                <v-btn small value="scene">whole scene</v-btn>
                <v-btn small value="view">map view</v-btn>
            </v-btn-toggle>
        </div>

        <div class="report-grid">
            <SectionCard class="map-card"
                         title="scene map"
                         :subtitle="mapSubtitle"
                         flush>
                <template v-slot:actions>
                    <v-btn-toggle v-model="imagery" mandatory dense class="scope-toggle">
                        <v-btn small value="before">before</v-btn>
                        <v-btn small value="after">after</v-btn>
                    </v-btn-toggle>
                </template>

                <div class="map-holder">
                    <div ref="map" class="report-map" />

                    <div class="map-legend">
                        <div v-for="entry in legend" :key="entry.label" class="legend-row">
                            <span class="legend-swatch" :style="{ backgroundColor: entry.color }" />
                            {{ entry.label }}
                        </div>
                    </div>
                </div>
            </SectionCard>

            <SectionCard title="damage split" :subtitle="scopeLabel">
                <div class="split">
                    <div v-for="row in splitRows" :key="row.key" class="split-row">
                        <div class="split-head">
                            <span class="split-key">{{ row.label }}</span>
                            <span class="split-value">
                                {{ row.value }}<span class="split-pct">{{ row.percent }}%</span>
                            </span>
                        </div>

                        <div class="split-track">
                            <div class="split-fill"
                                 :style="{ width: row.percent + '%', backgroundColor: row.color }" />
                        </div>
                    </div>
                </div>

                <div class="split-note">{{ splitNote }}</div>
            </SectionCard>
        </div>

        <SectionCard class="areas-card"
                     title="where the damage is"
                     :subtitle="areasSubtitle"
                     flush>
            <div class="areas-table">
                <table>
                    <thead>
                    <tr>
                        <th>area</th>
                        <th class="num">buildings</th>
                        <th class="num">severe</th>
                        <th class="num">moderate</th>
                        <th class="num">intact</th>
                        <th class="num">damaged</th>
                        <th class="share-col">share of area</th>
                    </tr>
                    </thead>

                    <tbody>
                    <tr v-for="row in areas"
                        :key="row.key"
                        :class="{'row--active': row.key === selectedArea}"
                        @click="focusArea(row)">
                        <td class="area-cell">
                            <span class="area-label">{{ row.label }}</span>
                            <span class="area-distance">{{ row.distance }}</span>
                        </td>
                        <td class="num strong">{{ row.total }}</td>
                        <td class="num severe">{{ row.severe }}</td>
                        <td class="num moderate">{{ row.moderate }}</td>
                        <td class="num intact">{{ row.intact }}</td>
                        <td class="num damaged">{{ row.damaged }}</td>
                        <td class="share-col">
                            <div class="share-cell">
                                <div class="share-track">
                                    <div class="share-fill"
                                         :style="{ width: row.percent + '%', backgroundColor: row.color }" />
                                </div>
                                <span class="share-value">{{ row.percent }}%</span>
                            </div>
                        </td>
                    </tr>

                    <tr v-if="!areas.length">
                        <td colspan="7" class="empty">{{ emptyMessage }}</td>
                    </tr>
                    </tbody>
                </table>
            </div>
        </SectionCard>
    </div>
</template>

<!--suppress JSMethodCanBeStatic, JSUnusedGlobalSymbols -->
<script lang="ts">

import * as L from "leaflet";

import {
    Component,
    Ref,
    Vue,
    Watch,
} from "vue-property-decorator";

import { getModule } from "vuex-module-decorators";
import { AppModule } from "@/store/app";

import SectionCard from "@/ui/components/SectionCard.vue";
import StatCard from "@/ui/components/StatCard.vue";

import { sceneIdFromLayerUrl } from "@/modules/api";
import { fetchDisasterZones } from "@/modules/zones";

import {
    IDisasterZone,
    ILatLng,
    IZoneInventory,
} from "@/models";
import {
    SEVERITY_COLORS,
    shortScene,
} from "@/modules/format";

type ScopeMode = "scene" | "view";
type ImageryMode = "before" | "after";

interface IStructurePoint {
    lat: number;
    lng: number;
    severity: string;
}

interface ICounts {
    total: number;
    severe: number;
    moderate: number;
    intact: number;
}

interface IAreaRow extends ICounts {
    key: string;
    label: string;
    distance: string;
    damaged: number;
    percent: number;
    color: string;
    bounds: L.LatLngBoundsLiteral;
}

interface IBoundBox {
    minLat: number;
    maxLat: number;
    minLng: number;
    maxLng: number;
}

const STRUCTURE_PANE = "structures";
const BASEMAP_PANE = "basemap";

// GeoServ filters by viewport, so "everything in this scene" is asked for with the whole world
// as the window. 10 000 is the service's own ceiling.
const WORLD_BOUNDS: [ILatLng, ILatLng] = [
    {lat: 90, lng: 180},
    {lat: -90, lng: -180},
];
const STRUCTURE_LIMIT = 10000;

const SEVERITY_FILL: Record<string, string> = {
    severe: SEVERITY_COLORS.severe,
    moderate: SEVERITY_COLORS.moderate,
    none: SEVERITY_COLORS.intact,
};

const SEVERITY_LABELS: Record<string, string> = {
    severe: "severe",
    moderate: "moderate",
    none: "intact",
};

const COMPASS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"];

// The scene is cut into a 3x3 grid: coarse enough that every row aggregates a real cluster
// instead of a handful of neighbouring buildings.
const GRID_CELLS = 3;

const OSM_URL = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";
const OSM_ATTRIBUTION = "&copy; <a href=\"https://www.openstreetmap.org/copyright\">OpenStreetMap</a> contributors";

/** Both layers store a Polygon ring as [lng, lat] pairs; MultiPolygon nests one level deeper. */
function firstRing(feature: any): number[][] {
    const geometry = feature?.geometry;
    if(!geometry) {
        return [];
    }

    if(geometry.type === "Polygon") {
        return geometry.coordinates?.[0] || [];
    }

    if(geometry.type === "MultiPolygon") {
        return geometry.coordinates?.[0]?.[0] || [];
    }

    return [];
}

function ringBox(ring: number[][]): IBoundBox {
    const box: IBoundBox = {minLat: 90, maxLat: -90, minLng: 180, maxLng: -180};

    for(const point of ring) {
        const lng = point[0];
        const lat = point[1];

        if(lat < box.minLat) {
            box.minLat = lat;
        }

        if(lat > box.maxLat) {
            box.maxLat = lat;
        }

        if(lng < box.minLng) {
            box.minLng = lng;
        }

        if(lng > box.maxLng) {
            box.maxLng = lng;
        }
    }

    return box;
}

/** Direction and distance of a cluster relative to the middle of the scene. */
function describeArea(centre: ILatLng, origin: ILatLng): { label: string; distance: string } {
    const north = centre.lat - origin.lat;
    const east = (centre.lng - origin.lng) * Math.cos(origin.lat * Math.PI / 180);
    const metres = Math.sqrt(north * north + east * east) * 111320;

    if(metres < 40) {
        return {label: "centre", distance: "scene middle"};
    }

    const angle = (Math.atan2(east, north) * 180 / Math.PI + 360) % 360;
    const label = COMPASS[Math.round(angle / 45) % 8];
    const distance = metres < 1000
        ? `${Math.round(metres / 10) * 10} m`
        : `${(metres / 1000).toFixed(1)} km`;

    return {label, distance};
}

function structureTooltip(feature: any): string {
    const properties = feature?.properties || {};
    const lines = [`<strong>${SEVERITY_LABELS[properties.severity] || "building"}</strong>`];

    if(typeof properties.damage_probability === "number") {
        lines.push(`Damage probability ${(properties.damage_probability * 100).toFixed(0)}%`);
    }

    return lines.join("<br>");
}

async function fetchGeoJSON(endpointUrl: string, limit: number): Promise<any[]> {
    const url = new URL(endpointUrl);

    url.searchParams.append("ne_lat", WORLD_BOUNDS[0].lat.toString());
    url.searchParams.append("ne_lng", WORLD_BOUNDS[0].lng.toString());
    url.searchParams.append("sw_lat", WORLD_BOUNDS[1].lat.toString());
    url.searchParams.append("sw_lng", WORLD_BOUNDS[1].lng.toString());
    url.searchParams.append("limit", limit.toString());

    const response = await fetch(url.toString());
    if(!response.ok) {
        throw new Error(`GeoServ answered ${response.status}`);
    }

    return await response.json();
}

@Component({
    components: {
        SectionCard,
        StatCard,
    },
})
export default class ReportView extends Vue {
    private readonly app = getModule(AppModule);

    @Ref("map") private mapRef!: HTMLElement;
    private map: L.Map | null = null;

    private basemap: L.TileLayer | null = null;
    private beforeLayer: L.TileLayer | null = null;
    private afterLayer: L.TileLayer | null = null;
    private structureLayer: L.GeoJSON | null = null;

    private scopeMode: ScopeMode = "scene";
    private imagery: ImageryMode = "after";

    // One small record per building; keeps the reactive payload light even for big scenes.
    private points: IStructurePoint[] = [];
    private viewBounds = {
        sw: {lat: -90, lng: -180},
        ne: {lat: 90, lng: 180},
    };

    private selectedArea = "";
    private loading = false;
    private loadError = "";

    // Raw GeoJSON never needs to be reactive (Leaflet owns it), so it is cached outside Vue's
    // observation with a Map, which Vue 2 does not walk.
    private readonly rawCache = new Map<string, { affected: any[]; unaffected: any[] }>();

    private get zone(): IDisasterZone | null {
        return this.app.selectedDisasterZone;
    }

    private get sceneId(): string | null {
        const zone = this.zone;
        if(!zone) {
            return null;
        }

        return sceneIdFromLayerUrl(zone.affectedStructuresUrl)
            || sceneIdFromLayerUrl(zone.heatmapUrl)
            || sceneIdFromLayerUrl(zone.amenitiesUrl);
    }

    private get inventory(): IZoneInventory | null {
        const scene = this.sceneId;
        if(!scene) {
            return null;
        }

        return (this.app.diagnostics?.zones || []).find(zone => zone.zone_id === scene) || null;
    }

    /** Totals as the API's own artefact sweep sees them, so they always match the Zones page. */
    private get sceneCounts(): ICounts {
        const affected = this.inventory?.layers["structures-affected"];
        const intact = this.inventory?.layers["structures-unaffected"]?.features || 0;

        return {
            severe: affected?.severity?.severe || 0,
            moderate: affected?.severity?.moderate || 0,
            intact,
            total: (affected?.features || 0) + intact,
        };
    }

    private get visiblePoints(): IStructurePoint[] {
        const {sw, ne} = this.viewBounds;

        return this.points.filter(point => {
            return point.lat >= sw.lat && point.lat <= ne.lat
                && point.lng >= sw.lng && point.lng <= ne.lng;
        });
    }

    private get counts(): ICounts {
        if(this.scopeMode === "view" && this.points.length) {
            return this.summarize(this.visiblePoints);
        }

        return this.sceneCounts;
    }

    private get scopeLabel(): string {
        return this.scopeMode === "view" ? "current map view" : "whole scene";
    }

    private get scopeHint(): string {
        return this.scopeMode === "view" ? "inside the current map view" : "in the indexed scene";
    }

    private get mapSubtitle(): string {
        const scene = this.sceneId;
        return scene ? `${shortScene(scene)} · after imagery and assessed buildings` : "no scene selected";
    }

    private get legend() {
        return [
            {label: "severe", color: SEVERITY_COLORS.severe},
            {label: "moderate", color: SEVERITY_COLORS.moderate},
            {label: "intact", color: SEVERITY_COLORS.intact},
        ];
    }

    private get splitRows() {
        const counts = this.counts;
        const total = Math.max(1, counts.total);
        const share = (value: number) => Math.round((value / total) * 100);

        return [
            {key: "severe", label: "severe damage", value: counts.severe, color: SEVERITY_COLORS.severe, percent: share(counts.severe)},
            {key: "moderate", label: "moderate damage", value: counts.moderate, color: SEVERITY_COLORS.moderate, percent: share(counts.moderate)},
            {key: "intact", label: "no visible damage", value: counts.intact, color: SEVERITY_COLORS.intact, percent: share(counts.intact)},
        ];
    }

    private get splitNote(): string {
        const counts = this.counts;
        const damaged = counts.severe + counts.moderate;
        const percent = counts.total ? Math.round((damaged / counts.total) * 100) : 0;

        return `${damaged} of ${counts.total} buildings show damage (${percent}%)`;
    }

    private get sceneBox(): IBoundBox | null {
        if(!this.points.length) {
            return null;
        }

        const box: IBoundBox = {minLat: 90, maxLat: -90, minLng: 180, maxLng: -180};

        for(const point of this.points) {
            box.minLat = Math.min(box.minLat, point.lat);
            box.maxLat = Math.max(box.maxLat, point.lat);
            box.minLng = Math.min(box.minLng, point.lng);
            box.maxLng = Math.max(box.maxLng, point.lng);
        }

        return box;
    }

    /**
     * Buildings are bucketed into a coarse grid; each bucket becomes one row of the table.
     * Labels use compass direction instead of tile ids, because the demo artefacts all carry
     * the same `tile` property, which would collapse into a single meaningless row.
     */
    private get areas(): IAreaRow[] {
        const source = this.scopeMode === "view" ? this.visiblePoints : this.points;
        const box = this.sceneBox;

        if(!source.length || !box) {
            return [];
        }

        const span = Math.max(box.maxLat - box.minLat, box.maxLng - box.minLng);
        const cell = Math.max(0.0002, span / GRID_CELLS);

        const origin = {
            lat: (box.minLat + box.maxLat) / 2,
            lng: (box.minLng + box.maxLng) / 2,
        };

        const buckets = new Map<string, IStructurePoint[]>();

        for(const point of source) {
            // Clamped so a point sitting exactly on the far edge cannot open a fourth cell.
            const row = Math.min(GRID_CELLS - 1, Math.floor((point.lat - box.minLat) / cell));
            const column = Math.min(GRID_CELLS - 1, Math.floor((point.lng - box.minLng) / cell));
            const key = `${row}:${column}`;

            const bucket = buckets.get(key);
            if(bucket) {
                bucket.push(point);
            } else {
                buckets.set(key, [point]);
            }
        }

        const rows: IAreaRow[] = [];

        buckets.forEach((bucketPoints, key) => {
            const counts = this.summarize(bucketPoints);
            let minLat = 90, maxLat = -90, minLng = 180, maxLng = -180;

            for(const point of bucketPoints) {
                minLat = Math.min(minLat, point.lat);
                maxLat = Math.max(maxLat, point.lat);
                minLng = Math.min(minLng, point.lng);
                maxLng = Math.max(maxLng, point.lng);
            }

            const where = describeArea({
                lat: (minLat + maxLat) / 2,
                lng: (minLng + maxLng) / 2,
            }, origin);

            const damaged = counts.severe + counts.moderate;

            rows.push({
                ...counts,
                key,
                label: where.label,
                distance: where.distance,
                damaged,
                percent: counts.total ? Math.round((damaged / counts.total) * 100) : 0,
                color: counts.severe >= counts.moderate ? SEVERITY_COLORS.severe : SEVERITY_COLORS.moderate,
                bounds: [[minLat, minLng], [maxLat, maxLng]],
            });
        });

        return rows.sort((a, b) => {
            return (b.severe - a.severe) || (b.damaged - a.damaged) || (b.total - a.total);
        });
    }

    private get areasSubtitle(): string {
        const count = this.areas.length;

        if(!count) {
            return "no assessed buildings in the current selection";
        }

        return `${count} area${count === 1 ? "" : "s"} · click a row to zoom the map`;
    }

    private get emptyMessage(): string {
        if(this.loading) {
            return "loading buildings from GeoServ";
        }

        if(this.loadError) {
            return this.loadError;
        }

        return "no assessed buildings for this scene";
    }

    private summarize(points: IStructurePoint[]): ICounts {
        const counts: ICounts = {total: points.length, severe: 0, moderate: 0, intact: 0};

        for(const point of points) {
            if(point.severity === "severe") {
                counts.severe += 1;
            } else if(point.severity === "moderate") {
                counts.moderate += 1;
            } else {
                counts.intact += 1;
            }
        }

        return counts;
    }

    private percentLabel(value: number): string {
        const total = this.counts.total;
        return total ? `${Math.round((value / total) * 100)}% of ${this.scopeMode === "view" ? "view" : "scene"}` : "no buildings";
    }

    private applyImagery() {
        this.beforeLayer?.remove();
        this.afterLayer?.remove();

        if(this.map) {
            if(this.imagery === "before") {
                this.beforeLayer?.addTo(this.map);
            } else {
                this.afterLayer?.addTo(this.map);
            }
        }
    }

    private async loadScene(zone: IDisasterZone) {
        const scene = this.sceneId;
        if(!scene || !this.map) {
            return;
        }

        this.loading = true;
        this.loadError = "";
        this.selectedArea = "";

        try {
            let payload = this.rawCache.get(scene);

            if(!payload) {
                const affected = zone.affectedStructuresUrl
                    ? await fetchGeoJSON(zone.affectedStructuresUrl, STRUCTURE_LIMIT).catch(() => [])
                    : [];

                const unaffected = zone.unaffectedStructuresUrl
                    ? await fetchGeoJSON(zone.unaffectedStructuresUrl, STRUCTURE_LIMIT).catch(() => [])
                    : [];

                payload = {affected, unaffected};
                this.rawCache.set(scene, payload);
            }

            if(!payload.affected.length && !payload.unaffected.length) {
                this.loadError = "GeoServ did not return any buildings - the per-area list needs the Rust index running";
            }

            this.points = [...payload.affected, ...payload.unaffected]
                .map(feature => this.toPoint(feature))
                .filter((point): point is IStructurePoint => point !== null);

            this.drawStructures(payload.affected, payload.unaffected);

            const box = this.sceneBox;
            if(box) {
                // The card is laid out asynchronously, so the canvas is re-measured before fitting;
                // otherwise the same scene lands on a different zoom depending on timing.
                this.map.invalidateSize();
                this.map.fitBounds([[box.minLat, box.minLng], [box.maxLat, box.maxLng]], {padding: [18, 18]});
            } else {
                this.map.setView(zone.center, zone.center.zoom);
            }

            this.updateViewBounds();
        } finally {
            this.loading = false;
        }
    }

    private toPoint(feature: any): IStructurePoint | null {
        const ring = firstRing(feature);
        if(!ring.length) {
            return null;
        }

        const box = ringBox(ring);

        return {
            lat: (box.minLat + box.maxLat) / 2,
            lng: (box.minLng + box.maxLng) / 2,
            severity: String(feature?.properties?.severity || "none"),
        };
    }

    private drawStructures(affected: any[], unaffected: any[]) {
        this.structureLayer?.remove();
        this.structureLayer = null;

        if(!this.map) {
            return;
        }

        this.structureLayer = L.geoJSON([...affected, ...unaffected] as any, {
            pane: STRUCTURE_PANE,
            style: (feature: any) => ({
                color: SEVERITY_FILL[feature?.properties?.severity] || SEVERITY_COLORS.severe,
                weight: 1,
                fillOpacity: 0.25,
            }),
            onEachFeature(feature: any, layer: L.Layer) {
                layer.bindTooltip(structureTooltip(feature), {direction: "top"});
            },
        }).addTo(this.map);
    }

    private updateViewBounds() {
        if(!this.map) {
            return;
        }

        const bounds = this.map.getBounds();

        this.viewBounds = {
            sw: {lat: bounds.getSouth(), lng: bounds.getWest()},
            ne: {lat: bounds.getNorth(), lng: bounds.getEast()},
        };
    }

    private focusArea(row: IAreaRow) {
        this.selectedArea = row.key;
        this.map?.fitBounds(row.bounds, {padding: [40, 40]});
    }

    @Watch("app.selectedDisasterZone", {immediate: true})
    private async onDisasterZoneSelected(zone: IDisasterZone | null) {
        await this.$nextTick();

        if(!this.map) {
            return;
        }

        this.beforeLayer?.remove();
        this.afterLayer?.remove();
        this.beforeLayer = null;
        this.afterLayer = null;

        this.points = [];
        this.selectedArea = "";
        this.loadError = "";

        if(!zone) {
            return;
        }

        if(zone.beforeLayer) {
            this.beforeLayer = L.tileLayer(zone.beforeLayer.urlTemplate, {
                attribution: zone.beforeLayer.attributionHtml,
                maxZoom: 19,
                maxNativeZoom: 19,
            });
        }

        if(zone.afterLayer) {
            this.afterLayer = L.tileLayer(zone.afterLayer.urlTemplate, {
                attribution: zone.afterLayer.attributionHtml,
                maxZoom: 19,
                maxNativeZoom: 19,
            });
        }

        this.applyImagery();
        await this.loadScene(zone);
    }

    @Watch("imagery")
    private onImageryChanged() {
        this.applyImagery();
    }

    @Watch("scopeMode")
    private onScopeChanged() {
        this.selectedArea = "";
    }

    async mounted(): Promise<void> {
        this.map = L.map(this.mapRef, {
            minZoom: 2,
            maxZoom: 18,
            zoomControl: true,
            attributionControl: true,
        }).setView([20, 0], 3);

        // The card is laid out after mount, so Leaflet has to measure again before tiles settle.
        await this.$nextTick();
        this.map.invalidateSize();

        const structurePane = this.map.createPane(STRUCTURE_PANE);
        structurePane.style.zIndex = "450";

        const basemapPane = this.map.createPane(BASEMAP_PANE);
        basemapPane.style.zIndex = "150";

        this.basemap = L.tileLayer(OSM_URL, {
            pane: BASEMAP_PANE,
            attribution: OSM_ATTRIBUTION,
            maxZoom: 19,
            maxNativeZoom: 19,
        }).addTo(this.map);

        this.map.on("moveend", () => this.updateViewBounds());
        this.map.on("zoomend", () => this.updateViewBounds());

        if(!this.app.disasterZones.length) {
            this.app.setDisasterZones(await fetchDisasterZones());
            this.app.setDefaultDisasterZone();
        }
    }

    beforeDestroy(): void {
        this.map?.remove();
        this.map = null;
    }
}

</script>

<style lang="scss" scoped>

.scope-bar {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 10px;
    margin-top: 14px;
}

.bar-label {
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--rahat-text-faint);
}

.scope-toggle {
    border: 1px solid var(--rahat-border);
    border-radius: 4px;
    background: transparent;
}

.report-grid {
    display: grid;
    grid-template-columns: minmax(0, 1.55fr) minmax(300px, 1fr);
    gap: 16px;
    margin-top: 16px;
}

@media (max-width: 1100px) {
    .report-grid {
        grid-template-columns: 1fr;
    }
}

.map-holder {
    position: relative;
}

.report-map {
    width: 100%;
    height: 420px;
    background: var(--rahat-map-bg);
}

/*
 * The legend floats over the map in both themes, so it is treated like the design system's
 * tooltips: an ink bubble with pale rose lettering. Following the theme's text colour instead
 * put dark prose on a dark panel in light mode.
 */
.map-legend {
    position: absolute;
    left: 12px;
    bottom: 26px;
    z-index: 500;
    padding: 8px 11px;
    background: rgba(26, 5, 7, 0.88);
    border: 1px solid rgba(251, 239, 240, 0.16);
    border-radius: 8px;
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
}

.legend-row {
    display: flex;
    align-items: center;
    gap: 7px;
    font-size: 11px;
    color: var(--crimson-pale);
    white-space: nowrap;
}

.legend-row + .legend-row {
    margin-top: 5px;
}

.legend-swatch {
    width: 9px;
    height: 9px;
    border-radius: 2px;
}

.split {
    display: flex;
    flex-direction: column;
    gap: 16px;
}

.split-head {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 12px;
}

.split-key {
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--rahat-text-faint);
}

.split-value {
    font-size: 18px;
    font-weight: 600;
    font-variant-numeric: tabular-nums;
    color: var(--rahat-text);
}

.split-pct {
    margin-left: 8px;
    font-size: 11px;
    font-weight: 500;
    color: var(--rahat-text-faint);
}

.split-track {
    margin-top: 7px;
    height: 6px;
    border-radius: 999px;
    background: var(--rahat-track);
    overflow: hidden;
}

.split-fill {
    height: 100%;
    border-radius: 999px;
    transition: width 240ms ease;
}

.split-note {
    margin-top: 18px;
    padding-top: 12px;
    border-top: 1px solid var(--rahat-border);
    font-size: 11px;
    color: var(--rahat-text-faint);
}

.areas-card {
    margin-top: 16px;
    margin-bottom: 10px;
}

.areas-table {
    overflow-x: auto;
}

table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
}

th {
    text-align: left;
    padding: 9px 12px;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--rahat-text-faint);
    border-bottom: 1px solid var(--rahat-border);
    white-space: nowrap;
}

th.num,
td.num {
    text-align: right;
}

td {
    padding: 9px 12px;
    border-bottom: 1px solid var(--rahat-border);
    color: var(--rahat-text-dim);
    white-space: nowrap;
}

tbody tr {
    cursor: pointer;
    transition: background 120ms ease;
}

tbody tr:hover {
    background: var(--rahat-accent-soft);
}

.row--active {
    background: var(--rahat-accent-soft);
}

.row--active td {
    color: var(--rahat-text);
}

.area-cell {
    display: flex;
    align-items: baseline;
    gap: 8px;
}

.area-label {
    font-weight: 600;
    color: var(--rahat-text);
}

.area-distance {
    font-size: 11px;
    color: var(--rahat-text-faint);
}

.strong {
    color: var(--rahat-text);
    font-weight: 600;
}

.severe {
    color: var(--rahat-danger);
}

.moderate {
    color: var(--rahat-warn);
}

.intact {
    color: var(--rahat-ok);
}

.damaged {
    font-weight: 600;
    color: var(--rahat-text);
}

.share-col {
    width: 200px;
}

.share-cell {
    display: flex;
    align-items: center;
    gap: 8px;
}

.share-track {
    flex: 1 1 auto;
    height: 6px;
    border-radius: 999px;
    background: var(--rahat-track);
    overflow: hidden;
}

.share-fill {
    height: 100%;
    border-radius: 999px;
}

.share-value {
    flex: 0 0 36px;
    text-align: right;
    font-variant-numeric: tabular-nums;
    color: var(--rahat-text-faint);
}

.empty {
    padding: 18px 12px;
    text-align: center;
    color: var(--rahat-text-faint);
}

</style>
