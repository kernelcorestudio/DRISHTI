<!--
    RAHAT + NETRA - Multi-Spectral Environmental & Hazard Mapping Workspace
    NDVI, NDWI, NDBI, NBR, and True/False Color IR Spectral Indices
-->

<template>
    <div class="page">
        <!-- KPI Ribbon -->
        <div class="grid grid--kpi">
            <StatCard label="Active Mode" :value="activeModeLabel" hint="multi-spectral algorithm" />
            <StatCard label="Surveyed Area" :value="surveyedAreaLabel" unit="km²" hint="total AOI extent" />
            <StatCard label="Target Extent" :value="classifiedAreaLabel" unit="km²" :hint="categoryLabel" />
            <StatCard label="Coverage" :value="coveragePctLabel" unit="%" hint="ratio of total scene" />
        </div>

        <!-- Spectral Mode Selector Bar -->
        <SectionCard class="block"
                     title="Spectral Index Selection & Band Combinations"
                     subtitle="compute scientific multi-spectral indices across 10-band Sentinel-2 imagery with dynamic SR enhancement">
            <div class="pa-4">
                <v-row dense class="mb-2">
                    <v-col v-for="mode in availableModes"
                           :key="mode.id"
                           cols="12" sm="6" md="4" lg="2">
                        <div class="spectral-mode-card"
                             :class="{ 'spectral-mode-card--active': currentMode === mode.id }"
                             @click="onSelectMode(mode.id)">
                            <div class="mode-icon-wrapper" :style="{ color: mode.color }">
                                <v-icon small>{{ mode.icon }}</v-icon>
                            </div>
                            <div class="mode-info">
                                <div class="mode-title">{{ mode.title }}</div>
                                <div class="mode-formula mono text-caption">{{ mode.formula }}</div>
                            </div>
                        </div>
                    </v-col>
                </v-row>

                <v-alert v-if="spectralError"
                         dense text type="error"
                         dismissible
                         class="mt-3 mb-0"
                         @input="spectralError = null">
                    {{ spectralError }}
                </v-alert>

                <div class="d-flex align-center justify-space-between mt-3 pt-3 border-top">
                    <div class="faint text-caption">
                        <strong>Formula:</strong> {{ modeDescription }} • <strong>Bands:</strong> {{ bandsUsedLabel }}
                    </div>

                    <div class="d-flex align-center">
                        <v-switch v-model="applySharpen"
                                  label="Edge Sharpening"
                                  dense hide-details
                                  color="accent"
                                  class="mr-4"
                                  @change="onRefreshSpectral" />

                        <v-btn small color="primary"
                               :loading="loading"
                               @click="onRefreshSpectral">
                            <v-icon left small>mdi-refresh</v-icon>
                            Re-Compute
                        </v-btn>
                    </div>
                </div>
            </div>
        </SectionCard>

        <!-- Spectral Dual-View Comparison -->
        <SectionCard class="block"
                     :title="`${activeModeLabel} — 10m Input vs 2.5m Super-Resolved Raster`"
                     subtitle="real-time sub-50ms spectral index mapping powered by spyndex and calibrated color ramps"
                     flush>
            <div class="pa-4">
                <div class="spectral-side-by-side">
                    <!-- Left: 10m LR Spectral -->
                    <div class="spectral-view-box">
                        <div class="view-header">
                            <div class="view-title">Sentinel-2 Native Spectral (10m)</div>
                            <span class="chip chip--warn">10m / px</span>
                        </div>
                        <div class="view-img-wrapper view-img-wrapper--pixelated">
                            <img v-if="lrPreview" :src="lrPreview" :alt="`${currentMode} 10m`" />
                            <div v-else class="empty py-12">Loading spectral raster...</div>
                        </div>
                    </div>

                    <!-- Right: 2.5m SR Spectral -->
                    <div class="spectral-view-box">
                        <div class="view-header">
                            <div class="view-title">Super-Resolved Spectral (2.5m)</div>
                            <span class="chip chip--ok">2.5m / px (4x SR)</span>
                        </div>
                        <div class="view-img-wrapper">
                            <img v-if="srPreview" :src="srPreview" :alt="`${currentMode} 2.5m SR`" />
                            <div v-else-if="lrPreview" class="empty py-12">
                                <v-icon small color="accent" class="mb-1">mdi-lightning-bolt</v-icon>
                                <div>Run Super-Resolution in the SR workspace to enable 4x spectral view</div>
                            </div>
                            <div v-else class="empty py-12">Loading...</div>
                        </div>
                    </div>
                </div>

                <!-- Dynamic Spectral Legend -->
                <div v-if="gradientCss || legendItems.length > 0" class="mt-4 pt-3 border-top">
                    <div class="legend-header mb-2 faint text-caption">Dynamic Spectral Classification Thresholds:</div>
                    <div v-if="gradientCss" class="mb-3">
                        <div class="spectral-gradient-bar" :style="{ background: gradientCss }" />
                    </div>
                    <div v-if="legendItems.length > 0" class="legend-grid">
                        <div v-for="(item, idx) in legendItems" :key="idx" class="legend-item">
                            <span class="legend-swatch" :style="{ backgroundColor: item.color }" />
                            <span class="legend-label">{{ item.label }}</span>
                            <span class="legend-thresh mono">{{ item.threshold }}</span>
                        </div>
                    </div>
                </div>
            </div>
        </SectionCard>

        <!-- Real-World Area Breakdown Card -->
        <SectionCard class="block"
                     title="Environmental & Hazard Impact Breakdown"
                     subtitle="quantitative surface area classification derived from spectral thresholds">
            <div class="pa-4">
                <v-row dense>
                    <v-col cols="12" md="4">
                        <div class="impact-kpi-card">
                            <div class="kpi-tag">Classified Surface Extent</div>
                            <div class="kpi-num mono">{{ classifiedAreaLabel }} <span class="unit">km²</span></div>
                            <div class="kpi-sub">{{ categoryLabel }} ({{ thresholdLabel }})</div>
                        </div>
                    </v-col>

                    <v-col cols="12" md="4">
                        <div class="impact-kpi-card">
                            <div class="kpi-tag">Percentage of Surveyed AOI</div>
                            <div class="kpi-num mono">{{ coveragePctLabel }} <span class="unit">%</span></div>
                            <div class="kpi-sub">Total Area: {{ surveyedAreaLabel }} km²</div>
                        </div>
                    </v-col>

                    <v-col cols="12" md="4">
                        <div class="impact-kpi-card">
                            <div class="kpi-tag">Disaster / Mitigation Context</div>
                            <div class="context-text">{{ disasterContext }}</div>
                        </div>
                    </v-col>
                </v-row>
            </div>
        </SectionCard>
    </div>
</template>

<script lang="ts">
/* eslint-disable no-console */
import { Component, Vue } from "vue-property-decorator";

import SectionCard from "@/ui/components/SectionCard.vue";
import StatCard from "@/ui/components/StatCard.vue";

import { fetchSpectralVisualization } from "@/modules/api";
import { ISpectralResult, ISpectralLegendItem } from "@/models";

interface ISpectralModeMeta {
    id: string;
    title: string;
    formula: string;
    icon: string;
    color: string;
    context: string;
}

@Component({
    components: {
        SectionCard,
        StatCard,
    },
})
export default class SpectralAnalysisView extends Vue {
    private currentMode = "ndvi";
    private applySharpen = false;
    private loading = false;
    private spectralError: string | null = null;
    private loadSeq = 0;

    private lrPreview = "";
    private srPreview = "";
    private modeTitle = "Normalized Difference Vegetation Index";
    private modeSubtitle = "Vegetation health, crop stress, and canopy density";
    private modeDescription = "(NIR - Red) / (NIR + Red)";
    private bandsUsed: string[] = ["B08 (NIR)", "B04 (Red)"];
    private legendItems: ISpectralLegendItem[] = [];
    private gradientCss: string | null = null;

    private surveyedArea: number | null = null;
    private classifiedArea: number | null = null;
    private coveragePct: number | null = null;
    private categoryName = "Awaiting computation";
    private thresholdName = "--";

    private readonly availableModes: ISpectralModeMeta[] = [
        {
            id: "true_color",
            title: "True Color RGB",
            formula: "B04 + B03 + B02",
            icon: "mdi-eye-outline",
            color: "#38bdf8",
            context: "Natural visible spectrum calibrated with Esri perceptual tone-matching.",
        },
        {
            id: "false_color_ir",
            title: "False Color IR",
            formula: "B08 + B04 + B03",
            icon: "mdi-tree-outline",
            color: "#fb7185",
            context: "NIR reflection makes lush vegetation bright crimson red, revealing flood lines.",
        },
        {
            id: "ndvi",
            title: "NDVI (Vegetation)",
            formula: "(NIR - Red) / (NIR + Red)",
            icon: "mdi-sprout-outline",
            color: "#34d399",
            context: "Evaluates vegetation vigor, drought stress, and agricultural crop damage.",
        },
        {
            id: "ndwi",
            title: "NDWI (Water Bodies)",
            formula: "(Green - NIR) / (Green + NIR)",
            icon: "mdi-water-outline",
            color: "#60a5fa",
            context: "Delineates open water bodies, river boundaries, and flood inundation extent.",
        },
        {
            id: "ndbi",
            title: "NDBI (Built-up / Urban)",
            formula: "(SWIR1 - NIR) / (SWIR1 + NIR)",
            icon: "mdi-city-variant-outline",
            color: "#fbb931",
            context: "Highlights concrete, built-up surfaces, asphalt, and urban sprawl.",
        },
        {
            id: "nbr",
            title: "NBR (Burn Scar)",
            formula: "(NIR - SWIR2) / (NIR + SWIR2)",
            icon: "mdi-fire",
            color: "#e0424e",
            context: "Pinpoints active burn scars, wildfire severity, and charred soil surfaces.",
        },
    ];

    private get activeModeLabel(): string {
        const found = this.availableModes.find(m => m.id === this.currentMode);
        return found ? found.title : this.currentMode.toUpperCase();
    }

    private get surveyedAreaLabel(): string {
        return this.surveyedArea !== null ? this.surveyedArea.toFixed(2) : "--";
    }

    private get classifiedAreaLabel(): string {
        return this.classifiedArea !== null ? this.classifiedArea.toFixed(2) : "--";
    }

    private get coveragePctLabel(): string {
        return this.coveragePct !== null ? this.coveragePct.toFixed(1) : "--";
    }

    private get categoryLabel(): string {
        return this.categoryName;
    }

    private get thresholdLabel(): string {
        return this.thresholdName;
    }

    private get bandsUsedLabel(): string {
        return this.bandsUsed.join(", ");
    }

    private get disasterContext(): string {
        const found = this.availableModes.find(m => m.id === this.currentMode);
        return found ? found.context : "Multi-spectral hazard analysis";
    }

    private async mounted() {
        await this.loadSpectral(this.currentMode);
    }

    private async onSelectMode(modeId: string) {
        if (this.currentMode === modeId) return;
        this.currentMode = modeId;
        await this.loadSpectral(modeId);
    }

    private async onRefreshSpectral() {
        await this.loadSpectral(this.currentMode);
    }

    private async loadSpectral(mode: string) {
        const seq = ++this.loadSeq;
        this.loading = true;
        this.spectralError = null;
        try {
            const res: ISpectralResult = await fetchSpectralVisualization(mode, this.applySharpen);
            if (seq !== this.loadSeq) {
                return;
            }
            if (res) {
                this.lrPreview = res.lr_preview || "";
                this.srPreview = res.sr_preview || "";
                this.modeTitle = res.title;
                this.modeSubtitle = res.subtitle;
                this.modeDescription = res.description;
                this.bandsUsed = res.bands_used || [];
                this.gradientCss = res.gradient_css || (res.legend && !Array.isArray(res.legend) ? res.legend.gradient_css : null) || null;
                if (Array.isArray(res.legend_items)) {
                    this.legendItems = res.legend_items;
                } else if (Array.isArray(res.legend)) {
                    this.legendItems = res.legend;
                } else {
                    this.legendItems = [];
                }

                if (res.coverage_stats) {
                    this.surveyedArea = res.coverage_stats.total_aoi_km2 ?? null;
                    this.classifiedArea = res.coverage_stats.area_km2 ?? null;
                    this.coveragePct = res.coverage_stats.area_pct ?? null;
                    this.categoryName = res.coverage_stats.category || "";
                    this.thresholdName = res.coverage_stats.threshold || "";
                }
            }
        } catch (e) {
            if (seq === this.loadSeq) {
                this.spectralError = e instanceof Error ? e.message : String(e);
            }
            console.error("Load spectral error:", e);
        } finally {
            if (seq === this.loadSeq) {
                this.loading = false;
            }
        }
    }
}
</script>

<style scoped lang="scss">
.spectral-mode-card {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 12px;
    background: var(--rahat-surface-2);
    border: 1px solid var(--rahat-border);
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.2s ease;

    &:hover {
        background: var(--rahat-accent-soft);
        border-color: var(--rahat-border-strong);
    }

    &--active {
        background: rgba(164, 22, 26, 0.15) !important;
        border-color: #a4161a !important;
        box-shadow: 0 0 12px rgba(164, 22, 26, 0.3);
    }
}

.mode-icon-wrapper {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    border-radius: 6px;
    background: var(--rahat-chip);
}

.mode-title {
    font-size: 12px;
    font-weight: 600;
    color: var(--rahat-text);
}

.mode-formula {
    font-size: 10px;
    color: var(--rahat-text-dim);
}

.border-top {
    border-top: 1px solid var(--rahat-border);
}

.spectral-side-by-side {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;

    @media (max-width: 900px) {
        grid-template-columns: 1fr;
    }
}

.spectral-view-box {
    background: var(--rahat-surface-2);
    border: 1px solid var(--rahat-border);
    border-radius: 8px;
    padding: 12px;
}

.view-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
}

.view-title {
    font-size: 13px;
    font-weight: 600;
    color: var(--rahat-text);
}

.view-img-wrapper {
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

    &--pixelated img {
        image-rendering: pixelated;
    }
}

.spectral-gradient-bar {
    height: 10px;
    border-radius: 999px;
    border: 1px solid var(--rahat-border);
}

.legend-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 8px;
}

.legend-item {
    display: flex;
    align-items: center;
    gap: 8px;
    background: var(--rahat-card);
    padding: 6px 10px;
    border-radius: 4px;
    border: 1px solid var(--rahat-border);
}

.legend-swatch {
    width: 14px;
    height: 14px;
    border-radius: 3px;
    flex-shrink: 0;
}

.legend-label {
    font-size: 11px;
    color: var(--rahat-text);
    flex-grow: 1;
}

.legend-thresh {
    font-size: 10px;
    color: var(--rahat-text-dim);
}

.impact-kpi-card {
    background: var(--rahat-surface-2);
    border: 1px solid var(--rahat-border);
    border-radius: 8px;
    padding: 16px;
    height: 100%;

    .kpi-tag {
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: var(--rahat-text-dim);
    }

    .kpi-num {
        font-size: 26px;
        font-weight: 700;
        color: var(--rahat-info);
        margin: 4px 0;

        .unit {
            font-size: 14px;
            color: var(--rahat-text-dim);
        }
    }

    .kpi-sub {
        font-size: 12px;
        color: var(--rahat-text);
    }

    .context-text {
        font-size: 13px;
        line-height: 1.5;
        color: var(--rahat-text);
        margin-top: 6px;
    }
}
</style>
