<!--
    DISASTER RESPONSE APP
    Copyright (c) 2021 SilentByte <https://silentbyte.com/>
-->

<template>
    <div class="line-chart">
        <div class="line-plot">
            <div class="line-axis">
                <span>{{ format(ceiling) }}</span>
                <span>{{ format(ceiling / 2) }}</span>
                <span>0</span>
            </div>

            <svg class="line-svg" viewBox="0 0 600 180" preserveAspectRatio="none" role="img">
                <line v-for="grid in [0, 90, 180]" :key="grid"
                      x1="0" :y1="grid" x2="600" :y2="grid"
                      stroke="var(--rahat-border-strong)" stroke-width="1" vector-effect="non-scaling-stroke" />

                <polygon v-if="coordinates" :points="areaPoints" :fill="fillColor" stroke="none" />
                <polyline v-if="coordinates" :points="coordinates"
                          fill="none" :stroke="color" stroke-width="2"
                          vector-effect="non-scaling-stroke" />

                <circle v-for="(point, index) in plotted" :key="`${index}-${point.label}`"
                        :cx="point.x" :cy="point.y" r="3.4"
                        :fill="isActive(index) ? color : 'var(--rahat-surface-2)'"
                        :stroke="color" stroke-width="1.6"
                        vector-effect="non-scaling-stroke" />
            </svg>
        </div>

        <div class="line-labels">
            <div v-for="(point, index) in points" :key="`lbl-${index}-${point.label}`" class="line-label">
                <span class="line-label-text">{{ point.label }}</span>
                <span class="line-label-value">{{ format(point.value) }}</span>
            </div>
        </div>
    </div>
</template>

<!--suppress JSUnusedGlobalSymbols -->
<script lang="ts">
import {
    Component,
    Prop,
    Vue,
} from "vue-property-decorator";

import { IChartPoint } from "@/models";

const VIEW_WIDTH = 600;
const VIEW_HEIGHT = 180;
const PAD_TOP = 10;

@Component
export default class ChartLine extends Vue {
    @Prop({type: Array, required: true})
    private readonly points!: IChartPoint[];

    @Prop({type: String, default: "var(--rahat-accent)"})
    private readonly color!: string;

    @Prop({type: Number, default: -1})
    private readonly activeIndex!: number;

    @Prop({type: String, default: "rgba(164, 22, 26, 0.12)"})
    private readonly fill!: string;

    private get ceiling(): number {
        // Round up to a friendly number so the axis labels are readable.
        const peak = Math.max(0.1, ...this.points.map(point => point.value));
        return Math.ceil(peak * 10) / 10;
    }

    private get fillColor(): string {
        return this.fill;
    }

    private get plotted(): Array<IChartPoint & {x: number; y: number}> {
        const count = this.points.length;
        if(count === 0) {
            return [];
        }

        const step = count > 1 ? VIEW_WIDTH / (count - 1) : 0;

        return this.points.map((point, index) => ({
            ...point,
            x: count > 1 ? index * step : VIEW_WIDTH / 2,
            y: PAD_TOP + (1 - point.value / this.ceiling) * (VIEW_HEIGHT - PAD_TOP),
        }));
    }

    private get coordinates(): string {
        return this.plotted.map(point => `${point.x},${point.y}`).join(" ");
    }

    private get areaPoints(): string {
        return `0,${VIEW_HEIGHT} ${this.coordinates} ${VIEW_WIDTH},${VIEW_HEIGHT}`;
    }

    private isActive(index: number): boolean {
        return index === this.activeIndex;
    }

    private format(value: number): string {
        return Number.isInteger(value) ? String(value) : value.toFixed(2);
    }
}
</script>

<style lang="scss" scoped>
.line-chart {
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.line-plot {
    display: flex;
    gap: 8px;
}

.line-axis {
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    font-size: 9px;
    color: var(--rahat-text-faint);
    font-variant-numeric: tabular-nums;
    padding: 2px 0 6px;
    min-width: 26px;
    text-align: right;
}

.line-svg {
    width: 100%;
    height: 180px;
    display: block;
}

.line-labels {
    display: flex;
    justify-content: space-between;
    gap: 4px;
    padding-left: 34px;
}

.line-label {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2px;
    min-width: 0;
}

.line-label-text {
    font-size: 9px;
    color: var(--rahat-text-faint);
    letter-spacing: 0.04em;
}

.line-label-value {
    font-size: 11px;
    color: var(--rahat-text-dim);
    font-variant-numeric: tabular-nums;
}
</style>
