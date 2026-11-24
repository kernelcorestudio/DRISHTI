<!--
    DISASTER RESPONSE APP
    Copyright (c) 2021 SilentByte <https://silentbyte.com/>
-->

<template>
    <div class="map-page">
        <div ref="map" class="map" />

        <div class="map-info">
            <div class="info-name">{{ zoneName }}</div>
            <div class="info-row">
                <span class="info-key">scene</span>
                <span class="info-value mono">{{ selectedSceneId || "-" }}</span>
            </div>
            <div class="info-row">
                <span class="info-key">layer</span>
                <span class="info-value">{{ visibleLayer }}</span>
            </div>
            <div class="info-row">
                <span class="info-key">zoom</span>
                <span class="info-value">{{ zoomLevel }}z</span>
            </div>
            <div class="info-chips">
                <span class="info-chip info-chip--affected">{{ zoneStats.affected }} affected</span>
                <span class="info-chip info-chip--severe">{{ zoneStats.severe }} severe</span>
                <span class="info-chip info-chip--intact">{{ zoneStats.intact }} intact</span>
            </div>
        </div>

        <v-card v-if="showStructures" outlined class="map-legend">
            <v-card-text class="pa-3">
                <div class="map-legend-title">
                    damage assessment
                </div>
                <div v-for="entry in severityLegend"
                     :key="entry.severity"
                     class="map-legend-row">
                    <span class="map-legend-swatch" :style="{ backgroundColor: entry.color }" />
                    {{ entry.label }}
                </div>
            </v-card-text>
        </v-card>

        <div class="map-options">
            <v-badge left bordered overlap
                     :color="visibleLayer === 'none' ? 'disabled' : visibleLayer === 'before' ? 'success' : 'error'"
                     :content="visibleLayer">
                <v-btn fab small elevation="0"
                       class="map-fab"
                       :color="visibleLayer === 'none' ? 'disabled' : visibleLayer === 'before' ? 'success' : 'error'"
                       :class="{'map-option-inactive': visibleLayer === 'none'}"
                       @click="onToggleLayers">
                    <v-icon small>{{ visibleLayer === "after" ? "mdi-flash-alert" : "mdi-flash" }}</v-icon>
                </v-btn>
            </v-badge>

            <v-btn fab small elevation="0"
                   class="map-fab"
                   :color="showHeatmap ? 'accent' : 'disabled'"
                   :class="{'map-option-inactive': !showHeatmap}"
                   @click="onToggleHeatmap">
                <v-icon small>mdi-dots-hexagon</v-icon>
            </v-btn>

            <v-btn fab small elevation="0"
                   class="map-fab"
                   :color="showAmenities ? 'accent' : 'disabled'"
                   :class="{'map-option-inactive': !showAmenities}"
                   @click="onToggleAmenities">
                <v-icon small>mdi-hospital-building</v-icon>
            </v-btn>

            <v-btn fab small elevation="0"
                   class="map-fab"
                   :color="showStructures ? 'accent' : 'disabled'"
                   :class="{'map-option-inactive': !showStructures}"
                   @click="onToggleDamagePolygons">
                <v-icon small>mdi-vector-polygon</v-icon>
            </v-btn>
        </div>

        <v-overlay :value="pending">
            <v-progress-circular indeterminate size="60" color="primary" />
        </v-overlay>
    </div>
</template>

<!--suppress JSMethodCanBeStatic, JSUnusedGlobalSymbols -->
<script lang="ts">

import * as L from "leaflet";
import "leaflet.heat";

import {
    Component,
    Ref,
    Vue,
    Watch,
} from "vue-property-decorator";

import { getModule } from "vuex-module-decorators";
import { AppModule } from "@/store/app";

import {
    NavigationGuardNext,
    Route,
} from "vue-router";

import * as outgoing from "@/router/outgoing";

import { sceneIdFromLayerUrl } from "@/modules/api";
import { fetchDisasterZones } from "@/modules/zones";
import { SEVERITY_COLORS as THEME_SEVERITY_COLORS } from "@/modules/format";

import {
    IDisasterZone,
    ILatLng,
} from "@/models";

interface IViewOptions {
    center: ILatLng;
    zoom: number;
    fly?: boolean;
}

type VisibleLayer = "none" | "before" | "after";

function capitalizeString(text: string) {
    return text.charAt(0).toUpperCase() + text.slice(1);
}

function extractMapViewOptions(text: string): IViewOptions | null {
    const matches = /@(-?\d+(\.\d+)?),(-?\d+(\.\d+)?),(\d+(\.\d+)?)z/.exec(text);
    if(!matches) {
        return null;
    }

    return {
        center: {
            lat: parseFloat(matches[1]),
            lng: parseFloat(matches[3]),
        },
        zoom: parseFloat(matches[5]),
    };
}

async function fetchGeoJSON(endpointUrl: string, bounds: [ILatLng, ILatLng], limit: number) {
    const url = new URL(endpointUrl);

    url.searchParams.append("ne_lat", bounds[0].lat.toString());
    url.searchParams.append("ne_lng", bounds[0].lng.toString());
    url.searchParams.append("sw_lat", bounds[1].lat.toString());
    url.searchParams.append("sw_lng", bounds[1].lng.toString());
    url.searchParams.append("limit", limit.toString());

    const response = await fetch(url.toString());
    if(!response.ok) {
        return [];
    }
    return await response.json();
}

async function fetchHeatmap(endpointUrl: string) {
    const response = await fetch(endpointUrl);
    if(!response.ok) {
        return [];
    }
    return await response.json();
}

const AMENITY_LIMIT = 4000;
const AMENITY_ZOOM_LEVEL = 14;

const SUPPORTED_AMENITIES = [
    "bank",
    "bus_station",
    "childcare",
    "cinema",
    "clinic",
    "college",
    "community_centre",
    "courthouse",
    "dentist",
    "doctors",
    "ferry_terminal",
    "fire_station",
    "fuel",
    "hospital",
    "kindergarten",
    "library",
    "nursing_home",
    "pharmacy",
    "place_of_worship",
    "police",
    "post_office",
    "prep_school",
    "prison",
    "public_building",
    "school",
    "shelter",
    "townhall",
    "train_station",
    "university",
];

const STRUCTURE_LIMIT = 6000;
const STRUCTURE_ZOOM_LEVEL = 17;

// Structure polygons live in their own pane above the heat canvas (overlayPane, z 400)
// but below markers (z 600), so the glow never washes them out and amenity icons stay
// on top. Relying on overlayPane alone would make the order depend on when each layer
// was last re-added.
const STRUCTURE_PANE = "structures";

// The basemap gets its own pane so it can be darkened with a CSS filter without touching the
// before/after orthophoto, which is also a tile layer and sits in the default tile pane.
const BASEMAP_PANE = "basemap";

// Structure polygons are coloured by the severity the inference pipeline reports
// (derived from the stage 2 damage probability), not by a flat damaged/undamaged split.
// The values come from the shared palette so the map and the charts cannot drift apart. They
// have to be concrete hex: Leaflet writes them straight onto SVG presentation attributes, where
// a CSS custom property would not resolve.
const SEVERITY_COLORS: Record<string, string> = {
    get severe() { return THEME_SEVERITY_COLORS.severe; },
    get moderate() { return THEME_SEVERITY_COLORS.moderate; },
    get none() { return THEME_SEVERITY_COLORS.intact; },
};

const SEVERITY_LABELS: Record<string, string> = {
    severe: "Severe damage",
    moderate: "Moderate damage",
    none: "No visible damage",
};

const OSM_URL = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";
const OSM_ATTRIBUTION = "&copy; <a href=\"https://www.openstreetmap.org/copyright\">OpenStreetMap</a> contributors";

function structureColor(feature: any, fallback: string | undefined): string {
    const severity = feature?.properties?.severity;

    return (severity && SEVERITY_COLORS[severity]) || fallback || SEVERITY_COLORS.severe;
}

function structureTooltip(feature: any): string {
    const properties = feature?.properties || {};

    const heading = SEVERITY_LABELS[properties.severity]
        || capitalizeString(String(properties.class || "building"));

    const lines = [`<strong>${heading}</strong>`];

    if(typeof properties.damage_probability === "number") {
        lines.push(`Damage probability ${(properties.damage_probability * 100).toFixed(0)}%`);
    }

    if(typeof properties.confidence === "number") {
        lines.push(`Model confidence ${(properties.confidence * 100).toFixed(0)}%`);
    }

    return lines.join("<br>");
}

@Component
export default class MapView extends Vue {
    private readonly app = getModule(AppModule);
    private pending = true;

    @Ref("map") private mapRef!: HTMLElement;
    private map!: L.Map;

    private basemap: L.TileLayer | null = null;

    private visibleLayer: VisibleLayer = "none";

    private showHeatmap = true;
    private showAmenities = true;
    private showStructures = false;

    private zoomLevel = 3;

    private amenityCache: L.GeoJSON | null = null;
    private affectedStructureCache: L.GeoJSON | null = null;
    private unaffectedStructureCache: L.GeoJSON | null = null;

    private beforeLayer: L.TileLayer | null = null;
    private afterLayer: L.TileLayer | null = null;
    private heatmapLayer: L.TileLayer | null = null;

    private get selectedSceneId(): string | null {
        const zone = this.app.selectedDisasterZone;
        if(!zone) {
            return null;
        }

        return sceneIdFromLayerUrl(zone.affectedStructuresUrl)
            || sceneIdFromLayerUrl(zone.heatmapUrl)
            || sceneIdFromLayerUrl(zone.amenitiesUrl);
    }

    private get zoneName(): string {
        return this.app.selectedDisasterZone?.name || "no zone selected";
    }

    private get zoneStats() {
        const sceneId = this.selectedSceneId;
        const inventory = (this.app.diagnostics?.zones || [])
            .find(zone => zone.zone_id === sceneId);

        const affected = inventory?.layers["structures-affected"];

        return {
            affected: affected?.features || 0,
            severe: affected?.severity?.severe || 0,
            intact: inventory?.layers["structures-unaffected"]?.features || 0,
        };
    }

    private get severityLegend() {
        return ["severe", "moderate", "none"].map((severity) => ({
            severity,
            label: SEVERITY_LABELS[severity],
            color: SEVERITY_COLORS[severity],
        }));
    }

    private addBasemap() {
        // Plain OSM tiles: no API key needed and they have data at every zoom level. The dark
        // look comes from the CSS filter on .leaflet-basemap-pane further down.
        this.basemap = L.tileLayer(OSM_URL, {
            pane: BASEMAP_PANE,
            attribution: OSM_ATTRIBUTION,
            maxZoom: 19,
            maxNativeZoom: 19,
        }).addTo(this.map);
    }

    private updateRoute() {
        const view = this.getView();
        const latitude = view.center.lat.toFixed(7);
        const longitude = view.center.lng.toFixed(7);
        const zoom = view.zoom.toFixed(0);

        const options = `@${latitude},${longitude},${zoom}z`;
        if(this.$route.params.options !== options) {
            this.$router.replace({
                name: this.$route.name!,
                params: {
                    options,
                },
            }).catch(() => undefined);
        }
    }

    private navigateToRouteView() {
        if(this.$route.params.options) {
            const view = extractMapViewOptions(this.$route.params.options);
            if(view) {
                this.setView(view);
            }
        }
    }

    private async updateAmenities() {
        if(this.getView().zoom < AMENITY_ZOOM_LEVEL) {
            this.amenityCache?.remove();
            return;
        }

        if(!this.showAmenities) {
            this.amenityCache?.remove();
            return;
        }

        const amenitiesUrl = this.app.selectedDisasterZone?.amenitiesUrl;
        if(!amenitiesUrl) {
            return;
        }

        const bounds = this.getBounds();
        const features = (await fetchGeoJSON(amenitiesUrl, bounds, AMENITY_LIMIT))
            .filter((f: any) => SUPPORTED_AMENITIES.includes(f?.properties?.amenity));

        const layer = L.geoJSON(features, {
            pointToLayer(point, coordinates) {
                const amenity = {
                    name: point.properties.name,
                    type: point.properties.amenity.split("_").map(capitalizeString).join(" "),
                    icon: `${point.properties.amenity}.svg`,
                };

                const tooltip = `${amenity.name} (${amenity.type} @ ${coordinates.lat.toFixed(7)}, ${coordinates.lng.toFixed(7)})`;

                const marker = L.marker(coordinates, {
                    alt: tooltip,
                    icon: L.icon({
                        iconUrl: outgoing.publicUrl("map/markers/amenities", amenity.icon),
                        iconSize: [32, 32],
                    }),
                });

                marker.bindTooltip(tooltip, {
                    direction: "top",
                    offset: [0, -24],
                });

                return marker;
            },
        }).addTo(this.map);

        this.amenityCache?.remove();
        this.amenityCache = layer;
    }

    private async updateAffectedStructures() {
        if(this.getView().zoom < STRUCTURE_ZOOM_LEVEL) {
            this.affectedStructureCache?.remove();
            return;
        }

        if(!this.showStructures) {
            this.affectedStructureCache?.remove();
            return;
        }

        const affectedStructuresUrl = this.app.selectedDisasterZone?.affectedStructuresUrl;
        if(!affectedStructuresUrl) {
            return;
        }

        const bounds = this.getBounds();
        const features = await fetchGeoJSON(affectedStructuresUrl, bounds, STRUCTURE_LIMIT);

        const layer = L.geoJSON(features, {
            pane: STRUCTURE_PANE,
            style: (feature) => ({
                color: structureColor(feature, SEVERITY_COLORS.severe),
                weight: 1,
            }),
            onEachFeature(feature, structureLayer) {
                structureLayer.bindTooltip(structureTooltip(feature), {
                    direction: "top",
                });
            },
        }).addTo(this.map);

        this.affectedStructureCache?.remove();
        this.affectedStructureCache = layer;
    }

    private async updateUnaffectedStructures() {
        if(this.getView().zoom < STRUCTURE_ZOOM_LEVEL) {
            this.unaffectedStructureCache?.remove();
            return;
        }

        if(!this.showStructures) {
            this.unaffectedStructureCache?.remove();
            return;
        }

        const unaffectedStructuresUrl = this.app.selectedDisasterZone?.unaffectedStructuresUrl;
        if(!unaffectedStructuresUrl) {
            return;
        }

        const bounds = this.getBounds();
        const features = await fetchGeoJSON(unaffectedStructuresUrl, bounds, STRUCTURE_LIMIT);

        const layer = L.geoJSON(features, {
            pane: STRUCTURE_PANE,
            style: (feature) => ({
                color: structureColor(feature, SEVERITY_COLORS.none),
                weight: 1,
            }),
            onEachFeature(feature, structureLayer) {
                structureLayer.bindTooltip(structureTooltip(feature), {
                    direction: "top",
                });
            },
        }).addTo(this.map);

        this.unaffectedStructureCache?.remove();
        this.unaffectedStructureCache = layer;
    }

    private async updateHeatmap() {
        this.heatmapLayer?.remove();

        if(!this.showHeatmap) {
            return;
        }

        const heatmapUrl = this.app.selectedDisasterZone?.heatmapUrl;
        if(!heatmapUrl) {
            return;
        }

        const heatmap = await fetchHeatmap(heatmapUrl);
        this.heatmapLayer = (L as any).heatLayer(heatmap, {
            radius: 20,
            minOpacity: 0.7,
        }).addTo(this.map);
    }

    private onViewChanged() {
        this.zoomLevel = this.map.getZoom();
        this.updateRoute();

        this.updateAmenities();
        this.updateAffectedStructures();
        this.updateUnaffectedStructures();
    }

    private onToggleLayers() {
        if(this.visibleLayer === "none") {
            this.visibleLayer = "before";
        } else if(this.visibleLayer === "before") {
            this.visibleLayer = "after";
        } else {
            this.visibleLayer = "none";
        }
    }

    private onToggleHeatmap() {
        this.showHeatmap = !this.showHeatmap;
        this.updateHeatmap();
    }

    private onToggleAmenities() {
        this.showAmenities = !this.showAmenities;

        if(this.showAmenities) {
            this.setView({
                ...this.getView(),
                zoom: Math.max(AMENITY_ZOOM_LEVEL, this.map.getZoom()),
                fly: true,
            });
        }

        this.updateAmenities();
    }

    private onToggleDamagePolygons() {
        this.showStructures = !this.showStructures;

        if(this.showStructures) {
            this.setView({
                ...this.getView(),
                zoom: Math.max(STRUCTURE_ZOOM_LEVEL, this.map.getZoom()),
                fly: true,
            });
        }

        this.updateAffectedStructures();
        this.updateUnaffectedStructures();
    }

    private getView(): IViewOptions {
        return {
            center: this.map.getCenter(),
            zoom: this.map.getZoom(),
        };
    }

    private setView(options: Partial<IViewOptions>) {
        const center = options.center || this.getView().center;
        const zoom = options.zoom || this.getView().zoom;

        if(options.fly) {
            this.map.flyTo(center, zoom);
        } else {
            this.map.setView(center, zoom);
        }
    }

    private getBounds(): [ILatLng, ILatLng] {
        const bounds = this.map.getBounds();
        return [
            bounds.getNorthEast(),
            bounds.getSouthWest(),
        ];
    }

    private hasInitializedRouteView = false;

    @Watch("app.selectedDisasterZone", {immediate: true})
    private async onDisasterZoneSelected(disasterZone: IDisasterZone | null) {
        await this.$nextTick();
        if(!this.map) {
            return;
        }

        this.beforeLayer?.remove();
        this.afterLayer?.remove();

        this.beforeLayer = null;
        this.afterLayer = null;

        if(!disasterZone) {
            return;
        }

        if(disasterZone.beforeLayer) {
            this.beforeLayer = L.tileLayer(disasterZone.beforeLayer.urlTemplate, {
                attribution: disasterZone.beforeLayer.attributionHtml,
                maxZoom: 19,
                maxNativeZoom: 19,
            });
        }

        if(disasterZone.afterLayer) {
            this.afterLayer = L.tileLayer(disasterZone.afterLayer.urlTemplate, {
                attribution: disasterZone.afterLayer.attributionHtml,
                maxZoom: 19,
                maxNativeZoom: 19,
            });
        }

        this.updateHeatmap().then();
        this.onVisibleLayerChanged();

        const preserveDeepLink = !this.hasInitializedRouteView && Boolean(this.$route.params.options);
        this.hasInitializedRouteView = true;
        if(!preserveDeepLink) {
            this.setView({
                center: disasterZone.center,
                // Demo tiles exist up to z19, so the zone's own zoom is what shows imagery.
                zoom: disasterZone.center.zoom,
                fly: true,
            });
        }
    }

    @Watch("visibleLayer", {immediate: true})
    private onVisibleLayerChanged() {
        this.beforeLayer?.remove();
        this.afterLayer?.remove();

        if(this.visibleLayer === "before") {
            this.beforeLayer?.addTo(this.map);
        } else if(this.visibleLayer === "after") {
            this.afterLayer?.addTo(this.map);
        }
    }

    beforeRouteUpdate(to: Route, from: Route, next: NavigationGuardNext): void {
        next();
        this.$nextTick(() => this.navigateToRouteView());
    }

    async mounted(): Promise<void> {
        this.map = L.map(this.mapRef, {
            minZoom: 2,
            maxZoom: 19,
            maxBounds: [
                [-90, -180],
                [90, 180],
            ],
            zoomControl: true,
        }).setView([20, 0], 3);

        // The page is sized by the viewport, so Leaflet has to re-measure after layout settles.
        await this.$nextTick();
        this.map.invalidateSize();

        L.control.scale().addTo(this.map);

        // 400 is Leaflet's overlayPane, where the heat canvas is drawn; 600 is markerPane.
        const structurePane = this.map.createPane(STRUCTURE_PANE);
        structurePane.style.zIndex = "450";

        // 150 keeps the basemap under the before/after orthophoto (default tile pane is 200).
        const basemapPane = this.map.createPane(BASEMAP_PANE);
        basemapPane.style.zIndex = "150";

        this.addBasemap();

        this.visibleLayer = "before";
        this.zoomLevel = this.map.getZoom();

        this.map.on("moveend", () => this.onViewChanged());
        this.map.on("zoomend", () => this.onViewChanged());

        this.navigateToRouteView();

        try {
            if(!this.app.disasterZones.length) {
                this.app.setDisasterZones(await fetchDisasterZones());
                this.app.setDefaultDisasterZone();
            }
        } finally {
            this.pending = false;
        }
    }

    beforeDestroy(): void {
        this.map.remove();
    }
}

</script>

<style lang="scss" scoped>

$side-offset: 18px;

.map-page {
    position: relative;
    width: 100%;
    height: calc(100vh - 64px);
    overflow: hidden;
    background: var(--rahat-map-bg);
}

.map {
    display: block;
    z-index: 0;
    width: 100%;
    height: 100%;
}

/*
 * The HUD floats over imagery in both themes, so it is always an ink panel with pale rose
 * lettering - the same rule the design system gives its tooltips. Letting the theme tokens
 * through put dark ink text on a near-black panel as soon as the light theme was active.
 */
.map-info {
    position: absolute;
    top: $side-offset;
    left: $side-offset;
    z-index: 2;
    background: rgba(26, 5, 7, 0.9);
    border: 1px solid rgba(251, 239, 240, 0.16);
    border-left: 2px solid #e0424e;
    border-radius: 8px;
    padding: 11px 14px;
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35);
    max-width: 320px;
}

.info-name {
    font-size: 13px;
    font-weight: 600;
    color: var(--crimson-pale);
    margin-bottom: 6px;
}

.info-row {
    display: flex;
    gap: 10px;
    font-size: 11px;
    padding: 1px 0;
}

.info-key {
    color: rgba(251, 239, 240, 0.6);
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-size: 9px;
    align-self: center;
    min-width: 38px;
}

.info-value {
    color: var(--crimson-pale);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.info-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
    margin-top: 8px;
}

.info-chip {
    font-size: 10px;
    padding: 2px 7px;
    border-radius: 4px;
    letter-spacing: 0.03em;
}

/* Fixed tones rather than tokens: these sit on the ink HUD, not on a theme surface. */
.info-chip--affected {
    background: rgba(224, 66, 78, 0.16);
    color: #e0424e;
}

.info-chip--severe {
    background: rgba(251, 113, 133, 0.18);
    color: #fb7185;
}

.info-chip--intact {
    background: rgba(52, 211, 153, 0.18);
    color: #34d399;
}

.map-legend {
    position: absolute;
    top: $side-offset;
    right: $side-offset;
    z-index: 2;
    background: rgba(26, 5, 7, 0.9) !important;
    border-color: rgba(251, 239, 240, 0.16) !important;
    border-radius: 8px !important;
    pointer-events: none;
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
}

.map-legend-title {
    margin-bottom: 8px;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #e0424e;
}

.map-legend-row {
    display: flex;
    align-items: center;
    margin-top: 4px;
    font-size: 12px;
    color: var(--crimson-pale);
}

.map-legend-swatch {
    display: inline-block;
    width: 11px;
    height: 11px;
    margin-right: 8px;
    border-radius: 2px;
}

.map-options {
    position: absolute;
    right: $side-offset;
    // Clears the Leaflet attribution bar, which sits on the very bottom edge of the map.
    bottom: 48px;
    z-index: 2;
    display: flex;
    flex-direction: column;
    gap: 8px;
    align-items: flex-end;
}

.map-fab {
    border: 2px solid rgba(255, 255, 255, 0.12) !important;
}

.map-option-inactive {
    opacity: 0.55;
}

</style>
