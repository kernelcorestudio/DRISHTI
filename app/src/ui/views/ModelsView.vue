<!--
    DISASTER RESPONSE APP
    Copyright (c) 2021 SilentByte <https://silentbyte.com/>
-->

<template>
    <div class="page">
        <div class="grid grid--two">
            <SectionCard v-for="model in models"
                         :key="model.role"
                         :title="titleOf(model.role)"
                         :subtitle="model.meta.arch || 'architecture not recorded'">
                <template v-slot:actions>
                    <span class="state" :class="model.exists ? 'state--ok' : 'state--bad'">
                        {{ model.exists ? "loaded" : "missing" }}
                    </span>
                </template>

                <div class="meta">
                    <div v-for="row in metaRows(model)" :key="row.key" class="meta-row">
                        <span class="label">{{ row.key }}</span>
                        <span class="meta-value" :class="{'mono': row.mono}">{{ row.value }}</span>
                    </div>
                </div>

                <div v-if="metricBars(model).length" class="metrics">
                    <div class="metrics-title">validation metrics</div>
                    <ChartBars :items="metricBars(model)" :max="1" :precision="4" />
                </div>

                <p v-if="!model.meta.metrics" class="footnote">
                    no metrics recorded next to the checkpoint
                </p>
            </SectionCard>
        </div>

        <div class="grid grid--two block">
            <SectionCard title="local evaluation" subtitle="measured on the four demo scenes, not the kaggle split">
                <div class="eval-head">
                    <div class="eval-score">
                        <span class="eval-value">{{ evaluation.footprint_iou_mean }}</span>
                        <span class="label">footprint iou</span>
                    </div>
                    <div class="eval-meta">
                        <div class="meta-row">
                            <span class="label">measured on</span>
                            <span class="meta-value">{{ evaluation.measured_on || "-" }}</span>
                        </div>
                        <div class="meta-row">
                            <span class="label">buildings</span>
                            <span class="meta-value">{{ evaluation.buildings_classified }}</span>
                        </div>
                        <div class="meta-row">
                            <span class="label">tile alignment</span>
                            <span class="meta-value">dRGB {{ evaluation.tile_alignment_drgb_mean }}</span>
                        </div>
                        <div class="meta-row">
                            <span class="label">min area</span>
                            <span class="meta-value">{{ minAreaLabel }}</span>
                        </div>
                    </div>
                </div>

                <ChartBars class="iou-bars" :items="iouByScene" :max="1" :precision="3" />
            </SectionCard>

            <SectionCard title="min-area sweep" subtitle="why 20 px was chosen">
                <ChartLine :points="sweepPoints" :active-index="activeSweepIndex" />

                <div class="sweep-table">
                    <div class="sweep-row sweep-row--head">
                        <span>min area</span>
                        <span class="num">mean iou</span>
                        <span class="num">polygons / tile</span>
                    </div>
                    <div v-for="point in sweepPoints" :key="point.minArea" class="sweep-row"
                         :class="{'sweep-row--active': point.minArea === evaluation.selected_min_area}">
                        <span>{{ point.minArea }} px</span>
                        <span class="num">{{ point.value }}</span>
                        <span class="num">{{ polygonsFor(point.minArea) }}</span>
                    </div>
                </div>
            </SectionCard>
        </div>

        <SectionCard class="block" title="notes" subtitle="what the numbers mean in practice">
            <ul class="notes">
                <li v-for="(note, index) in evaluation.notes" :key="index">{{ note }}</li>
                <li v-if="!evaluation.notes.length" class="faint">no notes recorded</li>
            </ul>
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

import ChartBars from "@/ui/components/ChartBars.vue";
import ChartLine from "@/ui/components/ChartLine.vue";
import SectionCard from "@/ui/components/SectionCard.vue";

import {
    IChartBar,
    IChartPoint,
    IEvaluation,
    IModelInfo,
    IModelMeta,
} from "@/models";
import { shortScene } from "@/modules/format";

interface IMetaRow {
    key: string;
    value: string;
    mono?: boolean;
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

const TITLES: Record<string, string> = {
    stage1: "stage-1 · building footprints",
    stage2: "stage-2 · damage classification",
};

@Component({
    components: {
        ChartBars,
        ChartLine,
        SectionCard,
    },
})
export default class ModelsView extends Vue {
    private readonly app = getModule(AppModule);

    private get diagnostics() {
        return this.app.diagnostics;
    }

    private get models(): IModelInfo[] {
        return this.diagnostics?.models || [];
    }

    private get minAreaLabel(): string {
        return this.diagnostics ? `${this.diagnostics.min_area} px` : "-";
    }

    private get evaluation(): IEvaluation {
        return this.diagnostics?.evaluation || EMPTY_EVALUATION;
    }

    private get iouByScene(): IChartBar[] {
        return Object.entries(this.evaluation.footprint_iou_by_scene || {})
            .map(([scene, iou]) => ({label: shortScene(scene), value: iou}))
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

    private titleOf(role: string): string {
        return TITLES[role] || role;
    }

    private metaRows(model: IModelInfo): IMetaRow[] {
        const meta = model.meta || {};

        return [
            {key: "file", value: model.path.split(/[\\/]/).pop() || model.path, mono: true},
            {key: "size", value: model.size_mb !== null ? `${model.size_mb} MB` : "-"},
            {key: "input size", value: meta.input_size ? `${meta.input_size} px` : "-"},
            {key: "loss", value: meta.loss || "-"},
            {key: "train tiles", value: meta.train_tiles ? String(meta.train_tiles) : "-"},
            {key: "valid tiles", value: meta.valid_tiles ? String(meta.valid_tiles) : "-"},
            {key: "trained", value: meta.trained || "-"},
            {key: "trained on", value: meta.trained_on || "-"},
            {key: "classes", value: this.classList(meta)},
            {key: "held-out events", value: (meta.valid_events || []).join(", ") || "-"},
        ];
    }

    private classList(meta: IModelMeta): string {
        const list = meta.classes || meta.codes || [];
        return list.length ? list.join(", ") : "-";
    }

    private metricBars(model: IModelInfo): IChartBar[] {
        return Object.entries(model.meta.metrics || {})
            .map(([key, value]) => ({
                label: key.replace(/_/g, " "),
                value,
            }));
    }

    private polygonsFor(minArea: number): number {
        const point = (this.evaluation.min_area_sweep || [])
            .find(entry => entry.min_area === minArea);

        return point ? point.polygons_per_tile : 0;
    }
}
</script>

<style lang="scss" scoped>
.block {
    margin-top: 16px;
}

.block:last-child {
    margin-bottom: 10px;
}

.state {
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 2px 7px;
    border-radius: 2px;
}

.state--ok {
    background: var(--rahat-ok-soft);
    color: var(--rahat-ok);
}

.state--bad {
    background: var(--rahat-danger-soft);
    color: var(--rahat-danger);
}

.meta {
    display: flex;
    flex-direction: column;
}

.meta-row {
    display: flex;
    align-items: baseline;
    gap: 12px;
    padding: 4px 0;
    border-bottom: 1px solid var(--rahat-border);
}

.meta-row:last-child {
    border-bottom: none;
}

.meta-row .label {
    min-width: 108px;
    flex: 0 0 auto;
}

.meta-value {
    font-size: 12px;
    color: var(--rahat-text-dim);
    word-break: break-word;
}

.metrics {
    margin-top: 16px;
    border-top: 1px solid var(--rahat-border);
    padding-top: 12px;
}

.metrics-title {
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--rahat-text-faint);
    margin-bottom: 8px;
}

.footnote {
    margin: 12px 0 0;
    font-size: 11px;
    color: var(--rahat-text-faint);
}

.eval-head {
    display: flex;
    gap: 22px;
    align-items: flex-start;
    margin-bottom: 16px;
}

.eval-score {
    display: flex;
    flex-direction: column;
    gap: 2px;
    border-left: 2px solid var(--rahat-yellow);
    padding-left: 12px;
}

.eval-value {
    font-size: 34px;
    font-weight: 600;
    line-height: 1;
    color: var(--rahat-yellow);
    font-variant-numeric: tabular-nums;
}

.eval-meta {
    flex: 1 1 auto;
}

.iou-bars {
    border-top: 1px solid var(--rahat-border);
    padding-top: 12px;
}

.sweep-table {
    margin-top: 16px;
}

.sweep-row {
    display: grid;
    grid-template-columns: 1fr 90px 120px;
    gap: 8px;
    padding: 5px 8px;
    font-size: 11.5px;
    color: var(--rahat-text-dim);
    border-bottom: 1px solid var(--rahat-border);
}

.sweep-row--head {
    font-size: 9px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--rahat-text-faint);
    border-bottom-color: var(--rahat-border);
}

.sweep-row--active {
    background: var(--rahat-accent-soft);
    color: var(--rahat-highlight);
    box-shadow: inset 2px 0 0 var(--rahat-accent);
}

.num {
    text-align: right;
    font-variant-numeric: tabular-nums;
}

.notes {
    margin: 0;
    padding-left: 18px;
    font-size: 12px;
    line-height: 1.65;
    color: var(--rahat-text-dim);
}

.notes li {
    margin-bottom: 6px;
}
</style>
