<!--
    DISASTER RESPONSE APP
    Copyright (c) 2021 SilentByte <https://silentbyte.com/>
-->

<template>
    <div class="stat" :class="`stat--${tone}`">
        <div class="stat-top">
            <div v-if="icon" class="stat-icon">
                <v-icon small>{{ icon }}</v-icon>
            </div>

            <div class="stat-body">
                <div class="stat-label">{{ label }}</div>

                <div class="stat-value">
                    {{ value }}<span v-if="unit" class="stat-unit">{{ unit }}</span>
                </div>
            </div>
        </div>

        <div v-if="hint" class="stat-hint">{{ hint }}</div>
    </div>
</template>

<!--suppress JSUnusedGlobalSymbols -->
<script lang="ts">
import {
    Component,
    Prop,
    Vue,
} from "vue-property-decorator";

type Tone = "default" | "good" | "warn" | "bad";

@Component
export default class StatCard extends Vue {
    @Prop({type: String, required: true})
    private readonly label!: string;

    @Prop({type: [String, Number], required: true})
    private readonly value!: string | number;

    @Prop({type: String, default: ""})
    private readonly unit!: string;

    @Prop({type: String, default: ""})
    private readonly hint!: string;

    @Prop({type: String, default: "default"})
    private readonly tone!: Tone;

    /**
     * MDI name for the round glyph on the left. Optional: a page that does not pass one gets the
     * same glass surface with the label and value left-aligned, which is what the older views do.
     */
    @Prop({type: String, default: ""})
    private readonly icon!: string;
}
</script>

<style lang="scss" scoped>
/*
 * Tones are carried as raw RGB triplets rather than finished colours. The glass treatment needs
 * the same hue at six different alphas (wash, border, icon fill, icon ring, glow) and rgba() cannot
 * take a hex token, so the triplet is what makes one hue reusable everywhere.
 */
.stat {
    --stat-rgb: 168, 158, 162;
    --stat-accent: var(--rahat-text-dim);

    position: relative;
    min-width: 0;
    padding: 14px 16px 15px;
    border-radius: 14px;
    overflow: hidden;

    /* Tint, then a top sheen, then the translucent panel - the order is what sells the glass. */
    background:
        radial-gradient(
            125% 125% at 0% 0%,
            rgba(var(--stat-rgb), 0.2) 0%,
            rgba(var(--stat-rgb), 0.05) 48%,
            rgba(var(--stat-rgb), 0) 74%),
        linear-gradient(180deg, rgba(255, 255, 255, 0.06) 0%, rgba(255, 255, 255, 0) 62%),
        var(--rahat-glass);
    backdrop-filter: blur(16px) saturate(125%);
    border: 1px solid rgba(var(--stat-rgb), 0.26);
    box-shadow:
        0 12px 28px rgba(0, 0, 0, 0.32),
        inset 0 1px 0 rgba(255, 255, 255, 0.08);
    transition:
        transform 180ms ease,
        border-color 180ms ease,
        box-shadow 180ms ease;
}

/*
 * Hover is a second tint layer rather than a change to the base gradient: fading one opacity is far
 * cheaper than repainting a multi-stop background on every card in the row.
 */
.stat::before {
    content: "";
    position: absolute;
    inset: 0;
    border-radius: inherit;
    pointer-events: none;
    background: radial-gradient(
        125% 125% at 0% 0%,
        rgba(var(--stat-rgb), 0.34) 0%,
        rgba(var(--stat-rgb), 0.08) 48%,
        rgba(var(--stat-rgb), 0) 74%);
    opacity: 0;
    transition: opacity 180ms ease;
}

html.light .stat {
    --stat-rgb: 122, 92, 98;

    box-shadow:
        0 12px 28px rgba(74, 10, 16, 0.1),
        inset 0 1px 0 rgba(255, 255, 255, 0.7);
}

/*
 * Lift, brighter ring, deeper shadow, hotter tint - all on one curve, so a row of six cards reacts
 * as a single surface. The lift is only 2px and the cursor stays default: these cards are read-only,
 * and a pointer cursor would promise a click that does not exist.
 */
.stat:hover {
    transform: translateY(-2px);
    border-color: rgba(var(--stat-rgb), 0.5);
    box-shadow:
        0 18px 36px rgba(0, 0, 0, 0.44),
        0 0 0 1px rgba(var(--stat-rgb), 0.16),
        inset 0 1px 0 rgba(255, 255, 255, 0.1);
}

.stat:hover::before {
    opacity: 1;
}

html.light .stat:hover {
    box-shadow:
        0 18px 36px rgba(74, 10, 16, 0.18),
        0 0 0 1px rgba(var(--stat-rgb), 0.14),
        inset 0 1px 0 rgba(255, 255, 255, 0.9);
}

.stat:hover .stat-label {
    color: var(--rahat-text);
}

.stat:hover .stat-hint {
    color: var(--rahat-text-dim);
}

.stat:hover .stat-value {
    text-shadow: 0 0 18px rgba(var(--stat-rgb), 0.45);
}

.stat:hover .stat-icon {
    transform: translateY(-1px) scale(1.06);
    border-color: rgba(var(--stat-rgb), 0.55);
    box-shadow:
        0 8px 18px rgba(0, 0, 0, 0.26),
        0 0 0 4px rgba(var(--stat-rgb), 0.12),
        inset 0 1px 0 rgba(255, 255, 255, 0.2);
}

.stat--warn {
    --stat-rgb: 251, 185, 49;
    --stat-accent: var(--rahat-warn);
}

.stat--bad {
    --stat-rgb: 251, 113, 133;
    --stat-accent: var(--rahat-danger);
}

.stat--good {
    --stat-rgb: 52, 211, 153;
    --stat-accent: var(--rahat-ok);
}

/* Deep, desaturated triplets: the neon values above read as pastel on a cream canvas. */
html.light .stat--warn {
    --stat-rgb: 180, 83, 9;
}

html.light .stat--bad {
    --stat-rgb: 190, 18, 60;
}

html.light .stat--good {
    --stat-rgb: 4, 120, 87;
}

.stat-top {
    position: relative;
    z-index: 1;
    display: flex;
    align-items: center;
    gap: 12px;
}

.stat-body {
    min-width: 0;
}

.stat-icon {
    width: 38px;
    height: 38px;
    flex: 0 0 auto;
    display: grid;
    place-items: center;
    border-radius: 50%;
    color: var(--stat-accent);
    background: radial-gradient(
        circle at 32% 26%,
        rgba(var(--stat-rgb), 0.34) 0%,
        rgba(var(--stat-rgb), 0.1) 100%);
    border: 1px solid rgba(var(--stat-rgb), 0.32);
    box-shadow:
        0 6px 14px rgba(0, 0, 0, 0.18),
        inset 0 1px 0 rgba(255, 255, 255, 0.16);
    transition:
        transform 180ms ease,
        border-color 180ms ease,
        box-shadow 180ms ease;
}

html.light .stat-icon {
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.9);
}

.stat-label {
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--rahat-text-dim);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    transition: color 180ms ease;
}

.stat-value {
    margin-top: 4px;
    font-size: 27px;
    font-weight: 700;
    line-height: 1.05;
    letter-spacing: -0.01em;
    color: var(--rahat-text);
    font-variant-numeric: tabular-nums;
}

.stat--good .stat-value {
    color: var(--rahat-ok);
}

.stat--warn .stat-value {
    color: var(--rahat-warn);
}

.stat--bad .stat-value {
    color: var(--rahat-danger);
}

.stat-unit {
    margin-left: 3px;
    font-size: 12px;
    font-weight: 500;
    color: var(--rahat-text-faint);
}

.stat-hint {
    position: relative;
    z-index: 1;
    margin-top: 10px;
    font-size: 10.5px;
    color: var(--rahat-text-faint);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    transition: color 180ms ease;
}

/* Some people feel the lift; respect that without losing the colour change. */
@media (prefers-reduced-motion: reduce) {
    .stat,
    .stat::before,
    .stat-icon,
    .stat-label,
    .stat-hint {
        transition: none;
    }

    .stat:hover,
    .stat:hover .stat-icon {
        transform: none;
    }
}
</style>
