<!--
    DISASTER RESPONSE APP
    Copyright (c) 2021 SilentByte <https://silentbyte.com/>
-->

<template>
    <div class="bars">
        <div v-for="(item, index) in items" :key="`${index}-${item.label}`" class="bar-row">
            <div class="bar-label" :title="item.label">{{ item.label }}</div>

            <div class="bar-track">
                <div class="bar-fill"
                     :style="{width: widthOf(item.value), background: item.color || defaultColor}" />
            </div>

            <div class="bar-value">{{ format(item.value) }}{{ suffix }}</div>
        </div>

        <div v-if="!items.length" class="bars-empty">{{ emptyLabel }}</div>
    </div>
</template>

<!--suppress JSUnusedGlobalSymbols -->
<script lang="ts">
import {
    Component,
    Prop,
    Vue,
} from "vue-property-decorator";

import { IChartBar } from "@/models";

@Component
export default class ChartBars extends Vue {
    @Prop({type: Array, required: true})
    private readonly items!: IChartBar[];

    @Prop({type: Number, default: 0})
    private readonly max!: number;

    @Prop({type: String, default: "var(--rahat-accent)"})
    private readonly defaultColor!: string;

    @Prop({type: String, default: ""})
    private readonly suffix!: string;

    @Prop({type: String, default: "no data"})
    private readonly emptyLabel!: string;

    @Prop({type: Number, default: 3})
    private readonly precision!: number;

    private get ceiling(): number {
        if(this.max > 0) {
            return this.max;
        }

        return Math.max(1, ...this.items.map(item => item.value));
    }

    private widthOf(value: number): string {
        // Keep a hairline for zero values so the track still reads as a row.
        return `${Math.max(1.5, (value / this.ceiling) * 100)}%`;
    }

    private format(value: number): string {
        return Number.isInteger(value) ? String(value) : value.toFixed(this.precision);
    }
}
</script>

<style lang="scss" scoped>
.bars {
    display: flex;
    flex-direction: column;
    gap: 7px;
}

.bar-row {
    display: grid;
    grid-template-columns: minmax(88px, 34%) 1fr auto;
    align-items: center;
    gap: 10px;
    font-size: 12px;
}

.bar-label {
    color: var(--rahat-text-dim);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.bar-track {
    height: 8px;
    background: var(--rahat-border);
    border-radius: 2px;
    overflow: hidden;
}

.bar-fill {
    height: 100%;
    border-radius: 2px;
    transition: width 240ms ease;
}

.bar-value {
    min-width: 48px;
    text-align: right;
    color: var(--rahat-text);
    font-variant-numeric: tabular-nums;
}

.bars-empty {
    padding: 18px 0;
    text-align: center;
    font-size: 12px;
    color: var(--rahat-text-faint);
}
</style>
