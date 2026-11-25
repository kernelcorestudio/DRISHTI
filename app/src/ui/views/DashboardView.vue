<!--
    DISASTER RESPONSE APP
    Copyright (c) 2021 SilentByte <https://silentbyte.com/>
-->

<template>
    <div class="page">
        <div class="grid grid--kpi">
            <StatCard label="zones indexed"
                      :value="zoneCount"
                      icon="mdi-layers-outline"
                      hint="scenes with GeoJSON layers" />
            <StatCard label="buildings mapped"
                      :value="affectedCount + intactCount"
                      icon="mdi-office-building-outline"
                      hint="stage-1 footprints classified" />
            <StatCard label="affected"
                      :value="affectedCount"
                      tone="warn"
                      icon="mdi-alert-outline"
                      hint="severe + moderate combined" />
            <StatCard label="severe"
                      :value="severeCount"
                      tone="bad"
                      icon="mdi-flash-outline"
                      hint="destruction level damage" />
            <StatCard label="moderate"
                      :value="moderateCount"
                      tone="warn"
                      icon="mdi-circle-half-full"
                      hint="partial damage" />
            <StatCard label="intact"
                      :value="intactCount"
                      tone="good"
                      icon="mdi-check-circle-outline"
                      hint="no visible damage" />
        </div>

        <v-alert v-if="serviceError"
                 dense text type="error"
                 class="service-alert">
            {{ serviceError }}
        </v-alert>

        <!--
            The telemetry band: totals, accuracy, the last run, the tile inventory and the stages
            behind them, as one bento instead of two columns of prose. Every number below is read
            from /health, /diagnostics and /jobs - nothing here is decoration.
        -->
        <div class="bento">
            <GlowCard class="bento-hero card-frame" :index="0">
                <span class="card-wave card-wave--top" aria-hidden="true" />

                <header class="card-head">
                    <span class="card-mark" aria-hidden="true">
                        <svg viewBox="0 0 24 24">
                            <path d="M12 3.2 3.2 8 12 12.8 20.8 8 12 3.2Z" />
                            <path d="m3.2 12.6 8.8 4.8 8.8-4.8"
                                  fill="none" stroke="currentColor" stroke-width="1.7"
                                  stroke-linecap="round" />
                        </svg>
                    </span>

                    <span class="card-sep" aria-hidden="true" />

                    <div class="card-titles">
                        <h3 class="card-title">damage assessment</h3>
                        <p class="card-subtitle">building impact and severity overview</p>
                    </div>

                    <span class="live-pill" :class="{'live-pill--down': !apiReady}">
                        <span class="live-dot" />
                        {{ apiReady ? "live" : "offline" }}
                    </span>
                </header>

                <div class="hero-figures">
                    <div class="hero-main">
                        <span class="hero-value">{{ animated.affected }}</span>
                        <span class="hero-unit">buildings affected</span>
                    </div>

                    <div class="hero-split">
                        <div class="split-item">
                            <span class="split-icon split-icon--severe" aria-hidden="true">
                                <svg viewBox="0 0 24 24">
                                    <path d="M12.8 3 6 13.4h5l-1 7.6 7.2-10.6h-5L12.8 3Z" />
                                </svg>
                            </span>

                            <span class="split-copy">
                                <b>{{ severeCount }}</b>
                                <i>severe</i>
                            </span>
                        </div>

                        <div class="split-item">
                            <span class="split-icon split-icon--moderate" aria-hidden="true">
                                <svg viewBox="0 0 24 24">
                                    <path d="M12 3.6 4.2 8 12 12.4 19.8 8 12 3.6Z" />
                                    <path d="m4.2 12.4 7.8 4.4 7.8-4.4" />
                                </svg>
                            </span>

                            <span class="split-copy">
                                <b>{{ moderateCount }}</b>
                                <i>moderate</i>
                            </span>
                        </div>

                        <div class="split-item">
                            <span class="split-icon split-icon--intact" aria-hidden="true">
                                <svg viewBox="0 0 24 24">
                                    <path d="M12 3.2 5.2 6v5.3c0 4 2.9 7.2 6.8 8.4 3.9-1.2 6.8-4.4 6.8-8.4V6L12 3.2Z" />
                                    <path d="m9.3 11.5 1.9 1.9 3.5-3.7" />
                                </svg>
                            </span>

                            <span class="split-copy">
                                <b>{{ intactCount }}</b>
                                <i>intact</i>
                            </span>
                        </div>
                    </div>
                </div>

                <div class="hero-chart">
                    <div class="hero-yaxis" aria-hidden="true">
                        <span v-for="tick in chartTicks"
                              :key="tick.label"
                              :style="{top: `${tick.y}%`}">{{ tick.label }}</span>
                    </div>

                    <div class="hero-plot"
                         @mousemove="onChartMove"
                         @mouseleave="chartHover = -1">
                        <svg class="hero-svg" viewBox="0 0 100 100" preserveAspectRatio="none"
                             role="img" aria-label="Affected buildings in each indexed zone">
                            <defs>
                                <linearGradient id="hero-fill" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="0%" stop-color="rgba(255, 59, 74, 0.44)" />
                                    <stop offset="62%" stop-color="rgba(255, 59, 74, 0.12)" />
                                    <stop offset="100%" stop-color="rgba(255, 59, 74, 0)" />
                                </linearGradient>
                            </defs>

                            <line v-for="tick in chartTicks" :key="tick.label"
                                  x1="0" :y1="tick.y" x2="100" :y2="tick.y"
                                  :class="{'hero-grid--base': tick.value === 0}"
                                  stroke-dasharray="3 5"
                                  vector-effect="non-scaling-stroke" />

                            <path v-if="chartArea" :d="chartArea" fill="url(#hero-fill)" />
                            <path v-if="chartLine" :d="chartLine" class="hero-line" vector-effect="non-scaling-stroke" />

                            <line v-if="hoveredPoint"
                                  :x1="hoveredPoint.x" :x2="hoveredPoint.x" y1="0" y2="100"
                                  class="hero-guide" vector-effect="non-scaling-stroke" />
                        </svg>

                        <span v-for="(point, index) in chartPoints"
                              :key="`node-${index}`"
                              class="hero-node"
                              :style="{left: `${point.x}%`, top: `${point.y}%`}" />

                        <span v-if="hoveredPoint"
                              class="hero-dot"
                              :style="{left: `${hoveredPoint.x}%`, top: `${hoveredPoint.y}%`}" />

                        <div v-if="hoveredZone"
                             class="hero-tip"
                             :class="{'hero-tip--below': tipBelow}"
                             :style="{left: tipLeft, top: tipTop}">
                            <span class="tip-zone">{{ hoveredZone.label }}</span>
                            <span class="tip-value">{{ hoveredZone.value }} affected</span>
                        </div>
                    </div>
                </div>

                <div class="hero-axis">
                    <span>{{ heroAxis.start }}</span>
                    <span>{{ heroAxis.end }}</span>
                </div>

                <ul class="svc-grid">
                    <li v-for="row in serviceRows" :key="row.label" class="svc-row">
                        <span class="svc-dot" :class="`svc-dot--${row.state}`" />
                        <span class="svc-label">{{ row.label }}</span>
                        <span class="svc-value">{{ row.value }}</span>
                    </li>
                </ul>

                <p class="hero-foot">
                    <svg viewBox="0 0 24 24" aria-hidden="true">
                        <path d="M20.4 12a8.4 8.4 0 1 1-2.5-6" />
                        <path d="M20.4 4.2v4.3h-4.3" />
                    </svg>
                    refreshed {{ syncedLabel }} · {{ maxJobs }} queue slots · {{ minArea }} px min-area
                </p>
            </GlowCard>

            <GlowCard class="bento-rings card-frame" tone="amber" :index="1">
                <!-- Two arcs of hairline rings, clipped by the card radius: the corners are the
                     only decoration on this card. -->
                <span class="card-wave card-wave--top" aria-hidden="true" />
                <span class="card-wave card-wave--bottom" aria-hidden="true" />

                <header class="card-head">
                    <span class="card-mark" aria-hidden="true">
                        <svg viewBox="0 0 24 24">
                            <rect x="4.4" y="12.2" width="3.7" height="7.4" rx="1.5" />
                            <rect x="10.15" y="8.1" width="3.7" height="11.5" rx="1.5" />
                            <rect x="15.9" y="4.4" width="3.7" height="15.2" rx="1.5" />
                        </svg>
                    </span>

                    <span class="card-sep" aria-hidden="true" />

                    <h3 class="card-title">model quality</h3>
                </header>

                <div class="rings">
                    <div v-for="ring in qualityRings" :key="ring.label" class="ring-cell">
                        <RingGauge :label="ring.label"
                                   :value="ring.value"
                                   :display="ring.display"
                                   :tone="ring.tone"
                                   :hint="ring.hint"
                                   :icon="ring.icon" />
                    </div>
                </div>

                <p class="quality-note">
                    <svg viewBox="0 0 24 24" aria-hidden="true">
                        <circle cx="12" cy="12" r="9.2" />
                        <path d="M12 11v5.4" />
                        <circle class="note-dot" cx="12" cy="7.7" r="1.05" />
                    </svg>

                    <span>{{ qualitySource }}</span>
                </p>
            </GlowCard>

            <GlowCard class="bento-term card-frame" tone="amber" :index="2">
                <span class="card-wave card-wave--top" aria-hidden="true" />

                <header class="card-head">
                    <span class="card-mark" aria-hidden="true">
                        <svg viewBox="0 0 24 24">
                            <path d="m5.4 6.6 4.4 5.4-4.4 5.4" />
                            <path d="M12.6 17.6h6" />
                        </svg>
                    </span>

                    <span class="card-sep" aria-hidden="true" />

                    <div class="card-titles">
                        <h3 class="card-title">last run</h3>
                        <p class="card-subtitle">most recent pipeline run</p>
                    </div>

                    <span class="term-lights" aria-hidden="true"><i /><i /><i /></span>
                </header>

                <div class="term-body" role="log" aria-label="Pipeline output">
                    <span class="term-wave" aria-hidden="true" />

                    <div v-for="(line, index) in visibleLogLines"
                         :key="index"
                         class="term-line"
                         :class="`term-line--${line.type}`">
                        <span class="term-mark" :class="`term-mark--${line.type}`">{{ lineMark(line.type) }}</span>
                        <span class="term-text" :class="`term-text--${line.type}`">{{ line.text }}</span>

                        <svg v-if="line.type === 'url'" class="term-open" viewBox="0 0 24 24" aria-hidden="true">
                            <path d="M13.6 5.6h4.8v4.8" />
                            <path d="M18.2 5.8 11 13" />
                            <path d="M16.8 14v3.4a1.6 1.6 0 0 1-1.6 1.6H6.6A1.6 1.6 0 0 1 5 17.4V8.6A1.6 1.6 0 0 1 6.6 7h3.4" />
                        </svg>
                    </div>

                    <span class="term-caret" :class="{'term-caret--typing': logTyping}" />
                </div>
            </GlowCard>

            <GlowCard class="bento-bars card-frame" tone="vivid" :index="3">
                <span class="card-wave card-wave--top" aria-hidden="true" />

                <span class="bars-watermark" aria-hidden="true">
                    <svg viewBox="0 0 24 24">
                        <path d="M12 3.2 3.2 8 12 12.8 20.8 8 12 3.2Z" />
                        <path d="m3.2 12.6 8.8 4.8 8.8-4.8" />
                        <path d="m3.2 17.4 8.8 4.8 8.8-4.8" />
                    </svg>
                </span>

                <header class="card-head">
                    <span class="card-mark" aria-hidden="true">
                        <svg viewBox="0 0 24 24">
                            <path d="M12 3.2 3.2 8 12 12.8 20.8 8 12 3.2Z" />
                            <path d="m3.2 12.6 8.8 4.8 8.8-4.8"
                                  fill="none" stroke="currentColor" stroke-width="1.7"
                                  stroke-linecap="round" />
                        </svg>
                    </span>

                    <span class="card-sep" aria-hidden="true" />

                    <div class="card-titles">
                        <h3 class="card-title">offline imagery</h3>
                        <p class="card-subtitle">tile distribution across zoom levels</p>
                    </div>
                </header>

                <div class="bars-figure">
                    <span class="bars-value">{{ animated.tiles }}</span>
                    <span class="bars-unit">tiles</span>
                </div>

                <div class="bars-plot">
                    <div class="bars-yaxis" aria-hidden="true">
                        <span v-for="tick in barsTicks"
                              :key="tick.label"
                              :style="{bottom: `${tick.y}%`}">{{ tick.label }}</span>
                    </div>

                    <div class="bars-stage">
                        <span v-for="tick in barsTicks"
                              :key="`grid-${tick.label}`"
                              class="bars-grid"
                              :class="{'bars-grid--base': tick.value === 0}"
                              :style="{bottom: `${tick.y}%`}"
                              aria-hidden="true" />

                        <div class="bars">
                            <button v-for="(bar, index) in imageryBars"
                                    :key="bar.label"
                                    type="button"
                                    class="bar"
                                    :class="{'bar--hot': index === barHover, 'bar--peak': index === peakBar}"
                                    :style="{height: `${bar.height}%`}"
                                    :aria-label="`${bar.label}: ${bar.value} tiles`"
                                    @mouseenter="barHover = index"
                                    @mouseleave="barHover = -1"
                                    @focus="barHover = index"
                                    @blur="barHover = -1" />
                        </div>
                    </div>
                </div>

                <div class="bars-axis" aria-hidden="true">
                    <span v-for="(bar, index) in imageryBars"
                          :key="bar.label"
                          :class="{'bars-zoom--hot': index === barHover}">
                        <b>{{ bar.label }}</b>
                        <i>{{ bar.value }}</i>
                    </span>
                </div>

                <p class="bars-caption">
                    <svg viewBox="0 0 24 24" aria-hidden="true">
                        <circle cx="12" cy="12" r="9.2" />
                        <path d="M12 11v5.4" />
                        <circle class="note-dot" cx="12" cy="7.7" r="1.05" />
                    </svg>
                    <span>{{ barCaption }}</span>
                </p>
            </GlowCard>

            <GlowCard class="bento-stack card-frame" :index="4">
                <span class="card-wave card-wave--top" aria-hidden="true" />
                <span class="card-wave card-wave--bottom" aria-hidden="true" />

                <header class="card-head">
                    <span class="card-mark" aria-hidden="true">
                        <svg viewBox="0 0 24 24">
                            <path d="M12 3.2 3.2 8 12 12.8 20.8 8 12 3.2Z" />
                            <path d="m3.2 12.6 8.8 4.8 8.8-4.8"
                                  fill="none" stroke="currentColor" stroke-width="1.7"
                                  stroke-linecap="round" />
                        </svg>
                    </span>

                    <span class="card-sep" aria-hidden="true" />

                    <div class="card-titles">
                        <h3 class="card-title">pipeline</h3>
                        <p class="card-subtitle">every stage running behind the ui</p>
                    </div>

                    <span class="pipeline-hint">
                        <svg viewBox="0 0 24 24" aria-hidden="true">
                            <circle cx="12" cy="12" r="9.2" />
                            <path d="M12 11v5.4" />
                            <circle cx="12" cy="7.9" r="0.6" />
                        </svg>
                        hover a stage for detail
                    </span>
                </header>

                <ul class="stages">
                    <li v-for="(step, index) in pipeline" :key="step.label">
                        <button type="button"
                                class="stage"
                                :class="{'stage--on': index === stageHover}"
                                @mouseenter="stageHover = index"
                                @mouseleave="stageHover = -1"
                                @focus="stageHover = index"
                                @blur="stageHover = -1">
                            <span class="stage-icon"><v-icon>{{ step.icon }}</v-icon></span>
                            <span class="stage-name">{{ step.label }}</span>
                            <span class="stage-state" :class="`stage-state--${step.state}`">
                                <i class="stage-check" aria-hidden="true">✓</i>{{ step.state }}
                            </span>
                        </button>
                    </li>
                </ul>

                <p :key="activeStageDetail" class="stage-detail" aria-live="polite">
                    {{ activeStageDetail }}
                </p>
            </GlowCard>
        </div>

        <div class="grid grid--two dashboard-bottom">
            <GlowCard class="bento-split card-frame" :index="5">
                <span class="card-wave card-wave--top" aria-hidden="true" />
                <span class="card-wave card-wave--bottom" aria-hidden="true" />

                <header class="card-head">
                    <span class="card-mark" aria-hidden="true">
                        <svg viewBox="0 0 24 24">
                            <path d="M12 3.2 3.2 8 12 12.8 20.8 8 12 3.2Z" />
                            <path d="m3.2 12.6 8.8 4.8 8.8-4.8"
                                  fill="none" stroke="currentColor" stroke-width="1.7"
                                  stroke-linecap="round" />
                        </svg>
                    </span>

                    <span class="card-sep" aria-hidden="true" />

                    <div class="card-titles">
                        <h3 class="card-title">damage split</h3>
                        <p class="card-subtitle">all indexed zones combined</p>
                    </div>

                    <span class="split-scope">
                        <svg viewBox="0 0 24 24" aria-hidden="true">
                            <path d="M4.6 16.4v-3.6" />
                            <path d="M9.8 16.4V8.8" />
                            <path d="M15 16.4v-5.2" />
                            <path d="M20.2 16.4V6.6" />
                        </svg>
                        severity
                        <svg class="scope-chevron" viewBox="0 0 24 24" aria-hidden="true">
                            <path d="m6.8 9.6 5.2 5.2 5.2-5.2" />
                        </svg>
                    </span>
                </header>

                <DonutChart :segments="severitySegments" caption="buildings" />
            </GlowCard>

            <GlowCard class="bento-zones card-frame" :index="6">
                <span class="card-wave card-wave--top" aria-hidden="true" />
                <span class="card-wave card-wave--bottom" aria-hidden="true" />

                <header class="card-head">
                    <span class="card-mark" aria-hidden="true">
                        <svg viewBox="0 0 24 24">
                            <path fill-rule="evenodd"
                                  d="M12 1.8a7.4 7.4 0 0 0-7.4 7.4c0 5.4 7.4 13 7.4 13s7.4-7.6 7.4-13A7.4 7.4 0 0 0 12 1.8Zm0 10.2a2.8 2.8 0 1 1 0-5.6 2.8 2.8 0 0 1 0 5.6Z" />
                        </svg>
                    </span>

                    <span class="card-sep" aria-hidden="true" />

                    <div class="card-titles">
                        <h3 class="card-title">affected by zone</h3>
                        <p class="card-subtitle">stage-2 damaged footprints</p>
                    </div>

                    <span class="zone-key">
                        <span v-for="item in severityLegend"
                              :key="item.label"
                              class="zone-key-item">
                            <i class="zone-key-dot" :style="{'--dot': item.color}" />
                            {{ item.label }}
                        </span>
                    </span>
                </header>

                <ZoneBars :rows="affectedByZone" empty-label="no zones indexed yet" />
            </GlowCard>
        </div>

        <div class="grid dashboard-last">
            <GlowCard class="bento-jobs card-frame" :index="7">
                <span class="card-wave card-wave--top" aria-hidden="true" />
                <span class="card-wave card-wave--bottom" aria-hidden="true" />

                <header class="card-head">
                    <span class="card-mark" aria-hidden="true">
                        <svg viewBox="0 0 24 24">
                            <path d="M12 3.2 3.2 8 12 12.8 20.8 8 12 3.2Z" />
                            <path d="m3.2 12.6 8.8 4.8 8.8-4.8"
                                  fill="none" stroke="currentColor" stroke-width="1.7"
                                  stroke-linecap="round" />
                            <path d="m3.2 17.3 8.8 4.8 8.8-4.8"
                                  fill="none" stroke="currentColor" stroke-width="1.7"
                                  stroke-linecap="round" />
                        </svg>
                    </span>

                    <span class="card-sep" aria-hidden="true" />

                    <div class="card-titles">
                        <h3 class="card-title">recent jobs</h3>
                        <p class="card-subtitle">in-memory queue history</p>
                    </div>

                    <span class="live-pill" :class="{'live-pill--down': !apiReady}">
                        <span class="live-dot" />
                        {{ apiReady ? "live queue" : "queue offline" }}
                    </span>
                </header>

                <div class="jobs-shell">
                    <JobTable :jobs="jobs" :limit="5" with-icons>
                        <template v-slot:empty>
                            <div class="jobs-empty">
                                <span class="jobs-empty-mark" aria-hidden="true">
                                    <svg viewBox="0 0 24 24">
                                        <path d="M12 3.4 3.6 8 12 12.6 20.4 8 12 3.4Z" />
                                        <path d="m3.6 12.4 8.4 4.6 8.4-4.6"
                                              fill="none" stroke="currentColor" stroke-width="1.6"
                                              stroke-linecap="round" />
                                        <path d="m3.6 16.9 8.4 4.6 8.4-4.6"
                                              fill="none" stroke="currentColor" stroke-width="1.6"
                                              stroke-linecap="round" />
                                    </svg>
                                    <i class="jobs-empty-pad" />
                                </span>

                                <p class="jobs-empty-title">no jobs yet</p>
                                <p class="jobs-empty-hint">
                                    Submit a GeoTIFF pair on the Inference page to start a new job.
                                </p>

                                <v-btn small outlined to="/inference" class="jobs-empty-cta">
                                    <v-icon small left>mdi-play-outline</v-icon>
                                    go to inference
                                </v-btn>
                            </div>
                        </template>
                    </JobTable>
                </div>
            </GlowCard>

            <GlowCard class="bento-actions card-frame" :index="8">
                <span class="card-wave card-wave--top" aria-hidden="true" />
                <span class="card-wave card-wave--bottom" aria-hidden="true" />

                <header class="card-head">
                    <span class="card-mark" aria-hidden="true">
                        <svg viewBox="0 0 24 24">
                            <path d="M13.4 2.8 5.6 13.6h4.9l-1.1 7.6 8-11h-4.9l.9-7.4Z" />
                        </svg>
                    </span>

                    <span class="card-sep" aria-hidden="true" />

                    <div class="card-titles">
                        <h3 class="card-title">quick actions</h3>
                        <p class="card-subtitle">jump straight to a feature</p>
                    </div>
                </header>

                <div class="actions">
                    <v-btn small depressed class="action action--primary" to="/inference">
                        <v-icon small left>mdi-upload</v-icon>
                        new inference job
                    </v-btn>

                    <v-btn small outlined class="action" to="/map">
                        <v-icon small left>mdi-map-outline</v-icon>
                        open map
                    </v-btn>

                    <v-btn small outlined class="action" to="/analytics">
                        <v-icon small left>mdi-chart-box-outline</v-icon>
                        analytics
                    </v-btn>

                    <v-btn small outlined class="action" to="/models">
                        <v-icon small left>mdi-brain</v-icon>
                        model metrics
                    </v-btn>
                </div>

                <div class="action-stats">
                    <div class="action-stat action-stat--red">
                        <span class="action-stat-icon"><v-icon small>mdi-target</v-icon></span>
                        <span class="action-stat-copy">
                            <span class="action-stat-label">footprint iou</span>
                            <span class="action-stat-value">{{ iouLabel }}</span>
                        </span>
                    </div>

                    <div class="action-stat action-stat--purple">
                        <span class="action-stat-icon"><v-icon small>mdi-layers-triple-outline</v-icon></span>
                        <span class="action-stat-copy">
                            <span class="action-stat-label">offline tiles</span>
                            <span class="action-stat-value">{{ tileCount }}</span>
                        </span>
                    </div>

                    <div class="action-stat action-stat--blue">
                        <span class="action-stat-icon"><v-icon small>mdi-image-outline</v-icon></span>
                        <span class="action-stat-copy">
                            <span class="action-stat-label">tile alignment</span>
                            <span class="action-stat-value">{{ drgbLabel }}</span>
                        </span>
                    </div>

                    <div class="action-stat action-stat--green">
                        <span class="action-stat-icon"><v-icon small>mdi-crop-free</v-icon></span>
                        <span class="action-stat-copy">
                            <span class="action-stat-label">min area</span>
                            <span class="action-stat-value">{{ minArea }} px</span>
                        </span>
                    </div>
                </div>
            </GlowCard>
        </div>
    </div>
</template>

<script lang="ts">
import {
    Component,
    Vue,
    Watch,
} from "vue-property-decorator";

import { getModule } from "vuex-module-decorators";
import { AppModule } from "@/store/app";

import DonutChart from "@/ui/components/DonutChart.vue";
import GlowCard from "@/ui/components/GlowCard.vue";
import JobTable from "@/ui/components/JobTable.vue";
import RingGauge from "@/ui/components/RingGauge.vue";
import StatCard from "@/ui/components/StatCard.vue";
import ZoneBars from "@/ui/components/ZoneBars.vue";

import {
    IChartSegment,
    IEvaluation,
    IZoneBarRow,
    IZoneInventory,
} from "@/models";
import {
    SEVERITY_COLORS,
    formatDuration,
    shortScene,
    zoneName,
} from "@/modules/format";

type StepState = "ok" | "warn" | "bad";

type LogLineType = "cmd" | "ok" | "info" | "url" | "warn";

interface IPipelineStep {
    label: string;
    detail: string;
    state: StepState;
    icon: string;
}

interface IServiceRow {
    label: string;
    value: string;
    state: StepState;
}

interface ISeriesPoint {
    label: string;
    value: number;
}

interface IBarPoint extends ISeriesPoint {
    /** Bar height as a percentage of the tallest zone. */
    height: number;
}

interface IQualityRing {
    label: string;
    value: number;
    display: string;
    tone: string;
    hint: string;
    icon: string;
}

interface ILogLine {
    type: LogLineType;
    text: string;
}

const EMPTY_EVALUATION: IEvaluation = {
    measured_on: "",
    scenes: [],
    footprint_iou_mean: 0,
    footprint_iou_by_scene: {},
    buildings_classified: 0,
    min_area_sweep: [],
    selected_min_area: 0,
    tile_alignment_drgb_mean: 0,
    notes: [],
};

@Component({
    components: {
        DonutChart,
        GlowCard,
        JobTable,
        RingGauge,
        StatCard,
        ZoneBars,
    },
})
export default class DashboardView extends Vue {
    private readonly app = getModule(AppModule);

    /** Index of the chart point under the pointer, -1 when the chart is idle. */
    private chartHover = -1;

    private barHover = -1;

    private stageHover = -1;

    /** How many terminal lines have been printed so far. */
    private logRevealed = 0;

    private logTimer: number | null = null;

    private countFrame: number | null = null;

    /** Counters that animate up to their target once diagnostics arrive. */
    private animated = {affected: 0, tiles: 0};

    private get diagnostics() {
        return this.app.diagnostics;
    }

    private get health() {
        return this.app.health;
    }

    private get jobs() {
        return this.app.jobs;
    }

    private get serviceError(): string | null {
        return this.app.serviceError;
    }

    private get zones(): IZoneInventory[] {
        return this.diagnostics?.zones || [];
    }

    private get zoneCount(): number {
        return this.zones.length;
    }

    private get evaluation(): IEvaluation {
        return this.diagnostics?.evaluation || EMPTY_EVALUATION;
    }

    private get minArea(): number {
        return this.diagnostics?.min_area ?? 0;
    }

    private get maxJobs(): number {
        return this.health ? this.health.max_jobs : 0;
    }

    // Nullable values are resolved here: the template compiler rejects ?. and ??.
    private get iouLabel(): string {
        return this.diagnostics ? String(this.diagnostics.evaluation.footprint_iou_mean) : "-";
    }

    private get drgbLabel(): string {
        return this.diagnostics
            ? `dRGB ${this.diagnostics.evaluation.tile_alignment_drgb_mean}`
            : "-";
    }

    private get severeCount(): number {
        return this.sumSeverity("severe");
    }

    private get moderateCount(): number {
        return this.sumSeverity("moderate");
    }

    private get affectedCount(): number {
        return this.zones.reduce((sum, zone) => sum + this.features(zone, "structures-affected"), 0);
    }

    private get intactCount(): number {
        return this.zones.reduce((sum, zone) => sum + this.features(zone, "structures-unaffected"), 0);
    }

    private get tileCount(): number {
        return (this.diagnostics?.imagery || []).reduce((total, zone) => {
            return total + Object.values(zone.roles).reduce((sum, role) => sum + role.tiles, 0);
        }, 0);
    }

    private get severitySegments(): IChartSegment[] {
        return [
            {label: "severe", value: this.severeCount, color: SEVERITY_COLORS.severe},
            {label: "moderate", value: this.moderateCount, color: SEVERITY_COLORS.moderate},
            {label: "intact", value: this.intactCount, color: SEVERITY_COLORS.intact},
        ];
    }

    private get affectedByZone(): IZoneBarRow[] {
        return this.zones
            .map(zone => {
                const severity = zone.layers["structures-affected"]?.severity || {};

                return {
                    label: zoneName(zone.zone_id),
                    total: this.features(zone, "structures-affected"),
                    severe: severity.severe || 0,
                    moderate: severity.moderate || 0,
                };
            })
            .sort((a, b) => b.total - a.total);
    }

    /** Legend for the stacked zone bars; kept beside the data so the two cannot drift apart. */
    private get severityLegend() {
        return [
            {label: "severe", color: SEVERITY_COLORS.severe},
            {label: "moderate", color: SEVERITY_COLORS.moderate},
        ];
    }

    private get apiReady(): boolean {
        return !!this.health && this.health.status === "ready";
    }

    /* ---- hero card ----------------------------------------------------------- */

    /** Affected buildings per indexed zone, most affected first. */
    private get heroSeries(): ISeriesPoint[] {
        return this.zones
            .map(zone => ({
                label: shortScene(zone.zone_id),
                value: this.features(zone, "structures-affected"),
            }))
            .filter(point => point.value > 0)
            .sort((a, b) => b.value - a.value);
    }

    private get chartPoints(): Array<{x: number; y: number}> {
        const series = this.heroSeries;
        if(series.length < 2) {
            return [];
        }

        // Plotted on a 0-100 viewBox against the rounded axis top, with headroom left at the
        // bottom so the dot and the bubble never clip.
        const top = this.chartScale.top;

        return series.map((point, index) => ({
            x: (index / (series.length - 1)) * 100,
            y: 92 - (point.value / top) * 76,
        }));
    }

    /**
     * A round top for the y-axis. Without it a peak of 208 would put the curve against the frame
     * edge and leave the labels reading 52 / 104 / 156, which nobody wants to scan. Five
     * divisions keeps the headroom small enough that the curve still fills the plot.
     */
    private get chartScale(): {top: number; step: number} {
        return this.niceScale(Math.max(1, ...this.heroSeries.map(point => point.value)), 5);
    }

    /** A round top and step for any value axis, so the labels land on readable numbers. */
    private niceScale(peak: number, divisions: number): {top: number; step: number} {
        const raw = Math.max(1, peak) / divisions;
        const magnitude = Math.pow(10, Math.floor(Math.log10(raw)));
        const normalised = raw / magnitude;
        const multiple = normalised <= 1 ? 1 : normalised <= 2 ? 2 : normalised <= 5 ? 5 : 10;
        const step = Math.max(1, multiple * magnitude);

        return {top: Math.ceil(Math.max(1, peak) / step) * step, step};
    }

    /** Y-axis labels, bottom-up, in the same 0-100 space as the curve. */
    private get chartTicks(): Array<{label: string; value: number; y: number}> {
        const {top, step} = this.chartScale;
        const ticks: Array<{label: string; value: number; y: number}> = [];

        for(let value = 0; value <= top + 0.001; value += step) {
            const rounded = Math.round(value);

            ticks.push({
                label: String(rounded),
                value: rounded,
                y: 92 - (value / top) * 76,
            });
        }

        return ticks;
    }

    /** Cubic-smoothed line through the zone points, in the same 0-100 space. */
    private get chartLine(): string {
        const points = this.chartPoints;

        return points.reduce((path, point, index) => {
            if(index === 0) {
                return `M ${point.x.toFixed(2)} ${point.y.toFixed(2)}`;
            }

            const previous = points[index - 1];
            const mid = ((previous.x + point.x) / 2).toFixed(2);

            return `${path} C ${mid} ${previous.y.toFixed(2)}, ${mid} ${point.y.toFixed(2)}, ` +
                `${point.x.toFixed(2)} ${point.y.toFixed(2)}`;
        }, "");
    }

    private get chartArea(): string {
        const line = this.chartLine;
        return line ? `${line} L 100 100 L 0 100 Z` : "";
    }

    private get hoveredPoint(): {x: number; y: number} | null {
        return this.chartHover >= 0 && this.chartHover < this.chartPoints.length
            ? this.chartPoints[this.chartHover]
            : null;
    }

    private get hoveredZone(): ISeriesPoint | null {
        return this.chartHover >= 0 ? this.heroSeries[this.chartHover] || null : null;
    }

    /** Keeps the bubble inside the card when the pointer is on the first or the last point. */
    private get tipLeft(): string {
        const point = this.hoveredPoint;
        return `clamp(58px, ${point ? point.x : 50}%, calc(100% - 58px))`;
    }

    /** A dot near the top of the plot has no room above it, so the bubble drops underneath. */
    private get tipBelow(): boolean {
        const point = this.hoveredPoint;
        return !!point && point.y < 38;
    }

    private get tipTop(): string {
        const point = this.hoveredPoint;
        return `${point ? point.y : 0}%`;
    }

    private get heroAxis(): {start: string; end: string} {
        const series = this.heroSeries;
        if(!series.length) {
            return {start: "no zones indexed yet", end: ""};
        }

        return {
            start: series[0].label,
            end: series[series.length - 1].label,
        };
    }

    /* ---- model quality card -------------------------------------------------- */

    /**
     * Four real scores, never placeholders: the scene IoU from the local evaluation plus the
     * recall, precision and F1 recorded next to the checkpoints themselves.
     */
    private get qualityRings(): IQualityRing[] {
        const rings: IQualityRing[] = [];
        const models = this.diagnostics ? this.diagnostics.models : [];
        const stage1 = models.find(model => model.role === "stage1");
        const stage2 = models.find(model => model.role === "stage2");

        if(this.diagnostics) {
            rings.push(this.makeRing(
                "scene iou",
                this.evaluation.footprint_iou_mean,
                `footprint IoU ${this.evaluation.footprint_iou_mean} across ` +
                `${this.evaluation.scenes.length} demo scenes`,
                "layers",
            ));
        }

        const stage1Metrics = stage1 ? stage1.meta.metrics : undefined;
        if(stage1Metrics) {
            if(typeof stage1Metrics.footprint_recall === "number") {
                rings.push(this.makeRing("recall", stage1Metrics.footprint_recall,
                    `stage-1 footprint recall ${stage1Metrics.footprint_recall} on the validation split`,
                    "target"));
            }

            if(typeof stage1Metrics.footprint_precision === "number") {
                rings.push(this.makeRing("precision", stage1Metrics.footprint_precision,
                    `stage-1 footprint precision ${stage1Metrics.footprint_precision} on the validation split`,
                    "bars"));
            }
        }

        const stage2Metrics = stage2 ? stage2.meta.metrics : undefined;
        if(stage2Metrics) {
            const score = stage2Metrics.matthew_macro_f1_3class_merged ||
                stage2Metrics.matthew_macro_f1_4class;

            if(typeof score === "number") {
                rings.push(this.makeRing("stage-2 f1", score,
                    `stage-2 macro F1 with severe and moderate merged: ${score}`,
                    "stack"));
            }
        }

        if(!rings.length) {
            rings.push(this.makeRing("pending", 0, "waiting for /diagnostics", "bars"));
        }

        return rings;
    }

    private get qualitySource(): string {
        if(!this.diagnostics) {
            return "waiting for /diagnostics";
        }

        return "demo scenes + checkpoint metadata";
    }

    /* ---- last run card ------------------------------------------------------- */

    private get logLines(): ILogLine[] {
        const lines: ILogLine[] = [];
        const job = this.jobs.length ? this.jobs[0] : null;

        if(job) {
            lines.push({type: "cmd", text: `POST /predict/disaster · ${shortScene(job.zone_id)}`});
            lines.push({
                type: "info",
                text: `status ${job.status} · ${job.tiles} tiles · ${formatDuration(job.duration_seconds)}`,
            });

            if(job.status === "succeeded") {
                lines.push({
                    type: "ok",
                    text: `${job.affected_structures} affected · ${job.unaffected_structures} intact`,
                });
                lines.push({
                    type: "ok",
                    text: `${job.severe_structures} severe · ${job.moderate_structures} moderate`,
                });
            }

            (job.artifacts || []).slice(0, 3).forEach(artifact => {
                lines.push({type: "url", text: artifact});
            });

            if(job.warning) {
                lines.push({type: "warn", text: job.warning});
            }

            if(job.error) {
                lines.push({type: "warn", text: job.error});
            }

            return lines;
        }

        /*
         * A fresh queue is empty, so the card reports the call the UI makes and what the artefacts
         * on disk already prove. It never types out a run that did not happen.
         */
        const models = this.diagnostics ? this.diagnostics.models : [];
        const loaded = models.filter(model => model.exists).length;
        const reachable = !!(this.health && this.health.geoserv_reachable);
        const status = this.health ? this.health.status : "offline";

        lines.push({type: "cmd", text: "POST /predict/disaster"});
        lines.push({
            type: "info",
            text: `api ${status} · mode ${this.health?.mode || "-"} · ${this.minArea} px min-area`,
        });
        lines.push({type: "ok", text: `${this.affectedCount + this.intactCount} footprints classified`});
        lines.push({type: "ok", text: `${this.affectedCount} affected · ${this.intactCount} intact`});
        lines.push({type: "ok", text: `${this.zoneCount} zones indexed as geojson`});
        lines.push({type: "info", text: `${this.tileCount} offline tiles bundled with the ui`});
        lines.push({
            type: reachable ? "ok" : "warn",
            text: reachable ? "geoserv index reachable" : "geoserv unreachable",
        });
        lines.push({type: "url", text: this.health ? this.health.geoserv_url : "-"});
        lines.push({
            type: loaded === models.length && models.length > 0 ? "ok" : "warn",
            text: `${loaded}/${models.length} checkpoints present`,
        });

        return lines;
    }

    private get visibleLogLines(): ILogLine[] {
        return this.logLines.slice(0, this.logRevealed);
    }

    private get logTyping(): boolean {
        return this.logRevealed < this.logLines.length;
    }

    /* ---- imagery card -------------------------------------------------------- */

    /*
     * Tiles per zone are near-identical by construction (every scene ships the same pyramid), so a
     * per-zone strip would draw four flat bars. The zoom pyramid is where the data actually moves:
     * a handful of low-zoom tiles and hundreds at z19.
     */
    private get imageryBars(): IBarPoint[] {
        const byZoom: { [zoom: string]: number } = {};

        (this.diagnostics ? this.diagnostics.imagery : []).forEach(zone => {
            Object.values(zone.roles).forEach(role => {
                Object.keys(role.by_zoom).forEach(zoom => {
                    byZoom[zoom] = (byZoom[zoom] || 0) + role.by_zoom[zoom];
                });
            });
        });

        const rows = Object.keys(byZoom)
            .map(zoom => ({label: `z${zoom}`, value: byZoom[zoom]}))
            .filter(row => row.value > 0)
            .sort((a, b) => Number(a.label.slice(1)) - Number(b.label.slice(1)));

        const peak = Math.max(1, ...rows.map(row => row.value));
        const {top} = this.niceScale(peak, 8);

        // Heights are read against the axis top, not the peak, so a bar lines up with its gridline.
        return rows.map(row => ({
            ...row,
            height: Math.max(2, Math.round((row.value / top) * 100)),
        }));
    }

    /** The tile pyramid's axis: eight divisions keeps a 512 peak on a 0 … 600, 100-step scale. */
    private get barsScale(): {top: number; step: number} {
        return this.niceScale(Math.max(1, ...this.imageryBars.map(point => point.value)), 8);
    }

    /** Bar-axis labels, bottom-up, as a percentage of the plot height. */
    private get barsTicks(): Array<{label: string; value: number; y: number}> {
        const {top, step} = this.barsScale;
        const ticks: Array<{label: string; value: number; y: number}> = [];

        for(let value = 0; value <= top + 0.001; value += step) {
            const rounded = Math.round(value);

            ticks.push({
                label: String(rounded),
                value: rounded,
                y: (value / top) * 100,
            });
        }

        return ticks;
    }

    /** The pyramid always climbs, so the peak is the last bar rather than the first. */
    private get peakBar(): number {
        const bars = this.imageryBars;

        return bars.reduce((best, bar, index) => bar.value > bars[best].value ? index : best, bars.length ? 0 : -1);
    }

    private get barCaption(): string {
        const bar = this.barHover >= 0 ? this.imageryBars[this.barHover] : null;
        if(bar) {
            const total = this.imageryBars.reduce((sum, point) => sum + point.value, 0);
            const share = total > 0 ? Math.round((bar.value / total) * 100) : 0;
            return `${bar.label} · ${bar.value} tiles · ${share}% of the pyramid`;
        }

        return `${this.imageryBars.length} zoom levels · before + after · hover a bar`;
    }

    /* ---- pipeline card ------------------------------------------------------- */

    private get activeStageDetail(): string {
        const step = this.stageHover >= 0 ? this.pipeline[this.stageHover] : null;

        // The header already carries the standing subtitle, so this line only speaks when a tile
        // is under the pointer and has something of its own to say.
        return step ? step.detail : "";
    }

    private get pipeline(): IPipelineStep[] {
        const models = this.diagnostics?.models || [];
        const loaded = models.filter(model => model.exists).length;

        return [
            {
                label: "GeoTIFF pair",
                detail: `before + after, up to ${this.diagnostics?.max_upload_mb ?? "-"} MB each`,
                state: "ok",
                icon: "mdi-image-multiple-outline",
            },
            {
                label: "Stage-1 footprints",
                detail: `unet resnet34 · min-area ${this.minArea} px`,
                state: models.find(model => model.role === "stage1")?.exists ? "ok" : "bad",
                icon: "mdi-vector-square",
            },
            {
                label: "Stage-2 damage",
                detail: "4-class classifier · severity + probability per building",
                state: models.find(model => model.role === "stage2")?.exists ? "ok" : "bad",
                icon: "mdi-shield-alert-outline",
            },
            {
                label: "GeoJSON artefacts",
                detail: `${this.affectedCount + this.intactCount} features across ${this.zoneCount} zones`,
                state: this.zoneCount > 0 ? "ok" : "warn",
                icon: "mdi-code-json",
            },
            {
                label: "GeoServ index",
                detail: this.health?.geoserv_url || "not configured",
                state: this.health?.geoserv_reachable ? "ok" : "bad",
                icon: "mdi-database-cog-outline",
            },
            {
                label: "Map render",
                detail: `${this.tileCount} offline tiles + heatmap + polygons`,
                state: this.tileCount > 0 ? "ok" : "warn",
                icon: "mdi-map-legend",
            },
            {
                label: "Loaded models",
                detail: `${loaded}/${models.length} checkpoints present`,
                state: loaded === models.length && models.length > 0 ? "ok" : "warn",
                icon: "mdi-brain",
            },
        ];
    }

    private get serviceRows(): IServiceRow[] {
        return [
            {
                label: "inference api",
                value: this.health ? this.health.status : "offline",
                state: this.health?.status === "ready" ? "ok" : "bad",
            },
            {
                label: "job queue",
                value: `${this.health?.active_jobs ?? 0} active / ${this.health?.max_jobs ?? 0} slots`,
                state: "ok",
            },
            {
                label: "geoserv",
                value: this.health?.geoserv_reachable ? "indexed" : "unreachable",
                state: this.health?.geoserv_reachable ? "ok" : "bad",
            },
            {
                label: "models missing",
                value: String(this.health?.missing_models?.length ?? 0),
                state: (this.health?.missing_models?.length ?? 0) === 0 ? "ok" : "warn",
            },
            {
                label: "mode",
                value: this.health?.mode || this.diagnostics?.mode || "-",
                state: "ok",
            },
            {
                label: "data dir",
                value: this.diagnostics?.data_dir || "-",
                state: "ok",
            },
        ];
    }

    private get syncedLabel(): string {
        const at = this.app.lastSyncedAt;
        if(!at) {
            return "never";
        }

        const seconds = Math.round((Date.now() - at) / 1000);
        return seconds < 5 ? "just now" : `${seconds}s ago`;
    }

    private features(zone: IZoneInventory, layer: string): number {
        return zone.layers[layer]?.features || 0;
    }

    private sumSeverity(label: string): number {
        return this.zones.reduce((sum, zone) => {
            return sum + (zone.layers["structures-affected"]?.severity?.[label] || 0);
        }, 0);
    }

    private makeRing(label: string, ratio: number, hint: string, icon: string): IQualityRing {
        const value = Math.max(0, Math.min(100, Math.round(ratio * 100)));

        let tone = "bad";
        if(value >= 70) {
            tone = "ok";
        } else if(value >= 45) {
            tone = "warn";
        }

        return {
            label,
            value,
            display: "",
            tone,
            hint,
            icon,
        };
    }

    private lineMark(type: LogLineType): string {
        switch(type) {
            case "cmd":
                return "$";
            case "ok":
                return "✓";
            case "warn":
                return "!";
            case "url":
                return "●";
            default:
                return "›";
        }
    }

    private onChartMove(event: MouseEvent): void {
        const points = this.chartPoints;
        if(!points.length) {
            return;
        }

        const target = event.currentTarget as HTMLElement;
        const rect = target.getBoundingClientRect();
        const ratio = Math.min(Math.max((event.clientX - rect.left) / rect.width, 0), 1);

        this.chartHover = Math.round(ratio * (points.length - 1));
    }

    /** Eases the two headline counters from wherever they are to the values just loaded. */
    private countUp(): void {
        const target = {affected: this.affectedCount, tiles: this.tileCount};
        const from = {...this.animated};

        if(this.countFrame !== null) {
            window.cancelAnimationFrame(this.countFrame);
            this.countFrame = null;
        }

        if(window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
            this.animated = target;
            return;
        }

        const started = performance.now();
        const duration = 900;

        const step = (now: number): void => {
            const progress = Math.min((now - started) / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3);

            this.animated = {
                affected: Math.round(from.affected + (target.affected - from.affected) * eased),
                tiles: Math.round(from.tiles + (target.tiles - from.tiles) * eased),
            };

            this.countFrame = progress < 1 ? window.requestAnimationFrame(step) : null;
        };

        this.countFrame = window.requestAnimationFrame(step);
    }

    /** Types the log out one line at a time, the way a terminal would print it. */
    private startLog(): void {
        this.stopLog();

        this.logRevealed = 1;
        this.logTimer = window.setInterval(() => {
            if(this.logRevealed >= this.logLines.length) {
                this.stopLog();
                return;
            }

            this.logRevealed += 1;
        }, 260);
    }

    private stopLog(): void {
        if(this.logTimer !== null) {
            window.clearInterval(this.logTimer);
            this.logTimer = null;
        }
    }

    @Watch("affectedCount")
    private onAffectedChanged(): void {
        this.countUp();
    }

    @Watch("tileCount")
    private onTilesChanged(): void {
        this.countUp();
    }

    mounted(): void {
        this.startLog();
        this.countUp();
    }

    beforeDestroy(): void {
        this.stopLog();

        if(this.countFrame !== null) {
            window.cancelAnimationFrame(this.countFrame);
            this.countFrame = null;
        }
    }
}
</script>

<style lang="scss" scoped>
.dashboard-bottom {
    margin-top: 16px;
}

/*
 * The closing band is deliberately uneven: the jobs table carries eight columns and needs the room,
 * so it takes the wider side and the action card sits beside it, as in the reference. Below 1180px
 * the pair stacks rather than squeezing the table.
 */
.dashboard-last {
    grid-template-columns: minmax(0, 1.55fr) minmax(0, 1fr);
    margin-top: 16px;
    padding-bottom: 10px;
}

@media (max-width: 1180px) {
    .dashboard-last {
        grid-template-columns: minmax(0, 1fr);
    }
}

/*
 * Bento: four columns on a wide screen. The hero takes a 2x2 block, the model-quality card takes
 * the other two columns beside it, the terminal and the tile counter fill the second row and the
 * stage strip closes the band across the whole width. Rows have a 232px floor and grow when a card
 * needs more room, which is what lets the quality rings keep their size.
 */
.bento {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    grid-auto-rows: minmax(232px, auto);
    gap: 16px;
    margin-top: 16px;
}

.bento-hero {
    grid-column: span 2;
    grid-row: span 2;
}

.bento-rings {
    grid-column: span 2;
}

.bento-term {
    grid-column: span 1;
}

.bento-bars {
    grid-column: span 1;
}

.bento-stack {
    grid-column: span 4;
}

@media (max-width: 1280px) {
    .bento {
        grid-template-columns: repeat(2, minmax(0, 1fr));
        grid-auto-rows: auto;
    }

    .bento-hero {
        grid-column: span 2;
        grid-row: auto;
        min-height: 400px;
    }

    .bento-term {
        grid-row: auto;
        min-height: 300px;
    }

    .bento-rings {
        min-height: 260px;
    }

    .bento-bars {
        min-height: 210px;
    }

    .bento-stack {
        grid-column: span 2;
        min-height: 210px;
    }
}

@media (max-width: 780px) {
    .bento {
        grid-template-columns: minmax(0, 1fr);
    }

    .bento-hero,
    .bento-term,
    .bento-rings,
    .bento-bars,
    .bento-stack {
        grid-column: span 1;
    }
}

/* "Live" is a promise about the 10s poll, so it is stated in the palette's own status colour. */
.live-pill {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    margin-left: auto;
    padding: 6px 14px;
    border-radius: 999px;
    border: 1px solid rgba(52, 211, 153, 0.45);
    background: rgba(52, 211, 153, 0.1);
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--rahat-ok);
}

.live-pill--down {
    border-color: rgba(255, 59, 74, 0.45);
    background: rgba(255, 59, 74, 0.1);
    color: #ff6b78;
}

.live-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: currentColor;
    box-shadow: 0 0 0 3px rgba(52, 211, 153, 0.16), 0 0 10px currentColor;
    animation: bento-pulse 1.8s ease-in-out infinite;
}

.live-pill--down .live-dot {
    box-shadow: 0 0 0 3px rgba(255, 59, 74, 0.16), 0 0 10px currentColor;
}

/*
 * The hero is one reading surface, not a tile. Lifting it 2px and sweeping a spotlight under the
 * cursor made the whole section look like it was shifting while the pointer moved across the data,
 * and it read as if the total had a hover state of its own. It stays perfectly still; the boxes
 * inside carry the feedback instead.
 */
.bento .bento-hero:hover {
    transform: none;
}

.bento-hero::v-deep .glow-spot,
.bento-hero::v-deep .glow-grid,
.bento-hero::v-deep .glow-edge-lit {
    opacity: 0;
    transition: none;
}

/* ---- hero: totals, the per-zone curve and the service strip ------------------- */

.hero-figures {
    position: relative;
    z-index: 1;
    display: flex;
    align-items: stretch;
    gap: 12px;
    margin: 2px 0 14px;
}

/*
 * At rest the total is the peer of the severity well beside it: same hairline, same faint tint.
 * The crimson fill is the hover reward, and it fades in through a pseudo layer because a
 * gradient cannot be interpolated on the element itself.
 */
.hero-main {
    position: relative;
    isolation: isolate;
    display: flex;
    align-items: baseline;
    gap: 10px;
    padding: 8px 20px 11px;
    border-radius: 14px;
    border: 1px solid rgba(255, 255, 255, 0.08);
    background: rgba(255, 255, 255, 0.022);
    transition: border-color 260ms ease, box-shadow 260ms ease;
}

.hero-main::before {
    content: "";
    position: absolute;
    inset: -1px;
    z-index: -1;
    border-radius: inherit;
    background: linear-gradient(140deg, rgba(122, 12, 19, 0.66), rgba(38, 7, 9, 0.88));
    opacity: 0;
    transition: opacity 260ms ease;
}

.hero-main:hover {
    border-color: rgba(255, 59, 74, 0.5);
    box-shadow: 0 16px 34px -20px rgba(255, 59, 74, 0.9),
        inset 0 1px 0 rgba(255, 255, 255, 0.07);
}

.hero-main:hover::before {
    opacity: 1;
}

.hero-value {
    font-size: 40px;
    font-weight: 700;
    line-height: 1;
    letter-spacing: -0.025em;
    font-variant-numeric: tabular-nums;
    color: var(--rahat-text-bright);
}

.hero-unit {
    font-size: 11.5px;
    color: rgba(251, 239, 240, 0.72);
}

.hero-split {
    display: flex;
    flex: 1 1 auto;
    align-items: center;
    min-width: 0;
    padding: 6px 2px;
    border-radius: 14px;
    border: 1px solid rgba(255, 255, 255, 0.08);
    background: rgba(255, 255, 255, 0.022);
}

.split-item {
    display: flex;
    flex: 1 1 0;
    align-items: center;
    gap: 10px;
    min-width: 0;
    padding: 0 14px;
    border-radius: 10px;
    transition: background-color 220ms ease;
}

.split-item:hover {
    background: rgba(255, 255, 255, 0.04);
}

.split-item + .split-item {
    border-left: 1px solid rgba(255, 255, 255, 0.07);
}

.split-icon {
    display: grid;
    flex: 0 0 auto;
    place-items: center;
    width: 32px;
    height: 32px;
    border-radius: 10px;
}

.split-icon svg {
    width: 16px;
    height: 16px;
    fill: none;
    stroke: currentColor;
    stroke-width: 1.7;
    stroke-linecap: round;
    stroke-linejoin: round;
}

.split-icon--severe {
    border: 1px solid rgba(255, 59, 74, 0.34);
    background: rgba(255, 59, 74, 0.14);
    color: #ff6b78;
}

.split-icon--moderate {
    border: 1px solid rgba(251, 185, 49, 0.32);
    background: rgba(251, 185, 49, 0.13);
    color: #fbb931;
}

.split-icon--intact {
    border: 1px solid rgba(52, 211, 153, 0.32);
    background: rgba(52, 211, 153, 0.13);
    color: #34d399;
}

.split-copy {
    display: flex;
    flex-direction: column;
    min-width: 0;
}

.split-copy b {
    font-size: 17px;
    font-weight: 700;
    line-height: 1.15;
    font-variant-numeric: tabular-nums;
    color: var(--rahat-text-bright);
}

.split-copy i {
    font-style: normal;
    font-size: 10.5px;
    color: var(--rahat-text-faint);
}

.hero-chart {
    position: relative;
    z-index: 1;
    display: flex;
    flex: 1 1 auto;
    gap: 10px;
    min-height: 158px;
}

.hero-yaxis {
    position: relative;
    flex: 0 0 26px;
    font-size: 9.5px;
    font-variant-numeric: tabular-nums;
    color: var(--rahat-text-faint);
}

.hero-yaxis span {
    position: absolute;
    right: 0;
    transform: translateY(-50%);
    line-height: 1;
}

.hero-plot {
    position: relative;
    flex: 1 1 auto;
    min-width: 0;
    cursor: crosshair;
}

.hero-svg {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    overflow: visible;
}

.hero-svg line {
    stroke: rgba(255, 255, 255, 0.075);
    stroke-width: 1;
}

/* The zero line closes the plot, so it is the one gridline that is not dashed. */
.hero-svg .hero-grid--base {
    stroke: rgba(255, 255, 255, 0.16);
    stroke-dasharray: none;
}

.hero-line {
    fill: none;
    stroke: #ff3b4a;
    stroke-width: 2;
    stroke-linecap: round;
    filter: drop-shadow(0 0 7px rgba(255, 59, 74, 0.65));
}

.hero-guide {
    stroke: rgba(255, 59, 74, 0.45);
    stroke-width: 1;
    stroke-dasharray: 3 3;
}

/* Every zone keeps a node on the curve, so the line reads as data points and not a blob. */
.hero-node {
    position: absolute;
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #fff;
    box-shadow: 0 0 0 2px rgba(255, 59, 74, 0.9), 0 0 12px rgba(255, 59, 74, 0.8);
    transform: translate(-50%, -50%);
    pointer-events: none;
}

.hero-dot {
    position: absolute;
    width: 11px;
    height: 11px;
    border-radius: 50%;
    border: 2px solid #fff;
    background: #ff3b4a;
    box-shadow: 0 0 16px rgba(255, 59, 74, 0.95);
    transform: translate(-50%, -50%);
    pointer-events: none;
}

/* The design system's tooltip: ink bubble, pale rose lettering, caret pointing at the dot. */
.hero-tip {
    position: absolute;
    display: flex;
    flex-direction: column;
    gap: 1px;
    padding: 6px 9px;
    border-radius: 8px;
    border: 1px solid rgba(251, 239, 240, 0.16);
    background: rgba(26, 5, 7, 0.94);
    box-shadow: 0 10px 26px rgba(0, 0, 0, 0.4);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    transform: translate(-50%, calc(-100% - 12px));
    white-space: nowrap;
    pointer-events: none;
    z-index: 2;
}

.hero-tip--below {
    transform: translate(-50%, 14px);
}

.hero-tip::after {
    content: "";
    position: absolute;
    left: 50%;
    bottom: -4px;
    width: 8px;
    height: 8px;
    background: rgba(26, 5, 7, 0.94);
    border-right: 1px solid rgba(251, 239, 240, 0.16);
    border-bottom: 1px solid rgba(251, 239, 240, 0.16);
    transform: translateX(-50%) rotate(45deg);
}

.hero-tip--below::after {
    top: -4px;
    bottom: auto;
    border-right: none;
    border-bottom: none;
    border-top: 1px solid rgba(251, 239, 240, 0.16);
    border-left: 1px solid rgba(251, 239, 240, 0.16);
}

.tip-zone {
    font-size: 9.5px;
    letter-spacing: 0.05em;
    color: rgba(251, 239, 240, 0.62);
}

.tip-value {
    font-size: 11.5px;
    font-weight: 600;
    font-variant-numeric: tabular-nums;
    color: var(--crimson-pale);
}

.hero-axis {
    position: relative;
    z-index: 1;
    display: flex;
    justify-content: space-between;
    gap: 12px;
    margin: 8px 0 0 36px;
    font-size: 10px;
    color: var(--rahat-text-faint);
}

.hero-axis span {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

/* The service strip sits in its own well so it reads as diagnostics, not as page copy. */
.svc-grid {
    position: relative;
    z-index: 1;
    list-style: none;
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0 30px;
    margin: 14px 0 0;
    padding: 8px 16px;
    border-radius: 14px;
    border: 1px solid rgba(255, 255, 255, 0.08);
    background: rgba(255, 255, 255, 0.022);
}

/* One hairline between the two columns, inset from the panel edges. */
.svc-grid::after {
    content: "";
    position: absolute;
    top: 12px;
    bottom: 12px;
    left: 50%;
    width: 1px;
    background: rgba(255, 255, 255, 0.07);
}

.svc-row {
    display: flex;
    align-items: center;
    gap: 9px;
    min-width: 0;
    padding: 7px 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    font-size: 11.5px;
    transition: background-color 220ms ease;
}

.svc-row:nth-last-child(-n + 2) {
    border-bottom: none;
}

.svc-row:hover {
    background: var(--rahat-accent-soft);
}

/* The row is the hit area; the pill is the part that answers. */
.svc-row:hover .svc-value {
    border-color: rgba(255, 59, 74, 0.42);
    color: var(--rahat-text-bright);
}

.svc-dot {
    width: 6px;
    height: 6px;
    flex: 0 0 auto;
    border-radius: 50%;
    background: var(--rahat-text-faint);
}

.svc-dot--ok {
    background: var(--rahat-ok);
    box-shadow: 0 0 8px var(--rahat-ok);
}

.svc-dot--warn {
    background: var(--rahat-warn);
    box-shadow: 0 0 8px var(--rahat-warn);
}

.svc-dot--bad {
    background: var(--rahat-danger);
    box-shadow: 0 0 8px var(--rahat-danger);
}

.svc-label {
    color: var(--rahat-text);
}

.svc-value {
    margin-left: auto;
    max-width: 62%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    padding: 2px 9px;
    border-radius: 999px;
    border: 1px solid rgba(255, 255, 255, 0.1);
    background: rgba(255, 255, 255, 0.04);
    font-family: var(--rahat-mono);
    font-size: 9.8px;
    color: var(--rahat-text);
}

.hero-foot {
    position: relative;
    z-index: 1;
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 12px 0 0;
    font-size: 10.5px;
    color: var(--rahat-text-faint);
}

.hero-foot svg {
    width: 13px;
    height: 13px;
    flex: 0 0 auto;
    fill: none;
    stroke: currentColor;
    stroke-width: 1.7;
    stroke-linecap: round;
    stroke-linejoin: round;
}

/* On cream the resting total is ink; only the crimson hover fill carries white. */
html.light .hero-main {
    border-color: rgba(100, 13, 20, 0.14);
    background: rgba(100, 13, 20, 0.03);
}

html.light .hero-main:hover .hero-value {
    color: #fff;
}

html.light .hero-main:hover .hero-unit {
    color: rgba(255, 255, 255, 0.82);
}

html.light .live-pill {
    border-color: rgba(4, 120, 87, 0.35);
    background: rgba(4, 120, 87, 0.1);
}

html.light .hero-split,
html.light .svc-grid {
    border-color: rgba(100, 13, 20, 0.14);
    background: rgba(100, 13, 20, 0.03);
}

html.light .split-item + .split-item {
    border-left-color: rgba(100, 13, 20, 0.1);
}

html.light .split-item:hover {
    background: rgba(100, 13, 20, 0.05);
}

html.light .svc-grid::after {
    background: rgba(100, 13, 20, 0.1);
}

html.light .svc-row {
    border-bottom-color: rgba(100, 13, 20, 0.07);
}

html.light .svc-value {
    border-color: rgba(100, 13, 20, 0.14);
    background: rgba(100, 13, 20, 0.05);
}

html.light .bento-split::v-deep .gdonut-hint,
html.light .bento-split::v-deep .gdonut-detail,
html.light .bento-split::v-deep .gdonut-pill {
    border-color: rgba(100, 13, 20, 0.14);
    background: rgba(100, 13, 20, 0.03);
}

html.light .split-scope {
    border-color: rgba(164, 22, 26, 0.3);
    background: rgba(164, 22, 26, 0.07);
    color: var(--rahat-accent);
}

html.light .hero-svg line {
    stroke: rgba(100, 13, 20, 0.12);
}

html.light .hero-svg .hero-grid--base {
    stroke: rgba(100, 13, 20, 0.24);
}

/* Below this the three severity columns start truncating, so the band goes two-up. */
@media (max-width: 720px) {
    .hero-figures {
        flex-wrap: wrap;
    }

    .hero-main,
    .hero-split {
        flex: 1 1 100%;
    }

    .hero-split {
        flex-wrap: wrap;
        gap: 12px 0;
        padding: 10px 2px;
    }

    .split-item {
        flex: 1 1 46%;
    }

    .split-item + .split-item {
        border-left: none;
    }

    .hero-chart {
        min-height: 140px;
    }
}

.service-alert {
    margin-top: 10px;
    border-radius: 2px;
    font-size: 12px;
}

/* ---- framed cards: model quality and pipeline -------------------------------- */

/*
 * The two wide cards of the band share one frame: a crimson hairline that fades towards the middle
 * of each side, a deep bloom underneath and the corner waves. The smaller cards keep the plain
 * shell so the band still has a hierarchy.
 */
.card-frame {
    overflow: hidden;
    border-radius: 16px;
    box-shadow: 0 20px 54px rgba(120, 10, 18, 0.34),
        inset 0 1px 0 rgba(255, 255, 255, 0.05);
}

/* The shell draws its 1px edge as a flat border colour; these cards replace it with the crimson
   hairline. */
.card-frame::v-deep .glow-edge {
    background: linear-gradient(140deg,
        rgba(255, 90, 105, 0.62),
        rgba(255, 59, 74, 0.16) 42%,
        rgba(255, 59, 74, 0.2) 62%,
        rgba(255, 90, 105, 0.6));
}

.card-frame::v-deep .glow-face {
    border-radius: 15px;
}

/* Concentric hairlines fanning out of the two right-hand corners. They are drawn with a repeating
   radial gradient rather than an SVG so they cost nothing to paint and scale with the card. */
.card-wave {
    position: absolute;
    width: 340px;
    height: 340px;
    border-radius: 50%;
    pointer-events: none;
    background: repeating-radial-gradient(circle at center,
        rgba(255, 59, 74, 0.5) 0 1px,
        transparent 1px 9px);
    -webkit-mask-image: radial-gradient(circle at center, black 36%, transparent 72%);
    mask-image: radial-gradient(circle at center, black 36%, transparent 72%);
    opacity: 0.34;
}

.card-wave--top {
    top: -212px;
    right: -120px;
}

.card-wave--bottom {
    right: -150px;
    bottom: -238px;
    opacity: 0.24;
}

.card-head {
    position: relative;
    z-index: 1;
    display: flex;
    align-items: center;
    gap: 11px;
    margin-bottom: 10px;
}

/* The stacked title pair every framed card shares: name over a one-line role. */
.card-titles {
    display: flex;
    flex-direction: column;
    min-width: 0;
}

.card-mark {
    display: grid;
    place-items: center;
    width: 34px;
    height: 34px;
    border-radius: 10px;
    background: linear-gradient(160deg, #ff4257 0%, #a4161a 78%);
    box-shadow: 0 6px 18px rgba(208, 30, 44, 0.38),
        inset 0 1px 0 rgba(255, 255, 255, 0.32);
    color: #fff;
}

.card-mark svg {
    width: 18px;
    height: 18px;
    fill: currentColor;
}

.card-sep {
    width: 2px;
    height: 24px;
    border-radius: 2px;
    background: linear-gradient(180deg,
        rgba(255, 59, 74, 0.08),
        rgba(255, 59, 74, 0.9),
        rgba(255, 59, 74, 0.08));
}

.card-title {
    margin: 0;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--rahat-text-bright);
}

.card-subtitle {
    overflow: hidden;
    margin: 2px 0 0;
    font-size: 10.5px;
    color: var(--rahat-text-faint);
    white-space: nowrap;
    text-overflow: ellipsis;
}

/* ---- damage split: the donut keeps its own drawing, only the frame is ours ----- */

/*
 * These two cards are reading surfaces like the hero, so they hold still: the donut's slices and
 * the zone rows are the things that react to the pointer, not the frame around them.
 */
.dashboard-bottom .bento-split:hover,
.dashboard-bottom .bento-zones:hover {
    transform: none;
}

.bento-split::v-deep .glow-spot,
.bento-split::v-deep .glow-grid,
.bento-split::v-deep .glow-edge-lit,
.bento-zones::v-deep .glow-spot,
.bento-zones::v-deep .glow-grid,
.bento-zones::v-deep .glow-edge-lit {
    opacity: 0;
    transition: none;
}

.bento-split::v-deep .glow-content,
.bento-zones::v-deep .glow-content {
    height: 100%;
    padding: 18px 20px 20px;
}

/* The chart carries the scope pill in the header now, so its own badge has nothing left to say. */
.bento-split::v-deep .gdonut-head {
    display: none;
}

.bento-split::v-deep .gdonut {
    display: flex;
    flex: 1 1 auto;
    flex-direction: column;
}

.bento-split::v-deep .gdonut-plot {
    display: flex;
    flex: 1 1 auto;
    align-items: center;
    margin-top: 6px;
}

.bento-split::v-deep .gdonut-foot {
    margin-top: 16px;
}

.bento-split::v-deep .gdonut-hint,
.bento-split::v-deep .gdonut-detail {
    margin-top: 0;
    padding: 11px 15px;
    border-radius: 12px;
    border: 1px solid rgba(255, 255, 255, 0.08);
    background: rgba(255, 255, 255, 0.022);
    font-size: 10.5px;
    color: var(--rahat-text-faint);
}

.bento-split::v-deep .hint-dot {
    width: 7px;
    height: 7px;
    box-shadow: 0 0 12px rgba(255, 59, 74, 0.65);
}

.bento-split::v-deep .detail-name {
    font-size: 12px;
    color: var(--rahat-text-bright);
}

.bento-split::v-deep .gdonut-pills {
    gap: 10px;
    margin-top: 14px;
}

.bento-split::v-deep .gdonut-pill {
    padding: 7px 15px;
    border-radius: 999px;
    border: 1px solid rgba(255, 255, 255, 0.1);
    background: rgba(255, 255, 255, 0.03);
    font-size: 10.5px;
}

.bento-split::v-deep .pill-dot {
    width: 9px;
    height: 9px;
}

/* The scope pill states what the ring is measuring; it is a label, not a control. */
.split-scope {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    margin-left: auto;
    padding: 6px 11px 6px 12px;
    border-radius: 999px;
    border: 1px solid rgba(255, 59, 74, 0.36);
    background: rgba(255, 59, 74, 0.08);
    font-size: 9.5px;
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #ff8a94;
    white-space: nowrap;
}

.split-scope svg {
    width: 12px;
    height: 12px;
    fill: none;
    stroke: currentColor;
    stroke-width: 1.9;
    stroke-linecap: round;
}

.split-scope .scope-chevron {
    width: 9px;
    height: 9px;
    opacity: 0.7;
}

/* ---- affected by zone: the rows carry the counts, the header only says which tone is which -- */

.bento-zones::v-deep .zones {
    flex: 1 1 auto;
    height: auto;
    min-height: 0;
    margin-top: 14px;
}

/* The key states the two tones; it is a label, so it does not react to the pointer either. */
.zone-key {
    display: inline-flex;
    align-items: center;
    gap: 14px;
    margin-left: auto;
    padding: 6px 12px;
    border-radius: 999px;
    border: 1px solid rgba(255, 255, 255, 0.09);
    background: rgba(255, 255, 255, 0.022);
}

.zone-key-item {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 9.5px;
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--rahat-text-dim);
    white-space: nowrap;
}

.zone-key-dot {
    display: inline-block;
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--dot);
    box-shadow: 0 0 10px var(--dot);
}

.rings {
    position: relative;
    z-index: 1;
    display: flex;
    flex: 1 1 auto;
    align-items: center;
    justify-content: space-between;
    gap: 0;
    margin: 2px 0 10px;
}

/*
 * Each ring sits in its own cell so the hairline divider between two cells can stop short of the
 * card edges instead of reading as a table border.
 */
.ring-cell {
    position: relative;
    display: flex;
    flex: 1 1 0;
    justify-content: center;
    min-width: 0;
    padding: 0 8px;
}

.ring-cell + .ring-cell::before {
    content: "";
    position: absolute;
    left: 0;
    top: 6%;
    bottom: 16%;
    width: 1px;
    background: linear-gradient(180deg,
        transparent,
        rgba(255, 255, 255, 0.1) 20%,
        rgba(255, 255, 255, 0.1) 80%,
        transparent);
}

html.light .ring-cell + .ring-cell::before {
    background: linear-gradient(180deg,
        transparent,
        rgba(100, 13, 20, 0.14) 20%,
        rgba(100, 13, 20, 0.14) 80%,
        transparent);
}

.quality-note {
    position: relative;
    z-index: 1;
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 0;
    padding: 7px 12px;
    border-radius: 999px;
    border: 1px solid rgba(255, 255, 255, 0.07);
    background: rgba(255, 255, 255, 0.025);
    font-size: 11px;
    color: var(--rahat-text-dim);
}

.quality-note svg {
    flex: 0 0 auto;
    width: 15px;
    height: 15px;
    fill: none;
    stroke: var(--rahat-text-faint);
    stroke-width: 1.6;
    stroke-linecap: round;
}

.quality-note .note-dot {
    fill: var(--rahat-text-faint);
    stroke: none;
}

html.light .quality-note {
    border-color: rgba(100, 13, 20, 0.14);
    background: rgba(100, 13, 20, 0.03);
}

/* Two rings per row once the card is a single column: four pills wider than 240px cannot sit on
   one line without the labels truncating into ellipses. */
@media (max-width: 780px) {
    .rings {
        flex-wrap: wrap;
        gap: 14px 0;
    }

    .ring-cell {
        flex: 1 1 46%;
    }

    .ring-cell + .ring-cell::before {
        display: none;
    }
}

/* ---- last run: terminal ------------------------------------------------------ */

.term-lights {
    display: inline-flex;
    gap: 5px;
    margin-left: auto;
}

.term-lights i {
    width: 9px;
    height: 9px;
    border-radius: 50%;
}

.term-lights i:nth-child(1) {
    background: #ff5f57;
}

.term-lights i:nth-child(2) {
    background: #febc2e;
}

.term-lights i:nth-child(3) {
    background: #28c840;
}

/*
 * Always crimson ink, never themed: a terminal reads as a terminal in both themes, the same rule the
 * map HUDs and the tooltips follow. A themed surface would put dark prose on cream and stop
 * looking like output printed by a machine.
 */
.term-body {
    position: relative;
    z-index: 1;
    display: flex;
    flex: 1 1 auto;
    flex-direction: column;
    justify-content: flex-start;
    gap: 5px;
    overflow: hidden;
    padding: 12px 13px 14px;
    border-radius: 12px;
    border: 1px solid rgba(255, 59, 74, 0.26);
    background: linear-gradient(180deg, rgba(34, 7, 10, 0.94), rgba(14, 4, 6, 0.97));
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
    font-family: var(--rahat-mono);
    font-size: 11px;
    line-height: 1.65;
}

/* The corner wireframe the framed cards carry, shrunk into the console. */
.term-wave {
    position: absolute;
    right: -72px;
    bottom: -84px;
    width: 220px;
    height: 220px;
    border-radius: 50%;
    background: repeating-radial-gradient(circle at center,
        rgba(255, 59, 74, 0.5) 0 1px,
        transparent 1px 8px);
    mask-image: radial-gradient(circle at center, black 28%, transparent 70%);
    opacity: 0.32;
    pointer-events: none;
}

.term-line {
    position: relative;
    z-index: 1;
    display: flex;
    align-items: baseline;
    gap: 8px;
    animation: bento-line-in 240ms ease backwards;
}

/* The call the UI makes gets the one highlighted row, like the prompt bar of a real console. */
.term-line--cmd {
    align-self: stretch;
    margin: -1px -2px 1px;
    padding: 6px 9px;
    border-radius: 8px;
    border: 1px solid rgba(255, 59, 74, 0.3);
    background: rgba(255, 59, 74, 0.16);
}

.term-mark {
    flex: 0 0 auto;
    width: 10px;
    text-align: center;
}

.term-mark--cmd {
    color: var(--crimson-bright);
}

.term-mark--ok {
    color: #34d399;
}

.term-mark--info {
    color: rgba(251, 239, 240, 0.4);
}

.term-mark--warn {
    color: #fbb931;
}

.term-mark--url {
    color: #38bdf8;
}

.term-text {
    min-width: 0;
    word-break: break-word;
}

.term-line--cmd .term-text {
    font-weight: 700;
    letter-spacing: 0.01em;
}

.term-text--cmd {
    color: #ffe9ea;
}

.term-text--ok {
    color: rgba(251, 239, 240, 0.9);
}

.term-text--info {
    color: rgba(251, 239, 240, 0.48);
}

.term-text--warn {
    color: #fbb931;
}

.term-text--url {
    color: #7dd3fc;
    text-decoration: underline;
    text-underline-offset: 2px;
}

.term-open {
    flex: 0 0 auto;
    align-self: center;
    width: 12px;
    height: 12px;
    fill: none;
    stroke: #7dd3fc;
    stroke-width: 1.7;
    stroke-linecap: round;
    stroke-linejoin: round;
    opacity: 0.9;
}

.term-caret {
    position: relative;
    z-index: 1;
    display: block;
    width: 8px;
    height: 14px;
    margin-top: 4px;
    background: #ff3b4a;
    opacity: 0.9;
}

.term-caret--typing {
    animation: bento-blink 1s steps(2, start) infinite;
}

/* ---- offline imagery: bars --------------------------------------------------- */

/* Oversized stack mark behind the figure, half transparent so it never competes with the bars. */
.bars-watermark {
    position: absolute;
    top: 6px;
    right: 4px;
    z-index: 0;
    width: 96px;
    height: 96px;
    color: #ff3b4a;
    opacity: 0.14;
    pointer-events: none;
}

.bars-watermark svg {
    width: 100%;
    height: 100%;
    fill: none;
    stroke: currentColor;
    stroke-width: 1.1;
    stroke-linejoin: round;
}

.bars-figure {
    position: relative;
    z-index: 1;
    display: flex;
    align-items: baseline;
    gap: 8px;
}

.bars-value {
    font-size: 38px;
    font-weight: 700;
    line-height: 1;
    letter-spacing: -0.03em;
    font-variant-numeric: tabular-nums;
    color: var(--rahat-text-bright);
    text-shadow: 0 0 22px rgba(255, 59, 74, 0.42);
}

.bars-unit {
    font-size: 13px;
    color: var(--rahat-text-faint);
}

.bars-plot {
    position: relative;
    z-index: 1;
    display: flex;
    flex: 1 1 auto;
    gap: 8px;
    min-height: 132px;
    margin-top: 12px;
}

.bars-yaxis {
    position: relative;
    flex: 0 0 26px;
    font-size: 9.5px;
    font-variant-numeric: tabular-nums;
    color: var(--rahat-text-faint);
}

.bars-yaxis span {
    position: absolute;
    right: 0;
    transform: translateY(50%);
    line-height: 1;
}

.bars-stage {
    position: relative;
    flex: 1 1 auto;
    min-width: 0;
}

.bars-grid {
    position: absolute;
    left: 0;
    right: 0;
    height: 0;
    border-top: 1px dashed rgba(255, 255, 255, 0.075);
    pointer-events: none;
}

/* Zero closes the plot, so it is the one line that is not dashed. */
.bars-grid--base {
    border-top-style: solid;
    border-top-color: rgba(255, 255, 255, 0.16);
}

.bars {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: flex-end;
    gap: 6px;
}

.bar {
    flex: 1 1 0;
    min-width: 0;
    padding: 0;
    border: 1px solid rgba(255, 59, 74, 0.4);
    border-radius: 6px 6px 2px 2px;
    background: linear-gradient(180deg, rgba(255, 59, 74, 0.5), rgba(122, 12, 19, 0.92));
    transform-origin: bottom;
    cursor: pointer;
    transition: transform 220ms cubic-bezier(0.22, 0.61, 0.36, 1),
        box-shadow 220ms ease,
        border-color 220ms ease,
        background 220ms ease;
    animation: bento-bar-in 620ms cubic-bezier(0.22, 0.61, 0.36, 1) backwards;
}

.bar--peak {
    border-color: rgba(255, 90, 105, 0.75);
    background: linear-gradient(180deg, #ff5a69, #a4161a);
    box-shadow: 0 0 18px -4px rgba(255, 59, 74, 0.65);
}

.bar:hover,
.bar--hot {
    transform: scaleY(1.03);
    border-color: #ff8a94;
    background: linear-gradient(180deg, #ff7b87, #c4161f);
    box-shadow: 0 0 22px -2px rgba(255, 59, 74, 0.85);
}

.bars-axis {
    position: relative;
    z-index: 1;
    display: flex;
    gap: 6px;
    margin: 9px 0 0 34px;
}

.bars-axis span {
    display: flex;
    flex: 1 1 0;
    flex-direction: column;
    align-items: center;
    gap: 2px;
    min-width: 0;
    font-variant-numeric: tabular-nums;
    transition: color 200ms ease;
}

.bars-axis b {
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.04em;
    color: var(--rahat-text-dim);
}

.bars-axis i {
    font-size: 10px;
    font-style: normal;
    font-weight: 600;
    color: var(--rahat-text);
}

.bars-axis .bars-zoom--hot b {
    color: var(--rahat-accent-2);
}

.bars-axis .bars-zoom--hot i {
    color: var(--rahat-text-bright);
}

.bars-caption {
    position: relative;
    z-index: 1;
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 12px 0 0;
    padding: 9px 12px;
    border-radius: 12px;
    border: 1px solid rgba(255, 255, 255, 0.09);
    background: rgba(255, 255, 255, 0.025);
    font-size: 10.5px;
    color: var(--rahat-text-dim);
}

.bars-caption svg {
    flex: 0 0 auto;
    width: 14px;
    height: 14px;
    fill: none;
    stroke: currentColor;
    stroke-width: 1.7;
}

html.light .bars-caption {
    border-color: rgba(100, 13, 20, 0.14);
    background: rgba(100, 13, 20, 0.03);
}

html.light .bars-grid {
    border-top-color: rgba(100, 13, 20, 0.12);
}

html.light .bars-grid--base {
    border-top-color: rgba(100, 13, 20, 0.24);
}

html.light .bars-watermark {
    opacity: 0.1;
}

/* ---- pipeline: stage tiles --------------------------------------------------- */

/* Registered so the conic gradient below can interpolate; without it the browser would jump the
   sweep from 0 to 360 and nothing would appear to move. */
@property --stage-angle {
    syntax: "<angle>";
    initial-value: 0deg;
    inherits: false;
}

.pipeline-hint {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    margin-left: auto;
    padding: 6px 13px;
    border-radius: 999px;
    border: 1px solid rgba(255, 255, 255, 0.09);
    background: rgba(255, 255, 255, 0.03);
    font-size: 10.5px;
    color: var(--rahat-text-dim);
    white-space: nowrap;
}

.pipeline-hint svg {
    width: 14px;
    height: 14px;
    fill: none;
    stroke: var(--rahat-text-faint);
    stroke-width: 1.6;
    stroke-linecap: round;
}

html.light .pipeline-hint {
    border-color: rgba(100, 13, 20, 0.14);
    background: rgba(100, 13, 20, 0.03);
}

.stages {
    position: relative;
    z-index: 1;
    list-style: none;
    display: grid;
    flex: 1 1 auto;
    grid-template-columns: repeat(7, minmax(0, 1fr));
    gap: 18px;
    margin: 4px 0 0;
    padding: 0;
}

.stages li {
    position: relative;
    display: flex;
    min-width: 0;
}

/* The run between two stages: a hairline with a glowing node at its centre. */
.stages li:not(:last-child)::after {
    content: "";
    position: absolute;
    top: 50%;
    right: -18px;
    width: 18px;
    height: 1px;
    background: linear-gradient(90deg,
        rgba(255, 59, 74, 0.18),
        rgba(255, 59, 74, 0.72),
        rgba(255, 59, 74, 0.18));
}

.stages li:not(:last-child)::before {
    content: "";
    position: absolute;
    top: 50%;
    right: -9px;
    width: 4px;
    height: 4px;
    transform: translate(50%, -50%);
    border-radius: 50%;
    background: #ff6b78;
    box-shadow: 0 0 9px 1px rgba(255, 59, 74, 0.75);
    z-index: 2;
}

.stage {
    position: relative;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 9px;
    width: 100%;
    height: 100%;
    padding: 16px 10px 13px;
    border-radius: 14px;
    border: 1px solid rgba(255, 255, 255, 0.08);
    background: linear-gradient(180deg, rgba(26, 18, 18, 0.92), rgba(10, 8, 8, 0.96));
    color: var(--rahat-text);
    font: inherit;
    text-align: center;
    cursor: pointer;
    isolation: isolate;
    transition: transform 260ms cubic-bezier(0.22, 0.61, 0.36, 1),
        border-color 260ms ease,
        box-shadow 260ms ease;
}

/*
 * The live border: a conic gradient reduced to the 1px frame by a content-box mask, parked
 * invisible until the pointer or the keyboard arrives on the tile.
 */
.stage::before {
    content: "";
    position: absolute;
    inset: -1px;
    padding: 1px;
    border-radius: inherit;
    background: conic-gradient(from var(--stage-angle),
        transparent 0deg 236deg,
        rgba(255, 59, 74, 0.12) 262deg,
        #ff3b4a 312deg,
        #ffd2d6 336deg,
        transparent 356deg);
    -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
    -webkit-mask-composite: xor;
    mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
    mask-composite: exclude;
    opacity: 0;
    transition: opacity 220ms ease;
    animation: stage-sweep 2.6s linear infinite;
    pointer-events: none;
    z-index: 2;
}

.stage:hover::before,
.stage--on::before,
.stage:focus-visible::before {
    opacity: 1;
}

.stage:hover,
.stage--on {
    transform: translateY(-4px);
    border-color: rgba(255, 59, 74, 0.3);
    background: linear-gradient(180deg, rgba(48, 14, 18, 0.95), rgba(14, 6, 7, 0.97));
    box-shadow: 0 18px 34px -18px rgba(255, 59, 74, 0.65);
}

.stage-icon {
    display: grid;
    place-items: center;
    color: var(--rahat-text);
    transition: color 240ms ease, filter 240ms ease;
}

.stage-icon .v-icon {
    font-size: 30px;
}

.stage:hover .stage-icon,
.stage--on .stage-icon {
    color: #ff6b78;
    filter: drop-shadow(0 0 8px rgba(255, 59, 74, 0.55));
}

.stage-name {
    font-size: 12px;
    font-weight: 600;
    line-height: 1.35;
    color: var(--rahat-text-bright);
}

.stage-state {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    margin-top: auto;
    padding: 4px 9px;
    border-radius: 8px;
    border: 1px solid rgba(255, 255, 255, 0.1);
    background: rgba(255, 255, 255, 0.04);
    font-size: 9.5px;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--rahat-text-faint);
}

.stage-check {
    font-style: normal;
    font-size: 10px;
    line-height: 1;
}

.stage-state--ok {
    border-color: rgba(52, 211, 153, 0.42);
    background: rgba(52, 211, 153, 0.12);
    color: #34d399;
}

.stage-state--warn {
    border-color: rgba(251, 185, 49, 0.42);
    background: rgba(251, 185, 49, 0.12);
    color: #fbb931;
}

.stage-state--bad {
    border-color: rgba(255, 59, 74, 0.42);
    background: rgba(255, 59, 74, 0.13);
    color: #ff6b78;
}

.stage-detail {
    position: relative;
    z-index: 1;
    margin: 12px 0 0;
    min-height: 15px;
    font-size: 11.5px;
    color: var(--rahat-text-faint);
    animation: bento-fade 240ms ease backwards;
}

@keyframes stage-sweep {
    to {
        --stage-angle: 360deg;
    }
}

/* Below 1280px the card is half as wide but a stage still needs its reading width, so the row
   scrolls horizontally instead of shrinking into slivers. */
@media (max-width: 1280px) {
    .stages {
        grid-template-columns: repeat(7, minmax(118px, 1fr));
        overflow-x: auto;
        padding-bottom: 6px;
    }

    .pipeline-hint {
        display: none;
    }
}

@media (prefers-reduced-motion: reduce) {
    .stage::before {
        animation: none;
    }
}

/* ---- motion ------------------------------------------------------------------ */

@keyframes bento-pulse {
    0%,
    100% {
        opacity: 1;
    }

    50% {
        opacity: 0.32;
    }
}

@keyframes bento-blink {
    0%,
    100% {
        opacity: 0.7;
    }

    50% {
        opacity: 0;
    }
}

@keyframes bento-line-in {
    from {
        opacity: 0;
        transform: translateY(4px);
    }
}

@keyframes bento-bar-in {
    from {
        opacity: 0;
        transform: scaleY(0.12);
    }
}

@keyframes bento-fade {
    from {
        opacity: 0;
        transform: translateY(3px);
    }
}

@media (max-width: 1280px) {
    .stages {
        grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    }
}

@media (prefers-reduced-motion: reduce) {
    .live-dot,
    .term-line,
    .term-caret--typing,
    .bar,
    .stage-detail {
        animation: none;
    }

    .bar:hover,
    .bar--hot,
    .stage:hover,
    .stage--on {
        transform: none;
    }
}

/* ---- recent jobs: the table rides in its own framed panel ------------------ */

.jobs-shell {
    position: relative;
    z-index: 1;
    overflow: hidden;
    border: 1px solid var(--rahat-border);
    border-radius: 12px;
    background: rgba(0, 0, 0, 0.24);
}

html.light .jobs-shell {
    background: rgba(100, 13, 20, 0.02);
}

/* The designed empty state: a marked glyph resting on its shadow, then the way out. */
.jobs-empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 24px 18px 26px;
    text-align: center;
}

.jobs-empty-mark {
    position: relative;
    display: grid;
    place-items: center;
    width: 46px;
    height: 40px;
    margin-bottom: 10px;
    color: #ff5a69;
}

.jobs-empty-mark svg {
    position: relative;
    z-index: 1;
    width: 32px;
    height: 32px;
    fill: currentColor;
    opacity: 0.92;
}

/* The red platform the glyph sits on. */
.jobs-empty-pad {
    position: absolute;
    left: 50%;
    bottom: 0;
    width: 48px;
    height: 10px;
    transform: translateX(-50%);
    border-radius: 50%;
    background: radial-gradient(closest-side, rgba(208, 30, 44, 0.55), transparent);
    filter: blur(1.5px);
}

.jobs-empty-title {
    margin: 0;
    font-size: 13px;
    font-weight: 700;
    color: var(--rahat-text);
}

.jobs-empty-hint {
    max-width: 340px;
    margin: 4px 0 0;
    font-size: 11px;
    line-height: 1.55;
    color: var(--rahat-text-faint);
}

.jobs-empty-cta {
    margin-top: 12px;
    border-color: rgba(255, 59, 74, 0.5) !important;
    color: #ff8a93 !important;
    font-size: 11px !important;
    letter-spacing: 0.02em;
    text-transform: none !important;
}

.jobs-empty-cta:hover {
    background: rgba(255, 59, 74, 0.12) !important;
    border-color: rgba(255, 59, 74, 0.75) !important;
}

html.light .jobs-empty-cta {
    border-color: rgba(100, 13, 20, 0.35) !important;
    color: var(--rahat-accent) !important;
}

/* ---- quick actions: buttons over a 2x2 of live figures -------------------- */

.actions {
    position: relative;
    z-index: 1;
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(148px, 1fr));
    gap: 10px;
}

.action {
    min-height: 42px;
    font-size: 11.5px !important;
    font-weight: 600;
    letter-spacing: 0.01em;
    text-transform: none !important;
    border-radius: 10px !important;
    border-color: var(--rahat-border) !important;
    background: rgba(255, 255, 255, 0.035) !important;
    color: var(--rahat-text-dim) !important;
    transition: background-color 160ms ease, border-color 160ms ease, color 160ms ease;
}

.action:hover {
    background: var(--rahat-chip-hot) !important;
    border-color: var(--rahat-border-strong) !important;
    color: var(--rahat-text) !important;
}

.action--primary {
    background: linear-gradient(135deg, #d51d27 0%, var(--crimson-vivid) 100%) !important;
    color: #fff !important;
    border-color: transparent !important;
    font-weight: 700;
    box-shadow: 0 8px 22px rgba(208, 30, 44, 0.42),
        inset 0 1px 0 rgba(255, 255, 255, 0.22);
}

.action--primary:hover {
    background: linear-gradient(135deg, #e52330 0%, #b81a1f 100%) !important;
    color: #fff !important;
}

html.light .action {
    background: #fff !important;
}

html.light .action--primary {
    background: linear-gradient(135deg, var(--crimson-vivid) 0%, var(--crimson-deep) 100%) !important;
    color: #fff !important;
}

.action-stats {
    position: relative;
    z-index: 1;
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
    margin-top: 12px;
}

/*
 * One accent per figure, drawn from the palette the rest of the app already uses: crimson for the
 * model, violet for the tile pyramid, blue for the georeferencing check, green for the filter.
 */
.action-stat {
    --stat: var(--rahat-highlight);
    --stat-soft: var(--rahat-accent-soft);

    display: flex;
    align-items: center;
    gap: 11px;
    min-width: 0;
    padding: 10px 12px;
    border-radius: 12px;
    border: 1px solid var(--rahat-border);
    background: linear-gradient(135deg, var(--stat-soft) 0%, transparent 62%), var(--rahat-chip);
}

.action-stat--red {
    --stat: #ff5a69;
    --stat-soft: rgba(208, 30, 44, 0.16);
}

.action-stat--purple {
    --stat: var(--rahat-purple);
    --stat-soft: var(--rahat-purple-soft);
}

.action-stat--blue {
    --stat: var(--rahat-info);
    --stat-soft: var(--rahat-info-soft);
}

.action-stat--green {
    --stat: var(--rahat-ok);
    --stat-soft: var(--rahat-ok-soft);
}

.action-stat-icon {
    display: grid;
    place-items: center;
    width: 34px;
    height: 34px;
    flex: 0 0 auto;
    border-radius: 10px;
    color: var(--stat);
    background: var(--stat-soft);
}

.action-stat-copy {
    display: flex;
    flex-direction: column;
    min-width: 0;
}

.action-stat-label {
    font-size: 10px;
    letter-spacing: 0.04em;
    color: var(--rahat-text-faint);
}

.action-stat-value {
    font-size: 17px;
    font-weight: 700;
    line-height: 1.25;
    color: var(--rahat-text-bright);
    font-variant-numeric: tabular-nums;
}

/* Both cards are reading surfaces, so the frame holds still and only the buttons react. */
.dashboard-last .bento-jobs:hover,
.dashboard-last .bento-actions:hover {
    transform: none;
}
</style>
