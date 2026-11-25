<!--
    DISASTER RESPONSE APP
    Copyright (c) 2021 SilentByte <https://silentbyte.com/>

    The root class is `gauge` rather than `ring` on purpose: the app loads a generated Tailwind
    sheet where `ring` is a box-shadow utility, and it would paint a blue 3px halo around the dial.
-->
<template>
    <div class="gauge" :class="`gauge--${tone}`" :title="hint">
        <div class="gauge-dial">
            <span class="gauge-halo" aria-hidden="true" />

            <svg class="gauge-svg" viewBox="0 0 120 120" aria-hidden="true">
                <circle class="gauge-track" cx="60" cy="60" r="50" />
                <circle class="gauge-arc" cx="60" cy="60" r="50" :style="arcStyle" />
            </svg>

            <span class="gauge-value">
                {{ shown }}<span v-if="!display" class="gauge-unit">%</span>
            </span>
        </div>

        <!-- The label is a pill rather than bare text so it can carry the metric's own glyph and
             stay legible over the card's spotlight wash. -->
        <span class="gauge-pill">
            <svg v-if="icon === 'layers'"
                 class="gauge-icon" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M12 3.6 3.9 8 12 12.4 20.1 8 12 3.6Z" />
                <path d="m3.9 12.6 8.1 4.3 8.1-4.3" />
                <path d="m3.9 17 8.1 4.3 8.1-4.3" />
            </svg>

            <svg v-else-if="icon === 'stack'"
                 class="gauge-icon" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M12 3.6 3.9 8 12 12.4 20.1 8 12 3.6Z"
                      fill="currentColor" fill-opacity="0.22" />
                <path d="M12 3.6 3.9 8 12 12.4 20.1 8 12 3.6Z" />
                <path d="m3.9 12.6 8.1 4.3 8.1-4.3" />
            </svg>

            <svg v-else-if="icon === 'target'"
                 class="gauge-icon" viewBox="0 0 24 24" aria-hidden="true">
                <circle cx="12" cy="12" r="8.4" />
                <circle cx="12" cy="12" r="3.1" fill="currentColor" stroke="none" />
                <path d="M12 1.8v2.4M12 19.8v2.4M1.8 12h2.4M19.8 12h2.4" />
            </svg>

            <svg v-else
                 class="gauge-icon" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M4.6 19.6v-5.2M12 19.6V9.4M19.4 19.6V4.6" />
            </svg>

            <span class="gauge-label">{{ label }}</span>
        </span>
    </div>
</template>

<!--suppress JSUnusedGlobalSymbols -->
<script lang="ts">
import {
    Component,
    Prop,
    Vue,
} from "vue-property-decorator";

const RADIUS = 50;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

/**
 * A single score ring.
 *
 * The arc is drawn with `stroke-dashoffset` rather than a conic gradient so it renders
 * identically in every browser and can be animated by the compositor. The offset is declared in
 * CSS as the final value and the keyframe only supplies the start, so nothing depends on
 * `animation-fill-mode` holding state after the fill completes.
 *
 * The arc starts at twelve o'clock and covers `value` percent of the full circle: the dial is a
 * progress reading, not a speedometer, so a 41% score must look like less than half of it.
 */
@Component
export default class RingGauge extends Vue {
    @Prop({type: String, required: true})
    private readonly label!: string;

    /** Percentage, 0-100. Values outside the range are clamped rather than trusted. */
    @Prop({type: Number, required: true})
    private readonly value!: number;

    /** Overrides the number printed inside the ring, e.g. "2/2". */
    @Prop({type: String, default: ""})
    private readonly display!: string;

    @Prop({type: String, default: "ok"})
    private readonly tone!: string;

    /** Glyph shown inside the label pill: layers | stack | target | bars. */
    @Prop({type: String, default: "bars"})
    private readonly icon!: string;

    /** Tooltip that states where the number came from. */
    @Prop({type: String, default: ""})
    private readonly hint!: string;

    private get shown(): string {
        return this.display || String(Math.round(this.value));
    }

    private get arcStyle(): Record<string, string> {
        const clamped = Math.max(0, Math.min(100, this.value));

        return {
            "stroke-dasharray": `${CIRCUMFERENCE}`,
            "--gauge-from": `${CIRCUMFERENCE}`,
            "--gauge-to": `${CIRCUMFERENCE * (1 - clamped / 100)}`,
        };
    }
}
</script>

<style lang="scss" scoped>
.gauge {
    --gauge-color: var(--rahat-accent-2);
    --gauge-rgb: 208, 30, 44;
    --gauge-track: rgba(255, 255, 255, 0.07);

    display: flex;
    flex: 1 1 0;
    flex-direction: column;
    align-items: center;
    gap: 9px;
    min-width: 0;
}

.gauge--ok {
    --gauge-color: #34d399;
    --gauge-rgb: 52, 211, 153;
}

.gauge--warn {
    --gauge-color: #fbb931;
    --gauge-rgb: 251, 185, 49;
}

/* The reference reads as a stop signal, so the low scores are a pure red rather than the softer
   rose the app uses for warnings elsewhere. */
.gauge--bad {
    --gauge-color: #ff3b4a;
    --gauge-rgb: 255, 59, 74;
}

.gauge-dial {
    position: relative;
    display: grid;
    place-items: center;
    width: 100%;
    max-width: 104px;
    aspect-ratio: 1 / 1;
}

/* Soft bloom behind the dial: the arc alone glows, but the whole tile has to sit in coloured
   light for the card to read like the mock. */
.gauge-halo {
    position: absolute;
    inset: 8%;
    border-radius: 50%;
    background: radial-gradient(circle at 50% 55%,
        rgba(var(--gauge-rgb), 0.3),
        transparent 68%);
    filter: blur(7px);
}

.gauge-svg {
    position: relative;
    width: 100%;
    height: 100%;
    /* Start the arc at twelve o'clock instead of three. */
    transform: rotate(-90deg);
}

.gauge-track {
    fill: none;
    stroke: var(--gauge-track);
    stroke-width: 10;
}

.gauge-arc {
    fill: none;
    stroke: var(--gauge-color);
    stroke-width: 10;
    stroke-linecap: round;
    stroke-dashoffset: var(--gauge-to);
    filter: drop-shadow(0 0 6px rgba(var(--gauge-rgb), 0.55));
    animation: gauge-fill 1100ms cubic-bezier(0.4, 0, 0.2, 1) backwards;
    transition: filter 300ms ease;
}

.gauge-value {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: clamp(17px, 1.55vw, 24px);
    font-weight: 700;
    letter-spacing: -0.02em;
    font-variant-numeric: tabular-nums;
    color: var(--rahat-text-bright);
    text-shadow: 0 1px 12px rgba(0, 0, 0, 0.55);
}

.gauge-unit {
    font-size: 0.68em;
    font-weight: 600;
    margin-left: 1px;
    color: var(--rahat-text);
}

.gauge-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    max-width: 100%;
    padding: 4px 9px;
    border-radius: 999px;
    border: 1px solid rgba(var(--gauge-rgb), 0.42);
    background: linear-gradient(180deg,
        rgba(var(--gauge-rgb), 0.17),
        rgba(var(--gauge-rgb), 0.06));
}

.gauge-icon {
    flex: 0 0 auto;
    width: 13px;
    height: 13px;
    fill: none;
    stroke: var(--gauge-color);
    stroke-width: 1.5;
    stroke-linecap: round;
    stroke-linejoin: round;
}

.gauge-label {
    font-size: 9.5px;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    color: var(--rahat-text-bright);
}

.gauge:hover .gauge-arc {
    filter: drop-shadow(0 0 10px rgba(var(--gauge-rgb), 0.85));
}

html.light .gauge {
    --gauge-track: rgba(164, 22, 26, 0.18);
}

html.light .gauge--bad {
    --gauge-color: #c8102c;
    --gauge-rgb: 200, 16, 44;
}

html.light .gauge-value {
    text-shadow: none;
}

@keyframes gauge-fill {
    from {
        stroke-dashoffset: var(--gauge-from);
    }
}

@media (prefers-reduced-motion: reduce) {
    .gauge-arc {
        animation: none;
    }
}
</style>
