<!--
    DISASTER RESPONSE APP
    Copyright (c) 2021 SilentByte <https://silentbyte.com/>
-->

<template>
    <div class="page">
        <div class="grid grid--kpi">
            <StatCard label="footprint iou" :value="evaluation.footprint_iou_mean" hint="4 demo scenes, local measurement" />
            <StatCard label="buildings classified" :value="evaluation.buildings_classified" hint="stage-1 -> stage-2 pass" />
            <StatCard label="tile alignment" :value="evaluation.tile_alignment_drgb_mean" unit="dRGB" hint="lower is better, 1600 samples" />
            <StatCard label="min area" :value="minArea" unit="px" hint="speckle filter, 384 mask space" />
        </div>

        <div class="scope-bar">
            <span class="label">scope</span>

            <v-select dense outlined hide-details
                      class="scope-select"
                      item-value="id"
                      item-text="label"
                      :items="scopeOptions"
                      :menu-props="menuProps"
                      v-model="scope" />
        </div>

        <div class="grid grid--two analytics-grid">
            <SectionCard title="damage split" :subtitle="scopeLabel">
                <DonutChart :segments="severitySegments" caption="buildings" />
            </SectionCard>

            <SectionCard title="stage-1 footprint iou per scene"
                         :subtitle="`measured ${evaluation.measured_on || '-'} against xBD ground truth`">
                <ChartBars :items="iouByScene" :max="1" :precision="3" suffix="" />
            </SectionCard>

            <SectionCard title="affected structures per zone" subtitle="stage-2 severe + moderate">
                <ChartBars :items="affectedByZone" />
            </SectionCard>

            <SectionCard title="intact structures per zone" subtitle="classified with no visible damage">
                <ChartBars :items="intactByZone" default-color="var(--rahat-ok)" />
            </SectionCard>

            <SectionCard title="severe vs moderate" :subtitle="scopeLabel">
                <div class="split-chart">
                    <div class="split-row">
                        <span class="split-key">severe</span>
                        <ChartBars :items="severeSeries" default-color="var(--rahat-danger)" />
                    </div>
                    <div class="split-row">
                        <span class="split-key">moderate</span>
                        <ChartBars :items="moderateSeries" default-color="var(--rahat-warn)" />
                    </div>
                </div>
            </SectionCard>

            <SectionCard title="min-area sweep" subtitle="footprint iou vs speckle filter size">
                <ChartLine :points="sweepPoints" :active-index="activeSweepIndex" />
            </SectionCard>

            <SectionCard title="job duration" subtitle="last 10 completed inferences">
                <ChartBars :items="jobDurations" :precision="1" suffix="s" empty-label="no completed jobs in this session" />
            </SectionCard>

            <SectionCard title="offline tiles per zoom" subtitle="self-hosted XYZ pyramid served by the app">
                <ChartBars :items="tilesByZoom" />
            </SectionCard>
        </div>
    </div>
</template>

<script lang="ts">
import {
    Component,
    Vue,
} from "vue-property-decorator";

import { getModule } from "vuex-module-decorators";
import { AppModule } from "@/store/app";

import ChartBars from "@/ui/components/ChartBars.vue";
import ChartLine from "@/ui/components/ChartLine.vue";
import DonutChart from "@/ui/components/DonutChart.vue";
import SectionCard from "@/ui/components/SectionCard.vue";
import StatCard from "@/ui/components/StatCard.vue";

import {
    IChartBar,
    IChartPoint,
    IChartSegment,
    IEvaluation,
    IZoneInventory,
} from "@/models";
import {
    SEVERITY_COLORS,
    formatClock,
    shortScene,
} from "@/modules/format";
import { SELECT_MENU_PROPS } from "@/modules/utils";

interface IScopeOption {
    id: string;
    label: string;
}

interface ISweepPoint extends IChartPoint {
    minArea: number;
}

const EMPTY_EVALUATION: IEvaluation = {
    measured_on: "",
    scenes: [],
    footprint_iou_mean: 0,
    footprint_iou_by_scene: {},
    buildings_classified: 0,
    min_area_sweep: [],
    selected_min_area: 0,
    tile_alignment_drgb_mean: 0,
    notes: [],
};

@Component({
    components: {
        ChartBars,
        ChartLine,
        DonutChart,
        SectionCard,
        StatCard,
    },
})
export default class AnalyticsView extends Vue {
    private readonly app = getModule(AppModule);

    private scope = "";

    /** Keep the scope panel under its field instead of on top of it; see modules/utils. */
    private readonly menuProps = SELECT_MENU_PROPS;

    private get diagnostics() {
        return this.app.diagnostics;
    }

    private get evaluation(): IEvaluation {
        return this.diagnostics?.evaluation || EMPTY_EVALUATION;
    }

    private get zones(): IZoneInventory[] {
        return this.diagnostics?.zones || [];
    }

    private get minArea(): number {
        return this.diagnostics ? this.diagnostics.min_area : 0;
    }

    private get scopeOptions(): IScopeOption[] {
        return [
            {id: "", label: "all zones"},
            ...this.zones.map(zone => ({id: zone.zone_id, label: zone.zone_id})),
        ];
    }

    private get scopeLabel(): string {
        return this.scope ? this.scope : "all indexed zones";
    }

    private get scopedZones(): IZoneInventory[] {
        return this.scope
            ? this.zones.filter(zone => zone.zone_id === this.scope)
            : this.zones;
    }

    private get severitySegments(): IChartSegment[] {
        return [
            {label: "severe", value: this.sumSeverity("severe"), color: SEVERITY_COLORS.severe},
            {label: "moderate", value: this.sumSeverity("moderate"), color: SEVERITY_COLORS.moderate},
            {label: "intact", value: this.sumFeatures("structures-unaffected"), color: SEVERITY_COLORS.intact},
        ];
    }

    private get iouByScene(): IChartBar[] {
        return Object.entries(this.evaluation.footprint_iou_by_scene || {})
            .map(([scene, iou]) => ({label: shortScene(scene), value: iou}))
            .sort((a, b) => b.value - a.value);
    }

    private get affectedByZone(): IChartBar[] {
        return this.scopedZones
            .map(zone => ({
                label: shortScene(zone.zone_id),
                value: this.features(zone, "structures-affected"),
            }))
            .sort((a, b) => b.value - a.value);
    }

    private get intactByZone(): IChartBar[] {
        return this.scopedZones
            .map(zone => ({
                label: shortScene(zone.zone_id),
                value: this.features(zone, "structures-unaffected"),
            }))
            .sort((a, b) => b.value - a.value);
    }

    private get severeSeries(): IChartBar[] {
        return this.scopedZones
            .map(zone => ({
                label: shortScene(zone.zone_id),
                value: zone.layers["structures-affected"]?.severity?.severe || 0,
            }))
            .filter(item => item.value > 0)
            .sort((a, b) => b.value - a.value);
    }

    private get moderateSeries(): IChartBar[] {
        return this.scopedZones
            .map(zone => ({
                label: shortScene(zone.zone_id),
                value: zone.layers["structures-affected"]?.severity?.moderate || 0,
            }))
            .filter(item => item.value > 0)
            .sort((a, b) => b.value - a.value);
    }

    private get sweepPoints(): ISweepPoint[] {
        return [...(this.evaluation.min_area_sweep || [])]
            .sort((a, b) => a.min_area - b.min_area)
            .map(point => ({
                label: String(point.min_area),
                value: point.mean_iou,
                minArea: point.min_area,
            }));
    }

    private get activeSweepIndex(): number {
        return this.sweepPoints.findIndex(point => point.minArea === this.evaluation.selected_min_area);
    }

    private get jobDurations(): IChartBar[] {
        return this.app.jobs
            .filter(job => job.status === "succeeded" && job.duration_seconds !== null)
            .slice(0, 10)
            .reverse()
            .map(job => ({
                label: `${formatClock(job.created_at)} ${shortScene(job.zone_id)}`,
                value: job.duration_seconds || 0,
            }));
    }

    private get tilesByZoom(): IChartBar[] {
        const byZoom: Record<string, number> = {};

        for(const zone of this.diagnostics?.imagery || []) {
            for(const role of Object.values(zone.roles)) {
                for(const [zoom, count] of Object.entries(role.by_zoom)) {
                    byZoom[zoom] = (byZoom[zoom] || 0) + count;
                }
            }
        }

        return Object.keys(byZoom)
            .sort((a, b) => Number(a) - Number(b))
            .map(zoom => ({label: `z${zoom}`, value: byZoom[zoom]}));
    }

    private features(zone: IZoneInventory, layer: string): number {
        return zone.layers[layer]?.features || 0;
    }

    private sumFeatures(layer: string): number {
        return this.scopedZones.reduce((sum, zone) => sum + this.features(zone, layer), 0);
    }

    private sumSeverity(label: string): number {
        return this.scopedZones.reduce((sum, zone) => {
            return sum + (zone.layers["structures-affected"]?.severity?.[label] || 0);
        }, 0);
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

.scope-select {
    width: 240px;
    flex: 0 0 auto;
}

.analytics-grid {
    margin-top: 16px;
    padding-bottom: 10px;
}

.split-chart {
    display: flex;
    flex-direction: column;
    gap: 14px;
}

.split-row {
    display: flex;
    flex-direction: column;
    gap: 6px;
}

.split-key {
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--rahat-text-faint);
}
</style>
