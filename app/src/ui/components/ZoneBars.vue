<!--
    DISASTER RESPONSE APP
    Copyright (c) 2021 SilentByte <https://silentbyte.com/>
-->

<template>
    <div class="zones">
        <article v-for="bar in bars"
                 :key="bar.key"
                 class="zone-row"
                 :title="bar.hint">
            <div class="zone-head">
                <span class="zone-rank">{{ bar.rank }}</span>

                <svg class="zone-glyph" viewBox="0 0 24 24" aria-hidden="true">
                    <g v-if="bar.glyph === 'wave'">
                        <path d="M2.8 10.2c2.1-2.5 4-2.5 6.1 0s4 2.5 6.1 0c1.5-1.8 3-2.3 4.4-1.6" />
                        <path d="M2.8 15.4c2.1-2.5 4-2.5 6.1 0s4 2.5 6.1 0c1.5-1.8 3-2.3 4.4-1.6" />
                    </g>
                    <g v-else-if="bar.glyph === 'storm'">
                        <path d="M12 4.4a7.6 7.6 0 1 1-7.6 7.6" />
                        <path d="M12 19.6a7.6 7.6 0 1 1 7.6-7.6" />
                        <circle cx="12" cy="12" r="1.9" />
                    </g>
                    <g v-else>
                        <path d="M12 21s6.2-5.3 6.2-10a6.2 6.2 0 1 0-12.4 0C5.8 15.7 12 21 12 21Z" />
                        <circle cx="12" cy="10.6" r="2.2" />
                    </g>
                </svg>

                <span class="zone-name">{{ bar.label }}</span>

                <span class="zone-tone zone-tone--severe">
                    <svg viewBox="0 0 24 24" aria-hidden="true">
                        <path d="M13.2 2.8 5.8 13.4h4.6l-.6 7.8 7.4-10.6h-4.6l.6-7.8Z" />
                    </svg>
                    <b>{{ bar.severe }}</b>
                    <span class="zone-tone-label">severe</span>
                </span>

                <span class="zone-tone zone-tone--moderate">
                    <svg viewBox="0 0 24 24" aria-hidden="true">
                        <path d="M12 3.2 3.4 7.4 12 11.6l8.6-4.2L12 3.2Z" />
                        <path d="m3.4 12.2 8.6 4.2 8.6-4.2" />
                        <path d="m3.4 16.8 8.6 4.2 8.6-4.2" />
                    </svg>
                    <b>{{ bar.moderate }}</b>
                    <span class="zone-tone-label">moderate</span>
                </span>

                <span class="zone-total">{{ bar.total }}</span>

                <span class="zone-share">{{ bar.share }}%</span>
            </div>

            <div class="zone-track">
                <div class="zone-fill" :style="{width: bar.width}">
                    <span v-for="seg in bar.segments"
                          :key="seg.tone"
                          class="zone-seg"
                          :style="{flexGrow: seg.value, '--tone': seg.color}" />
                </div>
            </div>
        </article>

        <div v-if="!rows.length" class="zones-empty">{{ emptyLabel }}</div>
    </div>
</template>

<!--suppress JSUnusedGlobalSymbols -->
<script lang="ts">
import {
    Component,
    Prop,
    Vue,
} from "vue-property-decorator";

import { IZoneBarRow } from "@/models";
import { SEVERITY_COLORS } from "@/modules/format";

interface ISegment {
    tone: string;
    value: number;
    color: string;
}

interface IBar {
    key: string;
    rank: string;
    label: string;
    glyph: string;
    severe: number;
    moderate: number;
    total: number;
    share: number;
    width: string;
    segments: ISegment[];
    hint: string;
}

/*
 * A ranked comparison, not a chart: the bar length is the affected total against the worst-hit
 * zone, and the two tones split that total into severe and moderate. Colours come from
 * SEVERITY_COLORS so this card and the donut beside it cannot drift apart.
 */
@Component
export default class ZoneBars extends Vue {
    @Prop({type: Array, required: true})
    private readonly rows!: IZoneBarRow[];

    @Prop({type: String, default: "no zones indexed yet"})
    private readonly emptyLabel!: string;

    private get bars(): IBar[] {
        const ceiling = Math.max(1, ...this.rows.map(row => row.total));
        const grand = this.rows.reduce((sum, row) => sum + row.total, 0);

        return this.rows.map((row, index) => {
            const severe = Math.max(0, row.severe);
            const moderate = Math.max(0, row.moderate);

            /*
             * Without a severity split the bar would read as empty even though the zone has damage,
             * so an unlabelled zone falls back to a single neutral block rather than to nothing.
             */
            const segments: ISegment[] = (severe + moderate) > 0
                ? [
                    {tone: "severe", value: severe, color: SEVERITY_COLORS.severe},
                    {tone: "moderate", value: moderate, color: SEVERITY_COLORS.moderate},
                ] as ISegment[]
                : [{tone: "bare", value: 1, color: "var(--rahat-text-faint)"}] as ISegment[];

            return {
                key: `${row.label}-${index}`,
                rank: String(index + 1).padStart(2, "0"),
                label: row.label,
                glyph: this.glyphFor(row.label),
                severe,
                moderate,
                total: row.total,
                share: grand > 0 ? Math.round((row.total / grand) * 100) : 0,
                // A zero row keeps a hairline so the track still reads as a row, not as a break.
                width: `${Math.max(1.5, (row.total / ceiling) * 100)}%`,
                segments,
                hint: `${row.label} - ${row.total} affected, ${severe} severe, ${moderate} moderate`,
            };
        });
    }

    /**
     * The glyph says what hit the zone, read off the label the index gives it: a tsunami is a wave,
     * a named hurricane is a cyclone, and anything named after a place is just a point on the map.
     */
    private glyphFor(label: string): string {
        const name = label.toLowerCase();

        if(/(tsunami|flood|surge)/.test(name)) {
            return "wave";
        }

        if(/(hurricane|typhoon|cyclone|storm)/.test(name)) {
            return "storm";
        }

        return "pin";
    }
}
</script>

<style lang="scss" scoped>
.zones {
    display: flex;
    flex-direction: column;
    gap: 9px;
    height: 100%;
    min-height: 0;
    /*
     * Whether the rows can show the words "severe" and "moderate" is a question about this column's
     * width, not about the window's, so the rows are measured against the card.
     */
    container-type: inline-size;
}

/*
 * Rows grow into whatever height the card is given instead of stacking at the top, which is what
 * left the old card as a small pile of bars above a large empty area.
 */
.zone-row {
    flex: 1 1 auto;
    min-height: 62px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: 9px;
    padding: 10px 15px;
    border: 1px solid var(--rahat-border);
    border-radius: 12px;
    background: var(--rahat-track);
    transition: border-color 160ms ease, background-color 160ms ease, box-shadow 160ms ease;
}

.zone-row:hover {
    border-color: rgba(255, 59, 74, 0.42);
    background: rgba(255, 59, 74, 0.05);
    box-shadow: 0 16px 34px -24px rgba(255, 59, 74, 0.95),
        inset 0 1px 0 rgba(255, 255, 255, 0.05);
}

.zone-head {
    display: flex;
    align-items: center;
    gap: 9px;
    min-width: 0;
}

.zone-rank {
    flex: none;
    display: inline-grid;
    place-items: center;
    width: 32px;
    height: 32px;
    border: 1px solid var(--rahat-border);
    border-radius: 9px;
    background: var(--rahat-chip);
    font-family: var(--rahat-mono);
    font-size: 10.5px;
    font-weight: 600;
    letter-spacing: 0.06em;
    font-variant-numeric: tabular-nums;
    color: var(--rahat-text-dim);
    transition: border-color 160ms ease, color 160ms ease;
}

.zone-row:hover .zone-rank {
    border-color: rgba(255, 59, 74, 0.38);
    color: #ff8a94;
}

.zone-glyph {
    flex: none;
    width: 19px;
    height: 19px;
    fill: none;
    stroke: var(--rahat-text-dim);
    stroke-width: 1.7;
    stroke-linecap: round;
    stroke-linejoin: round;
    transition: stroke 160ms ease;
}

.zone-row:hover .zone-glyph {
    stroke: var(--rahat-text-bright);
}

.zone-name {
    flex: 1 1 auto;
    min-width: 0;
    font-size: 13px;
    font-weight: 600;
    color: var(--rahat-text-bright);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

/*
 * The counts sit in tone-coloured pills so the eye can pick severe from moderate before it reads
 * the words. The border is a low-alpha version of the same hue rather than currentColor, which
 * would outline the pill as loudly as the numbers inside it.
 */
.zone-tone {
    flex: none;
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 4px 9px;
    border: 1px solid transparent;
    border-radius: 9px;
    font-size: 10.5px;
    font-weight: 500;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
}

.zone-tone svg {
    width: 11px;
    height: 11px;
    fill: none;
    stroke: currentColor;
    stroke-width: 1.9;
    stroke-linecap: round;
    stroke-linejoin: round;
}

.zone-tone b {
    font-size: 11px;
    font-weight: 700;
}

.zone-tone--severe {
    border-color: rgba(251, 113, 133, 0.32);
    background: rgba(251, 113, 133, 0.09);
    color: var(--rahat-danger);
}

.zone-tone--moderate {
    border-color: rgba(251, 185, 49, 0.3);
    background: rgba(251, 185, 49, 0.08);
    color: var(--rahat-warn);
}

.zone-total {
    flex: none;
    margin-left: 2px;
    font-size: 17px;
    font-weight: 700;
    letter-spacing: -0.01em;
    font-variant-numeric: tabular-nums;
    color: var(--rahat-text-bright);
}

.zone-share {
    flex: none;
    min-width: 44px;
    padding: 3px 8px;
    border: 1px solid var(--rahat-border);
    border-radius: 9px;
    background: var(--rahat-chip);
    text-align: center;
    font-size: 10.5px;
    font-variant-numeric: tabular-nums;
    color: var(--rahat-text-dim);
}

.zone-track {
    height: 9px;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.05);
    box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.045);
    overflow: hidden;
}

.zone-fill {
    display: flex;
    height: 100%;
    border-radius: 999px;
    overflow: hidden;
    transition: width 320ms cubic-bezier(0.22, 1, 0.36, 1);
}

/* flex-basis stays 0 so the inline flex-grow values decide the severe/moderate ratio. */
.zone-seg {
    flex-basis: 0;
    flex-shrink: 1;
    min-width: 0;
    height: 100%;
    background: var(--tone, var(--rahat-text-faint));
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.24);
}

.zones-empty {
    margin: auto;
    font-size: 12px;
    color: var(--rahat-text-faint);
}

/*
 * In a narrow column the two counts plus their words no longer fit beside the zone name. The
 * numbers, their colours and the glyph still say everything, so the words are what goes.
 */
@container (max-width: 560px) {
    .zone-tone-label {
        display: none;
    }

    .zone-tone {
        gap: 4px;
        padding: 4px 7px;
    }
}

/* ---- light canvas ----------------------------------------------------------- */

html.light .zone-row:hover {
    border-color: rgba(164, 22, 26, 0.4);
    background: rgba(164, 22, 26, 0.05);
    box-shadow: 0 16px 34px -26px rgba(100, 13, 20, 0.55);
}

html.light .zone-row:hover .zone-rank {
    border-color: rgba(164, 22, 26, 0.36);
    color: var(--rahat-accent);
}

html.light .zone-tone--severe {
    border-color: rgba(190, 18, 60, 0.26);
    background: rgba(190, 18, 60, 0.07);
}

html.light .zone-tone--moderate {
    border-color: rgba(180, 83, 9, 0.26);
    background: rgba(180, 83, 9, 0.08);
}

html.light .zone-track {
    background: rgba(100, 13, 20, 0.07);
    box-shadow: inset 0 0 0 1px rgba(100, 13, 20, 0.05);
}
</style>
