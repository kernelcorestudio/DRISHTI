<!--
    DISASTER RESPONSE APP
    Copyright (c) 2021 SilentByte <https://silentbyte.com/>
-->

<template>
    <div class="donut">
        <svg :width="size" :height="size" :viewBox="`0 0 ${size} ${size}`" class="donut-svg">
            <circle :cx="center" :cy="center" :r="radius"
                    fill="none"
                    stroke="#22222a"
                    :stroke-width="thickness" />

            <circle v-for="segment in arcs"
                    :key="segment.label"
                    :cx="center" :cy="center" :r="radius"
                    fill="none"
                    :stroke="segment.color"
                    :stroke-width="thickness"
                    stroke-linecap="butt"
                    :stroke-dasharray="`${segment.length} ${circumference - segment.length}`"
                    :transform="`rotate(${segment.rotate} ${center} ${center})`" />

            <text :x="center" :y="center - 2" text-anchor="middle" class="donut-total">{{ total }}</text>
            <text :x="center" :y="center + 15" text-anchor="middle" class="donut-caption">{{ caption }}</text>
        </svg>

        <ul class="donut-legend">
            <li v-for="segment in segments" :key="segment.label" class="donut-item">
                <span class="donut-swatch" :style="{background: segment.color}" />
                <span class="donut-label">{{ segment.label }}</span>
                <span class="donut-value">{{ segment.value }}</span>
                <span class="donut-share">{{ share(segment.value) }}</span>
            </li>
        </ul>
    </div>
</template>

<!--suppress JSUnusedGlobalSymbols -->
<script lang="ts">
import {
    Component,
    Prop,
    Vue,
} from "vue-property-decorator";

import { IChartSegment } from "@/models";

interface IArc extends IChartSegment {
    length: number;
    rotate: number;
}

const FULL_CIRCLE = 360;

@Component
export default class ChartDonut extends Vue {
    @Prop({type: Array, required: true})
    private readonly segments!: IChartSegment[];

    @Prop({type: Number, default: 150})
    private readonly size!: number;

    @Prop({type: Number, default: 16})
    private readonly thickness!: number;

    @Prop({type: String, default: "total"})
    private readonly caption!: string;

    private get center(): number {
        return this.size / 2;
    }

    private get radius(): number {
        return (this.size - this.thickness) / 2;
    }

    private get circumference(): number {
        return 2 * Math.PI * this.radius;
    }

    private get total(): number {
        return this.segments.reduce((sum, segment) => sum + segment.value, 0);
    }

    private get arcs(): IArc[] {
        const total = this.total;
        if(total <= 0) {
            return [];
        }

        let offset = 0;

        return this.segments
            .filter(segment => segment.value > 0)
            .map(segment => {
                // Dash length is proportional to the value; rotate each arc past the previous ones.
                const fraction = segment.value / total;
                const arc: IArc = {
                    ...segment,
                    length: fraction * this.circumference,
                    rotate: -90 + (offset / total) * FULL_CIRCLE,
                };

                offset += segment.value;
                return arc;
            });
    }

    private share(value: number): string {
        const total = this.total;
        return total > 0 ? `${Math.round((value / total) * 100)}%` : "0%";
    }
}
</script>

<style lang="scss" scoped>
.donut {
    display: flex;
    align-items: center;
    gap: 18px;
    flex-wrap: wrap;
}

.donut-svg {
    flex: 0 0 auto;
}

.donut-total {
    fill: var(--rahat-text);
    font-size: 22px;
    font-weight: 600;
}

.donut-caption {
    fill: rgba(242, 242, 242, 0.4);
    font-size: 9px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
}

.donut-legend {
    list-style: none;
    margin: 0;
    padding: 0;
    flex: 1 1 160px;
    min-width: 150px;
}

.donut-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 4px 0;
    font-size: 12px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.04);
}

.donut-item:last-child {
    border-bottom: none;
}

.donut-swatch {
    width: 9px;
    height: 9px;
    border-radius: 2px;
    flex: 0 0 auto;
}

.donut-label {
    color: var(--rahat-text-dim);
    text-transform: capitalize;
}

.donut-value {
    margin-left: auto;
    color: var(--rahat-text);
    font-variant-numeric: tabular-nums;
}

.donut-share {
    width: 38px;
    text-align: right;
    color: var(--rahat-text-faint);
    font-size: 11px;
    font-variant-numeric: tabular-nums;
}
</style>
