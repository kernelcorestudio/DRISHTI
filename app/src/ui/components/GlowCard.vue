<!--
    DISASTER RESPONSE APP
    Copyright (c) 2021 SilentByte <https://silentbyte.com/>
-->

<template>
    <section ref="root"
             class="glow-card"
             :class="[toneClass, {'glow-card--lit': lit}]"
             :style="{'--bento-i': String(index)}"
             @mouseenter="lit = true"
             @mouseleave="lit = false"
             @mousemove="onPointer"
             @touchstart.passive="onTouchStart"
             @touchmove.passive="onPointer"
             @focusin="lit = true"
             @focusout="onFocusOut">
        <!-- 1px edge: dim by default, then a second pass lit from the cursor. -->
        <span class="glow-edge" aria-hidden="true" />
        <span class="glow-edge-lit" aria-hidden="true" />

        <!-- Card face: the warm spotlight and the faint grid both follow the pointer. -->
        <div class="glow-face">
            <span class="glow-spot" aria-hidden="true" />
            <span class="glow-grid" aria-hidden="true" />
        </div>

        <div class="glow-content">
            <slot />
        </div>
    </section>
</template>

<!--suppress JSUnusedGlobalSymbols -->
<script lang="ts">
import {
    Component,
    Prop,
    Vue,
} from "vue-property-decorator";

/**
 * The card shell for the dashboard bento.
 *
 * Everything that tracks the pointer is pushed into CSS custom properties on the root element
 * rather than into reactive data: a mousemove that re-rendered the component tree 60 times a
 * second would make the charts stutter. Only the lit / unlit state is reactive, because it
 * changes twice per hover.
 */
@Component
export default class GlowCard extends Vue {
    /** Which palette colour the spotlight and the lit edge are drawn from. */
    @Prop({type: String, default: "deep"})
    private readonly tone!: string;

    /** Mount order, used to stagger the entrance animation. */
    @Prop({type: Number, default: 0})
    private readonly index!: number;

    private lit = false;

    private get toneClass(): string {
        return `glow-card--${this.tone}`;
    }

    private onPointer(event: MouseEvent | TouchEvent): void {
        const point = "touches" in event ? event.touches[0] : event;
        if(!point) {
            return;
        }

        this.setSpotlight(point.clientX, point.clientY);
    }

    private onTouchStart(event: TouchEvent): void {
        this.lit = true;
        this.onPointer(event);
    }

    private onFocusOut(event: FocusEvent): void {
        const next = event.relatedTarget as Node | null;
        const root = this.$refs.root as HTMLElement | undefined;

        // Tabbing between two children of the same card must not kill the highlight.
        if(!root || !next || !root.contains(next)) {
            this.lit = false;
        }
    }

    private setSpotlight(clientX: number, clientY: number): void {
        const root = this.$refs.root as HTMLElement | undefined;
        if(!root) {
            return;
        }

        const rect = root.getBoundingClientRect();
        root.style.setProperty("--mx", `${clientX - rect.left}px`);
        root.style.setProperty("--my", `${clientY - rect.top}px`);
    }
}
</script>

<style lang="scss" scoped>
.glow-card {
    /* Accent as raw "r, g, b" so it can be dropped into rgba() at any alpha. */
    --glow-rgb: 100, 13, 20;
    --glow-strength: 0.13;
    /* Grid hairlines are white on OLED and warm orange on cream. */
    --glow-grid: rgba(255, 255, 255, 0.09);

    position: relative;
    display: flex;
    min-width: 0;
    border-radius: 10px;
    isolation: isolate;
    /* Entrance settles in; `backwards` so the finished animation is not left holding `transform`,
       which would otherwise beat the hover lift on specificity. */
    animation: bento-rise 520ms cubic-bezier(0.22, 0.61, 0.36, 1) backwards;
    animation-delay: calc(var(--bento-i, 0) * 60ms);
    transition: transform 320ms cubic-bezier(0.22, 0.61, 0.36, 1);
}

.glow-card--vivid {
    --glow-rgb: 164, 22, 26;
}

.glow-card--amber {
    --glow-rgb: 208, 30, 44;
}

.glow-card--ok {
    --glow-rgb: 52, 211, 153;
    --glow-strength: 0.1;
}

.glow-card--danger {
    --glow-rgb: 251, 113, 133;
    --glow-strength: 0.1;
}

.glow-card:hover {
    transform: translateY(-2px);
}

.glow-edge {
    position: absolute;
    inset: 0;
    border-radius: inherit;
    background: var(--rahat-border);
}

.glow-edge-lit {
    position: absolute;
    inset: 0;
    border-radius: inherit;
    opacity: 0;
    background: radial-gradient(240px circle at var(--mx, 50%) var(--my, 0%),
        rgba(var(--glow-rgb), 0.9),
        rgba(var(--glow-rgb), 0.15) 45%,
        transparent 72%);
    transition: opacity 420ms ease;
    pointer-events: none;
}

.glow-face {
    position: absolute;
    inset: 1px;
    border-radius: 9px;
    overflow: hidden;
    background: var(--rahat-card);
    box-shadow: var(--rahat-shadow-soft);
}

.glow-spot {
    position: absolute;
    inset: 0;
    opacity: 0;
    background: radial-gradient(420px circle at var(--mx, 50%) var(--my, 0%),
        rgba(var(--glow-rgb), var(--glow-strength)),
        transparent 68%);
    transition: opacity 420ms ease;
}

.glow-grid {
    position: absolute;
    inset: 0;
    opacity: 0;
    background-image: linear-gradient(var(--glow-grid) 1px, transparent 1px),
        linear-gradient(90deg, var(--glow-grid) 1px, transparent 1px);
    background-size: 26px 26px;
    -webkit-mask-image: radial-gradient(220px circle at var(--mx, 50%) var(--my, 0%), black, transparent 76%);
    mask-image: radial-gradient(220px circle at var(--mx, 50%) var(--my, 0%), black, transparent 76%);
    transition: opacity 420ms ease;
}

.glow-card--lit .glow-edge-lit,
.glow-card--lit .glow-spot,
.glow-card--lit .glow-grid {
    opacity: 1;
}

.glow-content {
    position: relative;
    z-index: 1;
    display: flex;
    flex-direction: column;
    width: 100%;
    min-width: 0;
    padding: 16px 18px;
}

html.light .glow-card {
    --glow-grid: rgba(164, 22, 26, 0.18);
    --glow-strength: 0.1;
}

@keyframes bento-rise {
    from {
        opacity: 0;
        transform: translateY(10px);
    }
}

/* A pointer that never moves is the whole effect here, so there is nothing to keep when the
   visitor has asked the system for reduced motion. */
@media (prefers-reduced-motion: reduce) {
    .glow-card {
        animation: none;
        transition: none;
    }

    .glow-card:hover {
        transform: none;
    }

    .glow-spot,
    .glow-grid,
    .glow-edge-lit {
        transition: none;
    }
}
</style>
