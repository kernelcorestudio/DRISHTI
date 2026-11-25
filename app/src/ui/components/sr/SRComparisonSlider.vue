<!--
    RAHAT + NETRA - Super-Resolution Interactive Comparison Slider
-->

<template>
    <div class="sr-slider-container"
         ref="container"
         @mousemove="onMouseMove"
         @touchmove="onTouchMove"
         @mousedown="onMouseDown"
         @mouseup="onMouseUp"
         @mouseleave="onMouseUp">
        <!-- Low-Res (Left Background) -->
        <div class="sr-slide-layer sr-slide-layer--lr">
            <img :src="lrImage" :alt="lrLabel" class="sr-image" />
            <div class="sr-label sr-label--lr">{{ lrLabel }}</div>
        </div>

        <!-- Super-Resolved (Right Foreground, clipped by slider position) -->
        <div class="sr-slide-layer sr-slide-layer--sr"
             :style="{ clipPath: `inset(0 0 0 ${sliderPos}%)` }">
            <img :src="srImage" :alt="srLabel" class="sr-image" />
            <div class="sr-label sr-label--sr">{{ srLabel }}</div>
        </div>

        <!-- Divider Bar & Handle -->
        <div class="sr-divider" :style="{ left: `${sliderPos}%` }">
            <div class="sr-handle">
                <v-icon small color="white">mdi-code-tags</v-icon>
            </div>
        </div>
    </div>
</template>

<script lang="ts">
import { Component, Prop, Vue } from "vue-property-decorator";

@Component
export default class SRComparisonSlider extends Vue {
    @Prop({ required: true })
    public lrImage!: string;

    @Prop({ required: true })
    public srImage!: string;

    @Prop({ default: "Sentinel-2 (10m LR)" })
    public lrLabel!: string;

    @Prop({ default: "Super-Resolved (2.5m SR)" })
    public srLabel!: string;

    private sliderPos = 50;
    private isDragging = false;

    private onMouseDown() {
        this.isDragging = true;
    }

    private onMouseUp() {
        this.isDragging = false;
    }

    private onMouseMove(e: MouseEvent) {
        if (!this.isDragging) return;
        this.updatePos(e.clientX);
    }

    private onTouchMove(e: TouchEvent) {
        if (e.touches.length > 0) {
            this.updatePos(e.touches[0].clientX);
        }
    }

    private updatePos(clientX: number) {
        const container = this.$refs.container as HTMLElement;
        if (!container) return;
        const rect = container.getBoundingClientRect();
        const offsetX = clientX - rect.left;
        const pct = Math.max(0, Math.min(100, (offsetX / rect.width) * 100));
        this.sliderPos = Math.round(pct);
    }
}
</script>

<style scoped lang="scss">
.sr-slider-container {
    position: relative;
    width: 100%;
    aspect-ratio: 1 / 1;
    max-height: 540px;
    margin: 0 auto;
    border-radius: 8px;
    overflow: hidden;
    background: #080808;
    border: 1px solid rgba(255, 255, 255, 0.1);
    user-select: none;
    cursor: col-resize;
}

.sr-slide-layer {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;

    .sr-image {
        width: 100%;
        height: 100%;
        object-fit: contain;
        display: block;
        image-rendering: auto;
    }
}

.sr-slide-layer--lr .sr-image {
    image-rendering: pixelated;
}

.sr-label {
    position: absolute;
    top: 12px;
    padding: 4px 10px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    backdrop-filter: blur(8px);
    pointer-events: none;
}

.sr-label--lr {
    left: 12px;
    background: rgba(0, 0, 0, 0.75);
    color: #fbb931;
    border: 1px solid rgba(251, 185, 49, 0.3);
}

.sr-label--sr {
    right: 12px;
    background: rgba(0, 0, 0, 0.75);
    color: #34d399;
    border: 1px solid rgba(52, 211, 153, 0.3);
}

.sr-divider {
    position: absolute;
    top: 0;
    bottom: 0;
    width: 2px;
    background: #e0424e;
    box-shadow: 0 0 10px rgba(224, 66, 78, 0.8);
    transform: translateX(-50%);
    pointer-events: none;
    z-index: 10;
}

.sr-handle {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: #a4161a;
    border: 2px solid #ffffff;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.6);
    display: flex;
    align-items: center;
    justify-content: center;
}
</style>
