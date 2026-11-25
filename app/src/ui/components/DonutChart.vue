<!--
    DISASTER RESPONSE APP
    Copyright (c) 2021 SilentByte <https://silentbyte.com/>
-->

<template>
    <div class="gdonut">
        <div class="gdonut-head">
            <span class="gdonut-badge">
                <span class="badge-dot" />
                {{ badge }}
            </span>
        </div>

        <div class="gdonut-plot">
            <svg :viewBox="`0 0 ${VIEW_W} ${VIEW_H}`" class="gdonut-svg">
                <defs>
                    <linearGradient v-for="(arc, index) in arcs"
                                    :id="gradientId(index)"
                                    :key="'grad' + index"
                                    x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" :stop-color="arc.light" />
                        <stop offset="48%" :stop-color="arc.color" />
                        <stop offset="100%" :stop-color="arc.deep" />
                    </linearGradient>
                </defs>

                <g v-for="(arc, index) in arcs" :key="'lead' + index"
                   class="gdonut-lead"
                   :class="{'is-active': index === hover}">
                    <polyline :points="arc.leader" :stroke="arc.color" fill="none" stroke-width="1" />
                    <circle :cx="arc.dot.x" :cy="arc.dot.y" r="2.2" :fill="arc.color" />
                </g>

                <g class="gdonut-disc">
                    <path class="gdonut-base" :d="ringBase" />

                    <!-- Every side wall is painted before any top face. Otherwise a slice
                         drawn later lets its wall climb over its neighbour's surface. -->
                    <g v-for="(arc, index) in arcs"
                       :key="'wall' + index"
                       class="gdonut-wall"
                       :style="sectorStyle(arc, index)"
                       @mouseenter="hover = index"
                       @mouseleave="hover = -1">
                        <path v-if="arc.wallPath" :d="arc.wallPath" :fill="arc.wall" />

                        <line v-for="(rib, ribIndex) in arc.ribs"
                              :key="'rib' + ribIndex"
                              :x1="rib.x1" :y1="rib.y1" :x2="rib.x2" :y2="rib.y2"
                              stroke="rgba(0, 0, 0, 0.34)" stroke-width="1" />
                    </g>

                    <g v-for="(arc, index) in arcs"
                       :key="'arc' + index"
                       class="gdonut-sector"
                       :class="{'is-active': index === hover, 'is-muted': hover >= 0 && index !== hover}"
                       :style="sectorStyle(arc, index)"
                       @mouseenter="hover = index"
                       @mouseleave="hover = -1">
                        <path :d="arc.path" :fill="gradientRef(index)" />

                        <line v-for="(step, lineIndex) in arc.hatch"
                              :key="'hatch' + lineIndex"
                              :x1="step.x1" :y1="step.y1" :x2="step.x2" :y2="step.y2"
                              stroke="rgba(255, 255, 255, 0.16)" stroke-width="1" />

                        <path :d="arc.path" class="gdonut-edge"
                              fill="none" stroke="rgba(255, 255, 255, 0.24)" stroke-width="0.9" />

                        <text v-if="arc.showShare"
                              :x="arc.shareX" :y="arc.shareY"
                              text-anchor="middle"
                              class="gdonut-share">{{ arc.share }}</text>
                    </g>
                </g>

                <g v-for="(arc, index) in arcs" :key="'label' + index"
                   class="gdonut-labels"
                   :class="{'is-active': index === hover}">
                    <text :x="arc.labelX" :y="arc.labelY"
                          :text-anchor="arc.anchor"
                          class="gdonut-code">{{ arc.code }}</text>
                    <text :x="arc.labelX" :y="arc.labelY + 13"
                          :text-anchor="arc.anchor"
                          class="gdonut-amount">{{ arc.value }} ({{ arc.share }})</text>
                </g>
            </svg>
        </div>

        <!--
            The hint and the detail are two states of one well, so they share a single slot that is
            always tall enough for the detail. Without that the card would grow by the height of the
            metrics row on the first hover and pull on whatever card sits beside it.
        -->
        <div class="gdonut-foot">
            <div v-if="active" class="gdonut-detail" :style="{borderColor: active.edgeColor}">
                <div class="detail-head">
                    <span class="detail-dot" :style="{backgroundColor: active.color}" />
                    <span class="detail-name">{{ active.title }}</span>
                    <span class="detail-code" :style="{color: active.color, borderColor: active.edgeColor}">
                        {{ active.code }}
                    </span>
                </div>

                <div class="detail-metrics">
                    <span class="metric">
                        {{ caption }}: <b>{{ active.value }}</b>
                    </span>
                    <span class="metric">
                        share:
                        <b :style="{color: active.color}">{{ active.share }}</b>
                        of total
                    </span>
                    <span class="metric">
                        total: <b>{{ total }}</b>
                    </span>
                </div>
            </div>

            <div v-else class="gdonut-hint">
                <span class="hint-dot" />
                <span>Hover or tap a segment to inspect damage telemetry</span>
            </div>
        </div>

        <!-- A legend, not a control: the slices are the only thing that answers the pointer. -->
        <div class="gdonut-pills">
            <div v-for="arc in arcs"
                 :key="`pill-${arc.code}`"
                 class="gdonut-pill">
                <span class="pill-dot" :style="{backgroundColor: arc.color}" />
                <span class="pill-code">{{ arc.code }}</span>
                <span class="pill-share">{{ arc.share }}</span>
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

import { IChartSegment } from "@/models";

interface IPoint {
    x: number;
    y: number;
}

interface IHatch {
    x1: number;
    y1: number;
    x2: number;
    y2: number;
}

interface IArc extends IChartSegment {
    title: string;
    code: string;
    share: string;
    path: string;
    wallPath: string;
    light: string;
    deep: string;
    wall: string;
    edgeColor: string;
    leader: string;
    dot: IPoint;
    hatch: IHatch[];
    ribs: IHatch[];
    shareX: number;
    shareY: number;
    showShare: boolean;
    labelX: number;
    labelY: number;
    anchor: string;
    popX: number;
    popY: number;
}

// Geometry in viewBox units; the svg scales to whatever width the card gives it.
const VIEW_W = 480;
const VIEW_H = 272;
const CENTER_X = 240;
const CENTER_Y = 138;
const OUTER_R = 96;
// The reference ring is chunky: the hole is only about a third of the outer radius.
const INNER_R = 36;
// The reference disc is seen from above at an angle, so every circle projects to an
// ellipse: vertical radii are squeezed by this factor.
const TILT = 0.72;
const OUTER_RY = OUTER_R * TILT;
const INNER_RY = INNER_R * TILT;
// Height of the side wall: the rim of the near half is repeated this many units lower.
const DEPTH = 13;
const POP = 9;
// Just wide enough to read as a cut between two slices. A wider gap opens a notch at the rim
// (the radial cut runs out past the silhouette on the near side), which is what made the disc
// look collapsed at every seam.
const GAP_DEG = 0.9;

// A segment narrower than this cannot hold its percentage without crowding the rim.
const MIN_SHARE_SPAN = 15;

// Gradients need unique ids when more than one donut is mounted; a counter is simpler and
// safer than reaching into Vue's internal _uid.
let instanceSequence = 0;

/** Point on the tilted ring; angle is measured clockwise from 12 o'clock. */
function pointAt(angle: number, radius: number): IPoint {
    const rad = ((angle - 90) * Math.PI) / 180;
    return {
        x: CENTER_X + radius * Math.cos(rad),
        y: CENTER_Y + radius * TILT * Math.sin(rad),
    };
}

/** Annular sector between two angles, drawn clockwise on the tilted plane. */
function sectorPath(start: number, end: number): string {
    const outerStart = pointAt(start, OUTER_R);
    const outerEnd = pointAt(end, OUTER_R);
    const innerEnd = pointAt(end, INNER_R);
    const innerStart = pointAt(start, INNER_R);
    const large = end - start > 180 ? 1 : 0;

    return [
        `M ${outerStart.x} ${outerStart.y}`,
        `A ${OUTER_R} ${OUTER_RY} 0 ${large} 1 ${outerEnd.x} ${outerEnd.y}`,
        `L ${innerEnd.x} ${innerEnd.y}`,
        `A ${INNER_R} ${INNER_RY} 0 ${large} 0 ${innerStart.x} ${innerStart.y}`,
        "Z",
    ].join(" ");
}

/** Radial ribs that give the ring its corrugated, physical look. */
function hatchLines(start: number, end: number): IHatch[] {
    const lines: IHatch[] = [];
    const span = end - start;
    const segments = Math.max(2, Math.round(span / 3.4));

    for(let index = 0; index <= segments; index += 1) {
        const angle = start + (span * index) / segments;
        const from = pointAt(angle, INNER_R + 3);
        const to = pointAt(angle, OUTER_R - 3);

        lines.push({x1: from.x, y1: from.y, x2: to.x, y2: to.y});
    }

    return lines;
}

/**
 * The complete ring, hairline gaps included. It sits under the slices and shows through their
 * gaps as the separator, which is what keeps the outer silhouette closed: a gap that runs all the
 * way to the rim would cut a notch out of the disc at every seam.
 */
function ringPath(): string {
    const outerTop = pointAt(0, OUTER_R);
    const outerBottom = pointAt(180, OUTER_R);
    const innerTop = pointAt(0, INNER_R);
    const innerBottom = pointAt(180, INNER_R);

    return [
        `M ${outerTop.x} ${outerTop.y}`,
        `A ${OUTER_R} ${OUTER_RY} 0 0 1 ${outerBottom.x} ${outerBottom.y}`,
        `A ${OUTER_R} ${OUTER_RY} 0 0 1 ${outerTop.x} ${outerTop.y} Z`,
        `M ${innerTop.x} ${innerTop.y}`,
        `A ${INNER_R} ${INNER_RY} 0 0 0 ${innerBottom.x} ${innerBottom.y}`,
        `A ${INNER_R} ${INNER_RY} 0 0 0 ${innerTop.x} ${innerTop.y} Z`,
    ].join(" ");
}

const RING_BASE = ringPath();

/**
 * The extruded side of one slice: only the half of the rim that faces the viewer has a wall, and
 * it is the rim itself plus the same arc pushed down by DEPTH. Building it as one band (instead of
 * stacking translated copies of the whole sector) keeps the silhouette closed at the seam between
 * two slices, where two copies used to leave a corner of the card showing through.
 */
function wallBand(start: number, end: number): string {
    // 90 deg is the right of the disc and 270 deg the left, so this is the half of the rim that
    // sits below the tilt line, facing the viewer. The far half has no visible side.
    const from = Math.max(start, 90);
    const to = Math.min(end, 270);
    if(to - from < 0.2) {
        return "";
    }

    const large = to - from > 180 ? 1 : 0;
    const topStart = pointAt(from, OUTER_R);
    const topEnd = pointAt(to, OUTER_R);

    return [
        `M ${topStart.x} ${topStart.y}`,
        `A ${OUTER_R} ${OUTER_RY} 0 ${large} 1 ${topEnd.x} ${topEnd.y}`,
        `L ${topEnd.x} ${topEnd.y + DEPTH}`,
        `A ${OUTER_R} ${OUTER_RY} 0 ${large} 0 ${topStart.x} ${topStart.y + DEPTH}`,
        "Z",
    ].join(" ");
}

/** Ribs on the extruded side wall. Only the half of the rim facing the viewer shows one. */
function wallRibs(start: number, end: number): IHatch[] {
    const ribs: IHatch[] = [];
    const span = end - start;
    const segments = Math.max(2, Math.round(span / 2.6));

    for(let index = 0; index <= segments; index += 1) {
        const angle = start + (span * index) / segments;
        const rad = ((angle - 90) * Math.PI) / 180;
        if(Math.sin(rad) <= 0) {
            continue;
        }

        const edge = pointAt(angle, OUTER_R);
        ribs.push({x1: edge.x, y1: edge.y, x2: edge.x, y2: edge.y + DEPTH});
    }

    return ribs;
}

/** Mixes a #rrggbb colour towards white (positive) or black (negative). */
function shade(color: string, amount: number): string {
    const match = /^#?([0-9a-f]{6})$/i.exec(color.trim());
    if(!match) {
        return color;
    }

    const value = parseInt(match[1], 16);
    const channels = [(value >> 16) & 255, (value >> 8) & 255, value & 255];
    const target = amount >= 0 ? 255 : 0;
    const ratio = Math.abs(amount);

    return `#${channels
        .map(channel => Math.round(channel + (target - channel) * ratio))
        .map(channel => channel.toString(16).padStart(2, "0"))
        .join("")}`;
}

function capitalize(text: string): string {
    return text.charAt(0).toUpperCase() + text.slice(1);
}

@Component
export default class DonutChart extends Vue {
    @Prop({type: Array, required: true})
    private readonly segments!: IChartSegment[];

    @Prop({type: String, default: "buildings"})
    private readonly caption!: string;

    @Prop({type: String, default: "severity"})
    private readonly badge!: string;

    private hover = -1;

    private readonly instanceId = ++instanceSequence;

    private readonly VIEW_W = VIEW_W;

    private readonly VIEW_H = VIEW_H;

    private readonly ringBase = RING_BASE;

    private get total(): number {
        return this.segments.reduce((sum, segment) => sum + segment.value, 0);
    }

    private get active(): IArc | null {
        return this.hover >= 0 && this.hover < this.arcs.length ? this.arcs[this.hover] : null;
    }

    private get arcs(): IArc[] {
        const total = this.total;
        if(total <= 0) {
            return [];
        }

        const values = this.segments.filter(segment => segment.value > 0);
        let cursor = 0;

        return values.map(segment => {
            const span = (segment.value / total) * 360;
            const start = cursor;
            const end = cursor + span;
            cursor = end;

            const mid = (start + end) / 2;
            const midRad = ((mid - 90) * Math.PI) / 180;
            const outward = Math.cos(midRad) >= 0 ? 1 : -1;
            const elbow = pointAt(mid, OUTER_R + 13);
            const knee = {x: elbow.x + outward * 20, y: elbow.y};
            const sharePoint = pointAt(mid, (OUTER_R + INNER_R) / 2);

            return {
                ...segment,
                title: capitalize(segment.label),
                code: segment.label.slice(0, 3).toUpperCase(),
                share: `${Math.round((segment.value / total) * 100)}%`,
                path: sectorPath(start + GAP_DEG, end - GAP_DEG),
                // The wall follows the rim itself, so two neighbouring walls meet on the
                // boundary instead of one poking out under the other's rim.
                wallPath: wallBand(start, end),
                light: shade(segment.color, 0.26),
                deep: shade(segment.color, -0.42),
                wall: shade(segment.color, -0.52),
                edgeColor: `${segment.color}66`,
                leader: [
                    `${pointAt(mid, OUTER_R + 3).x},${pointAt(mid, OUTER_R + 3).y}`,
                    `${elbow.x},${elbow.y}`,
                    `${knee.x},${knee.y}`,
                ].join(" "),
                dot: pointAt(mid, OUTER_R + 3),
                hatch: hatchLines(start + GAP_DEG, end - GAP_DEG),
                ribs: wallRibs(start, end),
                shareX: sharePoint.x,
                shareY: sharePoint.y + 5,
                showShare: span - GAP_DEG * 2 >= MIN_SHARE_SPAN,
                labelX: knee.x + outward * 7,
                labelY: knee.y + 2,
                anchor: outward > 0 ? "start" : "end",
                // The pop follows the tilted plane rather than screen space.
                popX: Math.cos(midRad) * POP,
                popY: Math.sin(midRad) * POP * TILT,
            };
        });
    }

    private gradientId(index: number): string {
        return `gdonut-grad-${this.instanceId}-${index}`;
    }

    private gradientRef(index: number): string {
        return `url(#${this.gradientId(index)})`;
    }

    private sectorStyle(arc: IArc, index: number): Record<string, string> {
        if(index !== this.hover) {
            return {transform: "translate(0px, 0px)"};
        }

        return {
            transform: `translate(${arc.popX}px, ${arc.popY}px)`,
            filter: `drop-shadow(0 0 14px ${arc.color}) drop-shadow(0 0 3px rgba(255, 255, 255, 0.5))`,
        };
    }
}
</script>

<style lang="scss" scoped>
.gdonut {
    display: block;
}

.gdonut-head {
    display: flex;
    justify-content: flex-end;
    margin-bottom: 2px;
}

.gdonut-badge {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    padding: 5px 12px;
    border: 1px solid var(--rahat-border);
    border-radius: 999px;
    background: var(--rahat-track);
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--rahat-text-dim);                                                                                                                                                                                                               
}

.badge-dot {
    width: 7px;
    height: 7px;
    border-radius: 999px;
    background: var(--rahat-yellow);
}

.gdonut-plot {
    position: relative;
}

.gdonut-svg {
    display: block;
    width: 100%;
    height: auto;
    overflow: visible;
}

.gdonut-disc {
    filter: drop-shadow(0 10px 18px rgba(0, 0, 0, 0.55));
}

/* Reads as the shadow line between two slices on both themes. */
.gdonut-base {
    fill: rgba(0, 0, 0, 0.62);
}

.gdonut-wall {
    cursor: pointer;
    transition: transform 220ms cubic-bezier(0.22, 0.61, 0.36, 1);
}

.gdonut-sector {
    cursor: pointer;
    transition: transform 220ms cubic-bezier(0.22, 0.61, 0.36, 1), filter 220ms ease;
}

/* Brightness instead of opacity: a translucent surface would let the stacked wall
   underneath show through and read as two slices colliding. */
.gdonut-sector.is-muted {
    filter: brightness(0.84) saturate(0.92);
}

/* The reference keeps the ring readable while the active slice is lit, so the rim
   brightens instead of the whole segment dimming away. */
.gdonut-sector.is-active .gdonut-edge {
    stroke: rgba(255, 255, 255, 0.82);
    stroke-width: 1.5;
}

.gdonut-share {
    fill: #ffffff;
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 0.01em;
    /* Keeps the label readable on both the dark red and the bright yellow arcs. */
    paint-order: stroke;
    stroke: rgba(0, 0, 0, 0.3);
    stroke-width: 2.2px;
    pointer-events: none;
}

.gdonut-lead {
    pointer-events: none;
    opacity: 0.45;
    transition: opacity 180ms ease;
}

.gdonut-lead.is-active {
    opacity: 1;
}

.gdonut-labels {
    pointer-events: none;
}

.gdonut-code {
    fill: var(--rahat-text-faint);
    font-size: 9.5px;
    font-weight: 600;
    letter-spacing: 0.12em;
}

.gdonut-amount {
    fill: var(--rahat-text-dim);
    font-size: 11px;
    font-variant-numeric: tabular-nums;
}

.gdonut-labels.is-active .gdonut-code {
    fill: var(--rahat-text);
}

.gdonut-labels.is-active .gdonut-amount {
    fill: var(--rahat-text);
}

/*
 * One slot for both states of the well. It is reserved at the height of the detail panel, which is
 * the taller of the two and sits at the bottom of the slot, so swapping one for the other changes no
 * geometry outside this box - otherwise the card would grow on hover and shove its neighbour along
 * with it.
 */
.gdonut-foot {
    display: flex;
    align-items: flex-end;
    margin-top: 12px;
    min-height: 68px;
}

.gdonut-foot > * {
    flex: 1 1 auto;
    margin-top: 0;
}

.gdonut-hint {
    display: flex;
    align-items: center;
    gap: 9px;
    padding: 11px 14px;
    border: 1px solid var(--rahat-border);
    border-radius: 8px;
    background: var(--rahat-track);
    font-size: 10.5px;
    letter-spacing: 0.02em;
    color: var(--rahat-text-faint);
}

.hint-dot {
    flex: 0 0 auto;
    width: 6px;
    height: 6px;
    border-radius: 999px;
    background: var(--rahat-yellow);
}

.gdonut-detail {
    padding: 10px 14px 11px;
    border: 1px solid var(--rahat-border);
    border-radius: 8px;
    background: var(--rahat-track);
}

.detail-head {
    display: flex;
    align-items: center;
    gap: 8px;
}

.detail-dot {
    width: 9px;
    height: 9px;
    border-radius: 999px;
}

.detail-name {
    font-size: 12.5px;
    font-weight: 600;
    color: var(--rahat-text);
}

.detail-code {
    margin-left: auto;
    padding: 2px 8px;
    border: 1px solid var(--rahat-border);
    border-radius: 4px;
    font-size: 9.5px;
    font-weight: 700;
    letter-spacing: 0.1em;
}

.detail-metrics {
    display: flex;
    flex-wrap: wrap;
    gap: 6px 16px;
    margin-top: 7px;
    font-size: 10.5px;
    color: var(--rahat-text-faint);
}

.metric b {
    font-weight: 600;
    font-variant-numeric: tabular-nums;
    color: var(--rahat-text-dim);
}

.gdonut-pills {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 8px;
    margin-top: 12px;
}

.gdonut-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 5px 12px;
    border: 1px solid var(--rahat-border);
    border-radius: 999px;
    background: var(--rahat-track);
    font-size: 10.5px;
    color: var(--rahat-text-dim);
}

/* White at low alpha disappears on the cream canvas, so the legend keys are drawn in their own
   colours on a neutral track; the pills carry no state of their own. */
.pill-dot {
    width: 8px;
    height: 8px;
    border-radius: 999px;
}

.pill-code {
    font-weight: 600;
    letter-spacing: 0.08em;
}

.pill-share {
    color: var(--rahat-text-faint);
    font-variant-numeric: tabular-nums;
}
</style>
