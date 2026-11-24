<!--
    RAHAT + NETRA - Super-Resolution Mapping Workspace
    Sentinel-2 10m to 2.5m Super-Resolution with Hallucination-Aware Uncertainty USP
-->

<template>
    <div class="page">
        <!-- KPI Ribbon -->
        <div class="grid grid--kpi">
            <StatCard label="SR Engine" :value="activeModelLabel" hint="active neural model" />
            <StatCard label="Scale Factor" value="4x" unit="2.5m" hint="from 10m native" />
            <StatCard label="Trust Score" :value="trustScoreLabel" unit="%" hint="hallucination metric" />
            <StatCard label="Status" :value="statusLabel" :hint="statusHint" />
        </div>

        <!-- Satellite Acquisition & Control Card -->
        <SectionCard class="block"
                     title="Satellite Tile Acquisition & Engine Controls"
                     subtitle="fetch live Sentinel-2 L2A tile via Copernicus CDSE or choose a calibrated benchmark AOI">
            <div class="sr-controls">
                <v-row dense>
                    <v-col cols="12" md="4">
                        <v-select v-model="selectedPresetId"
                                  :items="presetItems"
                                  item-text="text"
                                  item-value="value"
                                  label="Area of Interest (AOI)"
                                  outlined dense
                                  prepend-inner-icon="mdi-map-marker-radius"
                                  hide-details
                                  class="mb-2" />
                    </v-col>

                    <v-col cols="12" md="4">
                        <v-select v-model="selectedModel"
                                  :items="modelOptions"
                                  item-text="text"
                                  item-value="value"
                                  label="SR Architecture"
                                  outlined dense
                                  prepend-inner-icon="mdi-brain"
                                  hide-details
                                  class="mb-2" />
                    </v-col>

                    <v-col cols="12" md="4" class="d-flex align-center">
                        <v-btn color="primary"
                               class="mr-2 flex-grow-1"
                               :loading="loadingTile"
                               :disabled="busy"
                               @click="onFetchTile">
                            <v-icon left small>mdi-satellite-download</v-icon>
                            Fetch Tile
                        </v-btn>

                        <v-btn color="accent"
                               class="flex-grow-1"
                               :loading="runningSR"
                               :disabled="busy || !hasLR"
                               @click="onRunSR">
                            <v-icon left small>mdi-lightning-bolt</v-icon>
                            Super-Resolve
                        </v-btn>
                    </v-col>
                </v-row>

                <!-- Advanced Options Row -->
                <v-row dense class="mt-2">
                    <v-col cols="12" md="6" class="d-flex align-center">
                        <span class="sr-control-label mr-3">MC-Dropout Uncertainty Passes:</span>
                        <v-slider v-model="mcSamples"
                                  min="4" max="16" step="2"
                                  thumb-label
                                  dense hide-details
                                  class="flex-grow-1" />
                        <span class="mono ml-2 font-weight-bold">{{ mcSamples }}x</span>
                    </v-col>

                    <v-col cols="12" md="3" class="d-flex align-center">
                        <v-switch v-model="applySharpen"
                                  label="Real-ESRGAN Edge Sharpening"
                                  dense hide-details color="accent" />
                    </v-col>

                    <v-col cols="12" md="3" class="d-flex align-center justify-end">
                        <v-btn text small color="info" :disabled="busy || !hasSR" @click="onDetectInfrastructure">
                            <v-icon left small>mdi-office-building-marker</v-icon>
                            Extract Infrastructure
                        </v-btn>
                    </v-col>
                </v-row>

                <v-alert v-if="srError"
                         dense text type="error"
                         dismissible
                         class="mt-3 mb-0"
                         @input="srError = null">
                    {{ srError }}
                </v-alert>

                <v-alert v-if="cloudWarning"
                         dense text type="warning"
                         class="mt-3 mb-0 sr-alert">
                    <v-icon small left color="warning">mdi-weather-cloudy</v-icon>
                    <strong>Cloud Shield Active:</strong> {{ cloudWarning }} ({{ cloudCoveragePct }}% cloud occlusion detected)
                </v-alert>
            </div>
        </SectionCard>

        <!-- Imagery Comparison & Hallucination Inspection -->
        <SectionCard class="block"
                     title="Satellite Imagery & Hallucination Trust Map"
                     subtitle="compare 10m Sentinel-2 input vs 2.5m super-resolved output with pixel-level epistemic uncertainty"
                     flush>
            <div class="sr-workspace-tabs">
                <v-tabs v-model="activeTab" background-color="transparent" slider-color="accent" dense>
                    <v-tab>
                        <v-icon small left>mdi-compare</v-icon>
                        Interactive Slider
                    </v-tab>
                    <v-tab>
                        <v-icon small left>mdi-view-parallel</v-icon>
                        Side-by-Side View
                    </v-tab>
                    <v-tab :disabled="!confidenceMap">
                        <v-icon small left>mdi-shield-check</v-icon>
                        Hallucination Heatmap
                    </v-tab>
                    <v-tab :disabled="!infraOverlay">
                        <v-icon small left>mdi-vector-polygon</v-icon>
                        Infrastructure Overlay
                    </v-tab>
                </v-tabs>

                <div class="sr-display-panel pa-4">
                    <!-- Tab 0: Slider -->
                    <div v-if="activeTab === 0">
                        <div v-if="hasLR && hasSR">
                            <SRComparisonSlider :lr-image="lrImage"
                                                :sr-image="srImage"
                                                lr-label="Sentinel-2 L2A (10m Native)"
                                                :sr-label="`NETRA ${selectedModel.toUpperCase()} (2.5m SR)`" />
                        </div>
                        <div v-else-if="hasLR" class="sr-single-preview">
                            <div class="sr-preview-box">
                                <img :src="lrImage" alt="Sentinel-2 Input" class="sr-image" />
                                <div class="sr-label sr-label--lr">Sentinel-2 Native 10m</div>
                            </div>
                            <div class="sr-prompt-overlay">
                                <v-btn color="accent" large @click="onRunSR" :loading="runningSR">
                                    <v-icon left>mdi-play</v-icon>
                                    Run 4x Super-Resolution
                                </v-btn>
                            </div>
                        </div>
                        <div v-else class="empty py-12">
                            <v-icon large color="dim" class="mb-2">mdi-satellite-variant</v-icon>
                            <div>Select an AOI preset above and click "Fetch Tile" to load satellite imagery</div>
                        </div>
                    </div>

                    <!-- Tab 1: Synchronized 3-Panel View -->
                    <div v-if="activeTab === 1">
                        <div v-if="hasLR">
                            <!-- Viewport Sync & Zoom Toolbar -->
                            <div class="sr-sync-toolbar d-flex align-center justify-space-between mb-3">
                                <div class="d-flex align-center">
                                    <v-icon small color="accent" class="mr-2">mdi-sync</v-icon>
                                    <span class="text-caption font-weight-bold">Synchronized 3-Panel Inspection Viewport</span>
                                    <span class="chip chip--ok ml-3" style="font-size: 10px;">Sync Active</span>
                                </div>
                                <div class="d-flex align-center">
                                    <span class="faint text-caption mr-2">Zoom:</span>
                                    <v-btn icon small class="mr-1" title="Zoom In (+)" @click="zoomIn">
                                        <v-icon small>mdi-plus</v-icon>
                                    </v-btn>
                                    <v-btn icon small class="mr-1" title="Zoom Out (-)" @click="zoomOut">
                                        <v-icon small>mdi-minus</v-icon>
                                    </v-btn>
                                    <v-btn text x-small color="accent" class="mr-2" title="Reset Zoom" @click="resetZoom">
                                        Fit
                                    </v-btn>
                                    <span class="mono font-weight-bold text-caption" style="min-width: 42px;">{{ syncZoom.toFixed(1) }}x</span>
                                </div>
                            </div>

                            <div class="sr-side-by-side sr-side-by-side--3col"
                                 @mousedown="onSyncMouseDown"
                                 @mousemove="onSyncMouseMove"
                                 @mouseup="onSyncMouseUp"
                                 @mouseleave="onSyncMouseUp"
                                 @wheel.prevent="onSyncWheel">
                                <!-- Panel 1: Input Sentinel-2 -->
                                <div class="sr-side-card">
                                    <div class="sr-card-title d-flex justify-space-between align-center">
                                        <span>Input: Sentinel-2 L2A (10m)</span>
                                        <span class="chip chip--neutral" style="font-size: 10px;">Input</span>
                                    </div>
                                    <div class="sr-img-wrapper sr-img-wrapper--pixelated sr-img-wrapper--sync"
                                         :style="{ cursor: syncZoom > 1.05 ? (isSyncPanning ? 'grabbing' : 'grab') : 'default' }">
                                        <img :src="lrImage"
                                             alt="Sentinel-2 10m Input"
                                             :style="syncTransformStyle"
                                             draggable="false" />
                                    </div>
                                    <div class="sr-meta">Resolution: 10m/px • Bands: B04, B03, B02, B08</div>
                                </div>

                                <!-- Panel 2: Super-Resolved (2.5m) -->
                                <div class="sr-side-card">
                                    <div class="sr-card-title d-flex justify-space-between align-center">
                                        <span>Output: {{ selectedModel.toUpperCase() }} (2.5m SR)</span>
                                        <span class="chip chip--ok" style="font-size: 10px;">4x Neural</span>
                                    </div>
                                    <div class="sr-img-wrapper sr-img-wrapper--sync"
                                         :style="{ cursor: syncZoom > 1.05 ? (isSyncPanning ? 'grabbing' : 'grab') : 'default' }">
                                        <img v-if="hasSR"
                                             :src="srImage"
                                             alt="2.5m Super-Resolved"
                                             :style="syncTransformStyle"
                                             draggable="false" />
                                        <div v-else class="empty py-12">Pending inference</div>
                                    </div>
                                    <div class="sr-meta">Resolution: 2.5m/px • Model: {{ selectedModel.toUpperCase() }} (&lt;4m GSD)</div>
                                </div>

                                <!-- Panel 3: Reference Ground Truth HR (1.5m) -->
                                <div class="sr-side-card">
                                    <div class="sr-card-title d-flex justify-space-between align-center">
                                        <span>Reference: {{ referenceTierLabel || 'Ground Truth HR (1.5m)' }}</span>
                                        <span :class="['chip', hrImage ? 'chip--ok' : 'chip--neutral']" style="font-size: 10px;">
                                            {{ hrImage ? 'SPOT 1.5m' : 'Independent' }}
                                        </span>
                                    </div>
                                    <div class="sr-img-wrapper sr-img-wrapper--sync"
                                         :style="{ cursor: syncZoom > 1.05 ? (isSyncPanning ? 'grabbing' : 'grab') : 'default' }">
                                        <img v-if="hrImage"
                                             :src="hrImage"
                                             alt="1.5m Reference Ground Truth"
                                             :style="syncTransformStyle"
                                             draggable="false" />
                                        <div v-else class="empty py-12">
                                            <v-icon small color="dim" class="mb-1">mdi-image-off-outline</v-icon>
                                            <div class="text-caption">Independent AOI (No Paired Reference)</div>
                                        </div>
                                    </div>
                                    <div class="sr-meta">Resolution: 1.5m/px • Paired SPOT 6/7 Optical Reference</div>
                                </div>
                            </div>
                        </div>
                        <div v-else class="empty py-12">No satellite imagery loaded</div>
                    </div>

                    <!-- Tab 2: Hallucination Heatmap -->
                    <div v-if="activeTab === 2">
                        <div v-if="confidenceMap" class="sr-side-by-side">
                            <div class="sr-side-card">
                                <div class="sr-card-title">Super-Resolved Imagery</div>
                                <div class="sr-img-wrapper">
                                    <img :src="srImage" alt="SR Imagery" />
                                </div>
                            </div>

                            <div class="sr-side-card">
                                <div class="sr-card-title">Epistemic Confidence & Trust Heatmap</div>
                                <div class="sr-img-wrapper">
                                    <img :src="confidenceMap" alt="Confidence Heatmap" />
                                </div>
                                <div class="sr-trust-legend mt-2">
                                    <div class="sr-legend-bar" />
                                    <div class="d-flex justify-space-between faint text-caption">
                                        <span>0% Hallucination Risk</span>
                                        <span>50%</span>
                                        <span>100% High Scientific Trust</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Tab 3: Infrastructure Overlay -->
                    <div v-if="activeTab === 3">
                        <div v-if="infraOverlay" class="sr-side-by-side">
                            <div class="sr-side-card">
                                <div class="sr-card-title">Extracted Vector Overlays (SR)</div>
                                <div class="sr-img-wrapper">
                                    <img :src="infraOverlay" alt="Infrastructure Overlay" />
                                </div>
                            </div>

                            <div class="sr-side-card pa-4">
                                <div class="sr-card-title mb-3">Extracted Infrastructure Metrics</div>
                                <div class="infra-stat-row">
                                    <span class="faint">Detected Buildings:</span>
                                    <span class="mono font-weight-bold text-h6">{{ infraBuildings }}</span>
                                </div>
                                <div class="infra-stat-row">
                                    <span class="faint">Road Network Segments:</span>
                                    <span class="mono font-weight-bold">{{ infraRoads }}</span>
                                </div>
                                <div class="infra-stat-row">
                                    <span class="faint">Estimated Road Length:</span>
                                    <span class="mono font-weight-bold">{{ infraRoadLength }} km</span>
                                </div>
                                <div class="infra-stat-row">
                                    <span class="faint">Built-up Surface Area:</span>
                                    <span class="mono font-weight-bold">{{ infraBuiltArea }} km²</span>
                                </div>
                                <v-divider class="my-3" />
                                <div class="text-caption faint">
                                    Infrastructure detected from 2.5m super-resolved multi-band raster with NDWI water masking.
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </SectionCard>

        <!-- Scientific Validation & Blockchain Provenance -->
        <v-row dense class="mt-4">
            <v-col cols="12" md="6">
                <SectionCard title="Quantitative Quality Benchmarks"
                             subtitle="real reference-based and no-reference image quality metrics">
                    <div class="pa-4">
                        <v-row dense>
                            <v-col cols="4">
                                <div class="metric-box">
                                    <div class="metric-val mono">{{ metricPSNR }}</div>
                                    <div class="metric-label">PSNR (dB)</div>
                                    <div class="metric-sub">Peak SNR (Higher is better)</div>
                                </div>
                            </v-col>
                            <v-col cols="4">
                                <div class="metric-box">
                                    <div class="metric-val mono">{{ metricSSIM }}</div>
                                    <div class="metric-label">SSIM</div>
                                    <div class="metric-sub">Structural Similarity</div>
                                </div>
                            </v-col>
                            <v-col cols="4">
                                <div class="metric-box">
                                    <div class="metric-val mono">{{ metricSAM }}</div>
                                    <div class="metric-label">SAM (rad)</div>
                                    <div class="metric-sub">Spectral Angle Mapper</div>
                                </div>
                            </v-col>
                        </v-row>

                        <v-divider class="my-3" />

                        <v-row dense>
                            <v-col cols="6">
                                <div class="metric-box">
                                    <div class="metric-val mono">{{ metricNIQE }}</div>
                                    <div class="metric-label">NIQE</div>
                                    <div class="metric-sub">Natural Image Quality (Lower is better)</div>
                                </div>
                            </v-col>
                            <v-col cols="6">
                                <div class="metric-box">
                                    <div class="metric-val mono">{{ metricBRISQUE }}</div>
                                    <div class="metric-label">BRISQUE</div>
                                    <div class="metric-sub">Blind Reference Score (&lt;35 ideal)</div>
                                </div>
                            </v-col>
                        </v-row>
                    </div>
                </SectionCard>
            </v-col>

            <v-col cols="12" md="6">
                <SectionCard title="NETRA Blockchain Provenance"
                             subtitle="cryptographic SHA-256 fingerprint & Polygon Amoy testnet ledger">
                    <div class="pa-4">
                        <div class="blockchain-status-row mb-3">
                            <span class="faint">Network:</span>
                            <span class="chip chip--ok">Polygon Amoy Testnet (80002)</span>
                        </div>

                        <div class="blockchain-status-row mb-3">
                            <span class="faint">Tile SHA-256:</span>
                            <span class="mono text-caption text-truncate">{{ tileHashLabel }}</span>
                        </div>

                        <div class="blockchain-status-row mb-3">
                            <span class="faint">Ledger Status:</span>
                            <span class="chip" :class="`chip--${blockchainTone}`">{{ blockchainStatusLabel }}</span>
                        </div>

                        <div v-if="txHash" class="blockchain-status-row mb-3">
                            <span class="faint">Tx Hash:</span>
                            <a :href="explorerUrl" target="_blank" class="mono text-caption text-truncate accent--text">
                                {{ txHash }}
                            </a>
                        </div>

                        <v-btn color="primary"
                               outlined small
                               class="mt-2 mr-2"
                               :disabled="busy || !hasSR"
                               :loading="registeringChain"
                               @click="onRegisterOnChain">
                            <v-icon left small>mdi-cube-outline</v-icon>
                            Verify & Anchor On-Chain
                        </v-btn>

                        <v-btn outlined small
                               class="mt-2"
                               :disabled="busy || !hasSR"
                               :href="geotiffDownloadUrl"
                               target="_blank">
                            <v-icon left small>mdi-download</v-icon>
                            GeoTIFF
                        </v-btn>
                    </div>
                </SectionCard>
            </v-col>
        </v-row>
    </div>
</template>

<script lang="ts">
/* eslint-disable no-console */
import { Component, Vue } from "vue-property-decorator";

import SectionCard from "@/ui/components/SectionCard.vue";
import StatCard from "@/ui/components/StatCard.vue";
import SRComparisonSlider from "@/ui/components/sr/SRComparisonSlider.vue";

import {
    fetchSRPresets,
    fetchSRTile,
    runSuperResolution,
    detectInfrastructure,
    registerTileOnChain,
    srDownloadUrl,
} from "@/modules/api";

import { ISRPreset, ISRResult, IInfrastructureResult } from "@/models";

@Component({
    components: {
        SectionCard,
        StatCard,
        SRComparisonSlider,
    },
})
export default class SuperResolutionView extends Vue {
    private presets: ISRPreset[] = [];
    private selectedPresetId = "punjab_agri";
    private selectedModel = "hat";
    private mcSamples = 8;
    private applySharpen = false;

    private loadingTile = false;
    private runningSR = false;
    private registeringChain = false;
    private detectingInfra = false;
    private activeTab = 0;
    private srError: string | null = null;

    private lrImage = "";
    private srImage = "";
    private hrImage = "";
    private referenceTierLabel = "";
    private confidenceMap = "";
    private cloudMask = "";
    private infraOverlay = "";

    private syncZoom = 1.0;
    private syncPanX = 0;
    private syncPanY = 0;
    private isSyncPanning = false;
    private syncDragStartX = 0;
    private syncDragStartY = 0;

    private meanConfidence: number | null = null;
    private hallucinationPct: number | null = null;
    private cloudCoveragePct = 0.0;
    private cloudWarning: string | null = null;
    private inferenceTimeMs = 0;

    private infraBuildings = 0;
    private infraRoads = 0;
    private infraRoadLength = 0;
    private infraBuiltArea = 0;

    private metricPSNR = "--";
    private metricSSIM = "--";
    private metricSAM = "--";
    private metricNIQE = "--";
    private metricBRISQUE = "--";

    private tileHash = "";
    private txHash = "";
    private explorerUrl = "https://amoy.polygonscan.com";
    private chainStatus = "pending";

    private readonly modelOptions = [
        { text: "HAT (WorldStrat x4 ONNX - Production)", value: "hat" },
        { text: "CARN (Fast Mobile SR x4)", value: "carn" },
        { text: "SRM-Net (Residual SE Attention)", value: "srm_net" },
        { text: "Real-ESRGAN (Generative Prior)", value: "realesrgan" },
        { text: "SwinIR (Swin Transformer)", value: "swinir" },
    ];

    private get geotiffDownloadUrl(): string {
        return srDownloadUrl("geotiff");
    }

    private get presetItems() {
        if (this.presets.length > 0) {
            return this.presets.map(p => ({ text: p.name || p.title || p.id, value: p.id }));
        }
        return [
            { text: "Punjab Agricultural Farmland (SPOT 1.5m Reference)", value: "punjab_agri" },
            { text: "Varanasi River & Ghats (Water Body Reference)", value: "varanasi_river" },
            { text: "Delhi NCR Urban Grid (Built-up Reference)", value: "delhi_ncr" },
        ];
    }

    private get busy(): boolean {
        return this.loadingTile || this.runningSR || this.registeringChain || this.detectingInfra;
    }

    private get hasLR(): boolean {
        return !!this.lrImage;
    }

    private get hasSR(): boolean {
        return !!this.srImage;
    }

    private get activeModelLabel(): string {
        return this.selectedModel.toUpperCase();
    }

    private get trustScoreLabel(): string {
        return this.meanConfidence !== null ? `${Math.round(this.meanConfidence * 100)}` : "--";
    }

    private get statusLabel(): string {
        if (this.runningSR) return "inferring";
        if (this.loadingTile) return "fetching";
        if (this.detectingInfra) return "extracting";
        if (this.hasSR) return "complete";
        if (this.hasLR) return "ready";
        return "idle";
    }

    private get statusHint(): string {
        if (this.hasSR) return `${this.inferenceTimeMs}ms execution time`;
        if (this.hasLR) return "tile loaded in memory";
        return "awaiting tile selection";
    }

    private get tileHashLabel(): string {
        return this.tileHash || "Pending SR inference";
    }

    private get blockchainStatusLabel(): string {
        if (this.chainStatus === "verified") return "On-Chain Verified";
        if (this.chainStatus === "simulated") return "Simulated Ledger";
        return "Not Registered";
    }

    private get blockchainTone(): string {
        if (this.chainStatus === "verified") return "ok";
        if (this.chainStatus === "simulated") return "warn";
        return "neutral";
    }

    private get syncTransformStyle(): Record<string, string> {
        return {
            transform: `translate(${this.syncPanX}px, ${this.syncPanY}px) scale(${this.syncZoom})`,
            transformOrigin: "center center",
            transition: this.isSyncPanning ? "none" : "transform 0.12s ease-out",
        };
    }

    private zoomIn(): void {
        this.syncZoom = Math.min(6.0, +(this.syncZoom * 1.35).toFixed(2));
    }

    private zoomOut(): void {
        this.syncZoom = Math.max(1.0, +(this.syncZoom * 0.74).toFixed(2));
        if (this.syncZoom <= 1.05) {
            this.syncPanX = 0;
            this.syncPanY = 0;
        }
    }

    private resetZoom(): void {
        this.syncZoom = 1.0;
        this.syncPanX = 0;
        this.syncPanY = 0;
    }

    private onSyncWheel(e: WheelEvent): void {
        const delta = e.deltaY < 0 ? 1.2 : 0.83;
        const newZoom = Math.max(1.0, Math.min(6.0, +(this.syncZoom * delta).toFixed(2)));
        this.syncZoom = newZoom;
        if (this.syncZoom <= 1.05) {
            this.syncPanX = 0;
            this.syncPanY = 0;
        }
    }

    private onSyncMouseDown(e: MouseEvent): void {
        if (this.syncZoom <= 1.05) return;
        this.isSyncPanning = true;
        this.syncDragStartX = e.clientX - this.syncPanX;
        this.syncDragStartY = e.clientY - this.syncPanY;
    }

    private onSyncMouseMove(e: MouseEvent): void {
        if (!this.isSyncPanning) return;
        this.syncPanX = e.clientX - this.syncDragStartX;
        this.syncPanY = e.clientY - this.syncDragStartY;
    }

    private onSyncMouseUp(): void {
        this.isSyncPanning = false;
    }

    private async mounted() {
        try {
            this.presets = await fetchSRPresets();
        } catch (e) {
            console.debug("Preset fetch notice:", e);
        }
        // Auto-fetch default preset on initial view mount
        this.onFetchTile();
    }

    private resetMetrics(): void {
        this.meanConfidence = null;
        this.hallucinationPct = null;
        this.metricPSNR = "--";
        this.metricSSIM = "--";
        this.metricSAM = "--";
        this.metricNIQE = "--";
        this.metricBRISQUE = "--";
        this.tileHash = "";
        this.txHash = "";
        this.chainStatus = "pending";
    }

    private async onFetchTile() {
        this.loadingTile = true;
        this.srError = null;
        try {
            const res = await fetchSRTile(this.selectedPresetId);
            const preview = res?.lr_preview || res?.preview_base64;
            if (preview) {
                this.lrImage = preview;
                this.hrImage = res.hr_preview || "";
                this.referenceTierLabel = res.reference_tier_label || (res.is_scientific_ground_truth ? "Ground Truth HR (1.5m)" : "");
                this.srImage = "";
                this.confidenceMap = "";
                this.infraOverlay = "";
                this.activeTab = 0;
                this.cloudWarning = res.cloud_warning || null;
                this.cloudCoveragePct = res.cloud_coverage_pct || 0.0;
                this.resetZoom();
                this.resetMetrics();
            } else {
                this.srError = "Tile fetch succeeded but no preview image was returned.";
            }
        } catch (e) {
            this.srError = e instanceof Error ? e.message : String(e);
            console.error("Fetch tile error:", e);
        } finally {
            this.loadingTile = false;
        }
    }

    private async onRunSR() {
        if (!this.hasLR) return;
        this.runningSR = true;
        this.srError = null;
        try {
            const res: ISRResult = await runSuperResolution({
                model_name: this.selectedModel,
                scale_factor: 4,
                mc_samples: this.mcSamples,
                apply_sharpen: this.applySharpen,
                use_tiling: true,
            });

            if (res) {
                this.srImage = res.sr_preview;
                if (res.hr_preview) {
                    this.hrImage = res.hr_preview;
                }
                if (res.reference_tier_label) {
                    this.referenceTierLabel = res.reference_tier_label;
                }
                this.confidenceMap = res.confidence_heatmap_preview || res.confidence_heatmap || "";
                this.inferenceTimeMs = res.inference_time_ms || 0;
                if (typeof res.mean_confidence === "number") {
                    this.meanConfidence = res.mean_confidence;
                } else if (typeof res.usp_metrics?.avg_confidence === "number") {
                    this.meanConfidence = res.usp_metrics.avg_confidence / 100.0;
                }
                if (typeof res.hallucination_pct === "number") {
                    this.hallucinationPct = res.hallucination_pct;
                }

                const m = res.metrics || {};
                this.metricPSNR = typeof m.psnr === "number" ? m.psnr.toFixed(2) : "N/A";
                this.metricSSIM = typeof m.ssim === "number" ? m.ssim.toFixed(3) : "N/A";
                this.metricSAM = typeof m.sam === "number" ? m.sam.toFixed(2) : "N/A";
                this.metricNIQE = typeof m.niqe === "number" ? m.niqe.toFixed(2) : "--";
                this.metricBRISQUE = typeof m.brisque === "number" ? m.brisque.toFixed(1) : "--";

                const rec = res.blockchain_record || res.blockchain_provenance;
                if (rec) {
                    this.tileHash = rec.sha256 || rec.imageHash || "";
                    this.chainStatus = rec.status || (rec.mode === "polygon_amoy" ? "verified" : "simulated");
                    this.txHash = rec.tx_hash || rec.txHash || "";
                    this.explorerUrl = rec.explorer_url || rec.txLink || this.explorerUrl;
                }
            }
        } catch (e) {
            this.srError = e instanceof Error ? e.message : String(e);
            console.error("SR execution error:", e);
        } finally {
            this.runningSR = false;
        }
    }

    private async onDetectInfrastructure() {
        this.detectingInfra = true;
        this.srError = null;
        try {
            const res: IInfrastructureResult = await detectInfrastructure();
            if (res) {
                const summary = res.infrastructure_summary;
                this.infraBuildings = res.building_count ?? summary?.buildings_count ?? 0;
                this.infraRoads = res.road_count ?? summary?.road_segments_count ?? 0;
                const roadKm = res.total_road_length_km ?? summary?.roads_length_km ?? 0;
                const builtKm2 = res.total_built_area_km2 ?? summary?.total_built_area_km2 ?? 0;
                this.infraRoadLength = parseFloat(Number(roadKm).toFixed(2));
                this.infraBuiltArea = parseFloat(Number(builtKm2).toFixed(4));
                const overlay = res.overlay_preview || res.infrastructure_overlay;
                if (overlay) {
                    this.infraOverlay = overlay;
                    this.activeTab = 3;
                }
            }
        } catch (e) {
            this.srError = e instanceof Error ? e.message : String(e);
            console.error("Infrastructure detection error:", e);
        } finally {
            this.detectingInfra = false;
        }
    }

    private async onRegisterOnChain() {
        this.registeringChain = true;
        this.srError = null;
        try {
            const res = await registerTileOnChain(this.selectedPresetId);
            if (res && res.record) {
                this.tileHash = res.record.sha256 || res.record.imageHash || this.tileHash;
                this.chainStatus = res.record.status || (res.record.mode === "polygon_amoy" ? "verified" : "simulated");
                if (res.record.tx_hash || res.record.txHash) {
                    this.txHash = res.record.tx_hash || res.record.txHash;
                }
                if (res.record.explorer_url || res.record.txLink) {
                    this.explorerUrl = res.record.explorer_url || res.record.txLink;
                }
            }
        } catch (e) {
            this.srError = e instanceof Error ? e.message : String(e);
            console.error("Register on-chain error:", e);
        } finally {
            this.registeringChain = false;
        }
    }
}
</script>

<style scoped lang="scss">
.sr-controls {
    padding: 16px 20px;
}

.sr-control-label {
    font-size: 13px;
    font-weight: 500;
    color: var(--rahat-text-dim);
    white-space: nowrap;
}

.sr-alert {
    background: var(--rahat-warn-soft) !important;
    border: 1px solid var(--rahat-warn);
    color: var(--rahat-warn) !important;
}

.sr-workspace-tabs {
    border-top: 1px solid var(--rahat-border);
}

.sr-single-preview {
    position: relative;
    max-width: 540px;
    margin: 0 auto;
    border-radius: 8px;
    overflow: hidden;
    background: var(--rahat-map-bg);
    border: 1px solid var(--rahat-border);

    .sr-image {
        width: 100%;
        display: block;
        image-rendering: pixelated;
    }
}

.sr-preview-box {
    position: relative;
}

.sr-prompt-overlay {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(0, 0, 0, 0.4);
    backdrop-filter: blur(2px);
}

.sr-side-by-side {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;

    @media (max-width: 900px) {
        grid-template-columns: 1fr;
    }
}

.sr-side-by-side--3col {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 14px;

    @media (max-width: 1200px) {
        grid-template-columns: 1fr;
    }
}

.sr-sync-toolbar {
    background: var(--rahat-surface-2);
    border: 1px solid var(--rahat-border);
    border-radius: 8px;
    padding: 6px 12px;
}

.sr-img-wrapper--sync {
    position: relative;
    user-select: none;
    overflow: hidden;

    img {
        user-select: none;
        -webkit-user-drag: none;
        pointer-events: none;
        width: 100%;
        height: 100%;
        object-fit: contain;
    }
}

.sr-side-card {
    background: var(--rahat-surface-2);
    border: 1px solid var(--rahat-border);
    border-radius: 8px;
    padding: 12px;
}

.sr-card-title {
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.02em;
    color: var(--rahat-text);
    margin-bottom: 8px;
}

.sr-img-wrapper {
    width: 100%;
    aspect-ratio: 1 / 1;
    background: var(--rahat-map-bg);
    border-radius: 6px;
    overflow: hidden;

    img {
        width: 100%;
        height: 100%;
        object-fit: contain;
        display: block;
    }
}

.sr-img-wrapper--pixelated img {
    image-rendering: pixelated;
}

.sr-meta {
    margin-top: 8px;
    font-size: 11px;
    color: var(--rahat-text-dim);
    font-family: monospace;
}

.sr-trust-legend {
    .sr-legend-bar {
        height: 8px;
        border-radius: 4px;
        background: linear-gradient(to right, #fb7185, #fbb931, #34d399);
        margin-bottom: 4px;
    }
}

.infra-stat-row {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    padding: 8px 0;
    border-bottom: 1px solid var(--rahat-border);
}

.metric-box {
    background: var(--rahat-surface-2);
    border: 1px solid var(--rahat-border);
    border-radius: 6px;
    padding: 12px;
    text-align: center;

    .metric-val {
        font-size: 20px;
        font-weight: 700;
        color: var(--rahat-info);
    }

    .metric-label {
        font-size: 12px;
        font-weight: 600;
        color: var(--rahat-text);
        margin-top: 2px;
    }

    .metric-sub {
        font-size: 10px;
        color: var(--rahat-text-dim);
        margin-top: 2px;
    }
}

.blockchain-status-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 8px;
}

.sr-label {
    position: absolute;
    top: 10px;
    left: 10px;
    padding: 3px 8px;
    border-radius: 4px;
    font-size: 10px;
    font-weight: 600;
    background: rgba(0, 0, 0, 0.7);
    color: #fbb931;
    border: 1px solid rgba(251, 185, 49, 0.3);
}
</style>
