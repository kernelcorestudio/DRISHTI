<!--
    DISASTER RESPONSE APP
    Copyright (c) 2021 SilentByte <https://silentbyte.com/>
-->

<template>
    <div class="page">
        <div class="grid grid--kpi">
            <StatCard label="zones" :value="rows.length" hint="directories under the data dir" />
            <StatCard label="geojson features" :value="totalFeatures" hint="affected + intact + amenities" />
            <StatCard label="artefact size" :value="totalSize" hint="all layers on disk" />
            <StatCard label="tiles" :value="totalTiles" hint="self-hosted XYZ pyramid" />
        </div>

        <SectionCard class="zones-card"
                     title="indexed zones"
                     subtitle="click a row to load that scene on the map"
                     flush>
            <div class="zones-table">
                <table>
                    <thead>
                    <tr>
                        <th>scene</th>
                        <th>name</th>
                        <th class="num">affected</th>
                        <th class="num">severe</th>
                        <th class="num">moderate</th>
                        <th class="num">intact</th>
                        <th class="num">amenities</th>
                        <th class="num">geojson</th>
                        <th class="num">tiles</th>
                        <th>zooms</th>
                        <th />
                    </tr>
                    </thead>

                    <tbody>
                    <tr v-for="row in rows" :key="row.scene"
                        :class="{'row--active': row.scene === selectedScene}"
                        @click="onOpen(row.scene)">
                        <td class="mono scene">{{ row.scene }}</td>
                        <td class="dim">{{ row.name }}</td>
                        <td class="num strong">{{ row.affected }}</td>
                        <td class="num severe">{{ row.severe }}</td>
                        <td class="num moderate">{{ row.moderate }}</td>
                        <td class="num intact">{{ row.intact }}</td>
                        <td class="num amenities">{{ row.amenities }}</td>
                        <td class="num dim">{{ row.size }}</td>
                        <td class="num dim">{{ row.tiles }}</td>
                        <td class="zooms">{{ row.zooms }}</td>
                        <td class="action-cell">
                            <v-icon small>mdi-arrow-right</v-icon>
                        </td>
                    </tr>

                    <tr v-if="!rows.length">
                        <td colspan="11" class="empty">no zones found in the data directory</td>
                    </tr>
                    </tbody>
                </table>
            </div>
        </SectionCard>

        <SectionCard class="zones-card"
                     title="layer urls"
                     subtitle="what GeoServ serves for the selected zone">
            <div class="layers">
                <div class="layer-row">
                    <span class="label">affected</span>
                    <span class="mono layer-url">{{ layerUrls.affected }}</span>
                </div>
                <div class="layer-row">
                    <span class="label">unaffected</span>
                    <span class="mono layer-url">{{ layerUrls.unaffected }}</span>
                </div>
                <div class="layer-row">
                    <span class="label">heatmap</span>
                    <span class="mono layer-url">{{ layerUrls.heatmap }}</span>
                </div>
                <div class="layer-row">
                    <span class="label">amenities</span>
                    <span class="mono layer-url">{{ layerUrls.amenities }}</span>
                </div>
                <div class="layer-row">
                    <span class="label">before layer</span>
                    <span class="mono layer-url">{{ layerUrls.before }}</span>
                </div>
                <div class="layer-row">
                    <span class="label">after layer</span>
                    <span class="mono layer-url">{{ layerUrls.after }}</span>
                </div>
            </div>
        </SectionCard>
    </div>
</template>

<script lang="ts">
import {
    Component,
    Vue,
} from "vue-property-decorator";

import { getModule } from "vuex-module-decorators";
import { AppModule } from "@/store/app";

import SectionCard from "@/ui/components/SectionCard.vue";
import StatCard from "@/ui/components/StatCard.vue";

import { IDisasterZone, IZoneInventory } from "@/models";
import { zoneBySceneId, zoneSceneId } from "@/modules/api";
import { formatBytes } from "@/modules/format";

interface IZoneRow {
    scene: string;
    name: string;
    affected: number;
    severe: number;
    moderate: number;
    intact: number;
    amenities: number;
    size: string;
    tiles: number;
    zooms: string;
    bytes: number;
}

@Component({
    components: {
        SectionCard,
        StatCard,
    },
})
export default class ZonesView extends Vue {
    private readonly app = getModule(AppModule);

    private get zones(): IZoneInventory[] {
        return this.app.diagnostics?.zones || [];
    }

    private get selectedScene(): string | null {
        const zone = this.app.selectedDisasterZone;
        return zone ? zoneSceneId(zone) : null;
    }

    private get selectedZone(): IDisasterZone | null {
        return this.app.selectedDisasterZone;
    }

    // Resolved here because the template compiler rejects optional chaining.
    private get layerUrls(): Record<string, string> {
        const zone = this.selectedZone;

        return {
            affected: (zone && zone.affectedStructuresUrl) || "-",
            unaffected: (zone && zone.unaffectedStructuresUrl) || "-",
            heatmap: (zone && zone.heatmapUrl) || "-",
            amenities: (zone && zone.amenitiesUrl) || "-",
            before: (zone && zone.beforeLayer && zone.beforeLayer.urlTemplate) || "-",
            after: (zone && zone.afterLayer && zone.afterLayer.urlTemplate) || "-",
        };
    }

    private get rows(): IZoneRow[] {
        return this.zones.map(zone => {
            const imagery = (this.app.diagnostics?.imagery || [])
                .find(entry => entry.zone_id === zone.zone_id);

            const roles = Object.values(imagery?.roles || {});
            const zooms = new Set<string>();

            for(const role of roles) {
                Object.keys(role.by_zoom).forEach(zoom => zooms.add(zoom));
            }

            const bytes = Object.values(zone.layers).reduce((sum, layer) => sum + layer.bytes, 0);

            return {
                scene: zone.zone_id,
                name: this.zoneName(zone.zone_id),
                affected: this.features(zone, "structures-affected"),
                severe: zone.layers["structures-affected"]?.severity?.severe || 0,
                moderate: zone.layers["structures-affected"]?.severity?.moderate || 0,
                intact: this.features(zone, "structures-unaffected"),
                amenities: this.features(zone, "amenities"),
                size: formatBytes(bytes),
                tiles: roles.reduce((sum, role) => sum + role.tiles, 0),
                zooms: this.zoomRange([...zooms]),
                bytes,
            };
        });
    }

    private get totalFeatures(): number {
        return this.rows.reduce((sum, row) => {
            return sum + row.affected + row.intact + row.amenities;
        }, 0);
    }

    private get totalSize(): string {
        return formatBytes(this.rows.reduce((sum, row) => sum + row.bytes, 0));
    }

    private get totalTiles(): number {
        return this.rows.reduce((sum, row) => sum + row.tiles, 0);
    }

    private zoneName(sceneId: string): string {
        return zoneBySceneId(this.app.disasterZones, sceneId)?.name || "not registered";
    }

    private zoomRange(zooms: string[]): string {
        const sorted = zooms.map(Number).sort((a, b) => a - b);
        if(!sorted.length) {
            return "-";
        }

        const first = sorted[0];
        const last = sorted[sorted.length - 1];
        return first === last ? `z${first}` : `z${first}-${last}`;
    }

    private onOpen(sceneId: string) {
        const zone = zoneBySceneId(this.app.disasterZones, sceneId);
        if(!zone) {
            return;
        }

        if(zone.id !== this.app.selectedDisasterZone?.id) {
            this.app.setSelectedDisasterZone(zone);
        }

        this.$router.push("/map").catch(() => undefined);
    }

    private features(zone: IZoneInventory, layer: string): number {
        return zone.layers[layer]?.features || 0;
    }
}
</script>

<style lang="scss" scoped>
.zones-card {
    margin-top: 16px;
}

.zones-card:last-child {
    margin-bottom: 10px;
}

.zones-table {
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

td {
    padding: 10px 12px;
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
    box-shadow: inset 2px 0 0 var(--rahat-accent);
}

.scene {
    color: var(--rahat-text);
    font-size: 11.5px;
}

.num {
    text-align: right;
    font-variant-numeric: tabular-nums;
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

.amenities {
    color: var(--rahat-info);
}

.zooms {
    font-family: var(--rahat-mono);
    font-size: 11px;
    color: var(--rahat-text-faint);
}

.action-cell {
    text-align: right;
    color: var(--rahat-text-faint);
}

.empty {
    padding: 30px;
    text-align: center;
    color: var(--rahat-text-faint);
}

.layers {
    display: flex;
    flex-direction: column;
    gap: 6px;
}

.layer-row {
    display: flex;
    gap: 14px;
    align-items: baseline;
    padding: 5px 0;
    border-bottom: 1px solid var(--rahat-border);
}

.layer-row:last-child {
    border-bottom: none;
}

.layer-row .label {
    min-width: 96px;
}

.layer-url {
    color: var(--rahat-text-dim);
    font-size: 11px;
    word-break: break-all;
}
</style>
