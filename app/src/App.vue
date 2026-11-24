<!--
    DISASTER RESPONSE APP
    Copyright (c) 2021 SilentByte <https://silentbyte.com/>
-->

<template>
    <v-app :dark="theme.isDark" class="rahat-app">
        <v-navigation-drawer app permanent :dark="theme.isDark" width="264" class="rahat-drawer">
            <div class="drawer-card">
                <div class="brand">
                    <!-- The supplied lockup already carries the wordmark, so the header is the image alone. -->
                    <img class="brand-logo" :src="logoSrc" alt="RAHAT" />
                </div>

                <v-list dense nav class="nav">
                    <v-list-item v-for="item in navItems"
                                 :key="item.route"
                                 :to="item.route"
                                 :exact="item.route !== '/map'"
                                 class="nav-item"
                                 :class="{ 'nav-item--active': isNavActive(item.route) }">
                        <v-list-item-icon class="nav-icon">
                            <v-icon small>{{ item.icon }}</v-icon>
                        </v-list-item-icon>

                        <v-list-item-content>
                            <v-list-item-title class="nav-label">{{ item.label }}</v-list-item-title>
                        </v-list-item-content>

                        <v-list-item-action v-if="item.route === '/inference' && activeJobs > 0"
                                            class="nav-badge">
                            {{ activeJobs }}
                        </v-list-item-action>

                        <v-list-item-action class="nav-chevron">
                            <v-icon small>mdi-chevron-right</v-icon>
                        </v-list-item-action>
                    </v-list-item>
                </v-list>

                <div class="status-card">
                    <div class="status-head">
                        <div class="status-tile">
                            <v-icon small>mdi-satellite-variant</v-icon>
                        </div>

                        <div class="status-titles">
                            <div class="status-title">RAHAT v2</div>
                            <div class="status-sub">system status</div>
                        </div>

                        <div class="status-pill" :class="`status-pill--${apiTone}`">
                            <span class="status-pill-dot" />
                            {{ apiState }}
                        </div>
                    </div>

                    <div class="status-rows">
                        <div class="foot-row">
                            <span class="dot" :class="geoservDot" />
                            geoserv
                            <span class="foot-value">{{ geoservState }}</span>
                        </div>

                        <div class="foot-row">
                            <span class="dot" :class="modelDot" />
                            models
                            <span class="foot-value">{{ modelState }}</span>
                        </div>
                    </div>
                </div>

                <button type="button" class="drawer-foot" title="Refresh now" @click="refresh">
                    <v-icon x-small :class="{ 'mdi-spin': loading }">mdi-sync</v-icon>
                    {{ syncedLabel }}
                </button>
            </div>
        </v-navigation-drawer>

        <v-app-bar app :dark="theme.isDark" flat height="64" class="rahat-bar">
            <div class="bar-title">
                <div class="page-title">{{ pageTitle }}</div>
                <div class="page-subtitle">{{ pageSubtitle }}</div>
            </div>

            <v-spacer />

            <v-select class="zone-select"
                      dense outlined hide-details
                      return-object
                      item-value="id"
                      item-text="name"
                      prepend-inner-icon="mdi-map-marker-outline"
                      :items="app.disasterZones"
                      :value="app.selectedDisasterZone"
                      :menu-props="zoneMenuProps"
                      @change="onSelectDisasterZone">
                <template v-slot:item="{ item, attrs, on }">
                    <v-list-item v-bind="attrs" v-on="on">
                        <v-list-item-icon>
                            <v-icon small>{{ zoneIcon(item) }}</v-icon>
                        </v-list-item-icon>

                        <v-list-item-content>
                            <v-list-item-title class="zone-option-label">{{ item.name }}</v-list-item-title>
                        </v-list-item-content>

                        <v-list-item-icon v-if="item.id === selectedZoneId" class="zone-option-check">
                            <v-icon small>mdi-check</v-icon>
                        </v-list-item-icon>
                    </v-list-item>
                </template>
            </v-select>

            <v-btn icon class="theme-toggle"
                   :title="theme.isDark ? 'Switch to the rose-white theme' : 'Switch to the OLED theme'"
                   @click="toggleTheme">
                <v-icon>{{ theme.isDark ? "mdi-white-balance-sunny" : "mdi-weather-night" }}</v-icon>
            </v-btn>

            <v-btn icon class="refresh" @click="refresh">
                <v-icon :class="{'mdi-spin': loading}">mdi-refresh</v-icon>
            </v-btn>
        </v-app-bar>

        <v-main class="rahat-main">
            <router-view />
        </v-main>
    </v-app>
</template>

<!--suppress JSMethodCanBeStatic, JSUnusedGlobalSymbols -->
<script lang="ts">

import {
    Component,
    Vue,
} from "vue-property-decorator";

import { getModule } from "vuex-module-decorators";
import { AppModule } from "@/store/app";
import { ThemeModule } from "@/store/theme";

import { IDisasterZone } from "@/models";
import {
    ApiRequestError,
    fetchDiagnostics,
    fetchHealth,
    fetchJobs,
} from "@/modules/api";
import { fetchDisasterZones } from "@/modules/zones";
import { SELECT_MENU_PROPS } from "@/modules/utils";

const REFRESH_INTERVAL_MS = 10000;

interface INavItem {
    route: string;
    label: string;
    icon: string;
}

@Component
export default class App extends Vue {
    private readonly app = getModule(AppModule);

    private readonly theme = getModule(ThemeModule);

    private readonly navItems: INavItem[] = [
        { route: "/", label: "Dashboard", icon: "mdi-view-dashboard-outline" },
        { route: "/map", label: "Map", icon: "mdi-map-outline" },
        { route: "/report", label: "Report", icon: "mdi-file-document-outline" },
        { route: "/analytics", label: "Analytics", icon: "mdi-chart-box-outline" },
        { route: "/zones", label: "Zones", icon: "mdi-map-marker-multiple-outline" },
        { route: "/inference", label: "Inference", icon: "mdi-play-circle-outline" },
        { route: "/super-resolution", label: "Super-Res", icon: "mdi-satellite-variant" },
        { route: "/spectral", label: "Spectral", icon: "mdi-image-filter-hdr" },
        { route: "/models", label: "Models", icon: "mdi-brain" },
        { route: "/system", label: "System", icon: "mdi-tune-variant" },
    ];

    private loading = false;

    private timer: number | null = null;

    /** Keep the zone panel under its field instead of on top of it; see modules/utils. */
    private readonly zoneMenuProps = SELECT_MENU_PROPS;

    private get pageTitle(): string {
        return (this.$route.meta?.title as string) || "RAHAT";
    }

    private get pageSubtitle(): string {
        return (this.$route.meta?.subtitle as string) || "";
    }

    private get activeJobs(): number {
        return this.app.health?.active_jobs || 0;
    }

    private get selectedZoneId(): string | null {
        return this.app.selectedDisasterZone?.id || null;
    }

    private isNavActive(route: string): boolean {
        if(route === "/map") {
            return this.$route.path === "/map" || this.$route.path.startsWith("/map/");
        }
        return this.$route.path === route;
    }

    private get apiState(): string {
        const status = this.app.health?.status;
        return status ? status : "offline";
    }

    /** Same three-way read as apiDot, but as a bare tone for the sidebar status pill. */
    private get apiTone(): string {
        const status = this.app.health?.status;
        return status === "ready" ? "ok" : status === "degraded" ? "warn" : "bad";
    }

    /**
     * The lockup ships from public/ so the dev server and the built bundle resolve it identically.
     * The source artwork is black ink on transparency, so the panel picks which file is drawn.
     */
    private get logoSrc(): string {
        const file = this.theme.isDark ? "sidebar-logo-dark.png" : "sidebar-logo.png";
        return `${process.env.BASE_URL}${file}`;
    }

    private get geoservDot(): string {
        return this.app.health?.geoserv_reachable ? "dot--ok" : "dot--bad";
    }

    private get geoservState(): string {
        return this.app.health?.geoserv_reachable ? "indexed" : "down";
    }

    private get modelDot(): string {
        const missing = this.app.health?.missing_models?.length || 0;
        return missing === 0 && this.app.health ? "dot--ok" : "dot--warn";
    }

    private get modelState(): string {
        const missing = this.app.health?.missing_models?.length || 0;
        return missing === 0 ? "loaded" : `${missing} missing`;
    }

    private get syncedLabel(): string {
        const at = this.app.lastSyncedAt;
        if(!at) {
            return "not synced yet";
        }

        const seconds = Math.max(0, Math.round((Date.now() - at) / 1000));
        return seconds < 3 ? "synced just now" : `synced ${seconds}s ago`;
    }

    private toggleTheme(): void {
        this.theme.toggleTheme();
    }

    /**
     * Open on the current zone, closed everywhere else: the row itself carries the highlight.
     */
    private zoneIcon(disasterZone: IDisasterZone): string {
        return disasterZone.id === this.selectedZoneId
            ? "mdi-map-marker-check"
            : "mdi-map-marker-outline";
    }

    private onSelectDisasterZone(disasterZone: IDisasterZone) {
        if(!disasterZone) {
            return;
        }

        if(disasterZone.id === this.app.selectedDisasterZone?.id) {
            return;
        }

        // Re-setting the same object does not trigger the map watchers, so clear it first.
        this.app.setSelectedDisasterZone(null);
        this.app.setSelectedDisasterZone(disasterZone);

        if(this.$route.name !== "Map") {
            this.$router.push("/map").catch(() => undefined);
        }
    }

    private describeError(reason: unknown): string {
        if(reason instanceof ApiRequestError) {
            return reason.message === "Failed to fetch"
                ? "inference API unreachable - start uvicorn on :8099"
                : reason.message;
        }

        return String(reason);
    }

    private async refresh(): Promise<void> {
        if(this.loading) {
            return;
        }

        this.loading = true;

        // The three calls differ in cost (diagnostics walks every tile), so one slow response
        // must not blank the others.
        const [health, diagnostics, jobs] = await Promise.allSettled([
            fetchHealth(),
            fetchDiagnostics(),
            fetchJobs(),
        ]);

        this.app.setHealth(health.status === "fulfilled" ? health.value : null);
        if(diagnostics.status === "fulfilled") {
            this.app.setDiagnostics(diagnostics.value);
        }
        if(jobs.status === "fulfilled") {
            this.app.setJobs(jobs.value);
        }

        const failure = [health, diagnostics, jobs].find(result => result.status === "rejected");
        this.app.setServiceError(failure && failure.status === "rejected"
            ? this.describeError(failure.reason)
            : null);

        this.app.markSynced();
        this.loading = false;
    }

    private async loadZones(): Promise<void> {
        if(this.app.disasterZones.length) {
            return;
        }

        try {
            // Loaded by the shell so the zone selector works on every page, not just the map.
            this.app.setDisasterZones(await fetchDisasterZones());
            this.app.setDefaultDisasterZone();
        } catch(error) {
            console.warn("could not load disaster zones", error);
        }
    }

    mounted(): void {
        this.app.initializeStore();
        this.loadZones().then();
        this.refresh().then();
        this.timer = window.setInterval(() => this.refresh().then(), REFRESH_INTERVAL_MS);
    }

    beforeDestroy(): void {
        if(this.timer !== null) {
            window.clearInterval(this.timer);
        }

        this.app.uninitializeStore();
    }
}

</script>

<style lang="scss" scoped>
.rahat-app {
    background: var(--rahat-bg);
}

/* The drawer is only a transparent rail; the visible panel is .drawer-card, inset like a floating slab. */
.rahat-drawer {
    background: transparent !important;
    border-right: 0 !important;
    box-shadow: none !important;
}

.rahat-drawer::v-deep .v-navigation-drawer__content {
    display: flex;
    flex-direction: column;
}

.drawer-card {
    position: relative;
    flex: 1 1 auto;
    min-height: 0;
    margin: 10px;
    display: flex;
    flex-direction: column;
    background: linear-gradient(168deg, #170b0d 0%, #0b0708 34%, #080808 62%);
    border: 1px solid rgba(208, 30, 44, 0.22);
    border-radius: 18px;
    overflow: hidden;
    box-shadow: 0 18px 48px rgba(0, 0, 0, 0.55), 0 0 34px rgba(164, 22, 26, 0.14);
}

/*
 * The bloom from the reference: a crimson wash bleeding in at the top-right corner, with a fainter
 * one on the left so the header band reads as lit rather than half-painted. Decoration only, so it
 * sits below the content and never takes a pointer event.
 */
.drawer-card::before {
    content: "";
    position: absolute;
    inset: 0;
    pointer-events: none;
    background: radial-gradient(74% 30% at 94% -8%, rgba(214, 32, 40, 0.26), transparent 66%),
        radial-gradient(56% 24% at 2% -6%, rgba(140, 18, 26, 0.12), transparent 70%);
}

/* Keep the flow above the bloom; the decoration is a sibling layer, not a wrapper. */
.drawer-card > * {
    position: relative;
    z-index: 1;
}

html.light .drawer-card {
    background: linear-gradient(168deg, #fffafb 0%, #fdf1f2 46%, #fbeeef 100%);
    border-color: rgba(100, 13, 20, 0.18);
    box-shadow: 0 18px 48px rgba(74, 10, 16, 0.12);
}

html.light .drawer-card::before {
    background: radial-gradient(78% 34% at 92% -6%, rgba(208, 30, 44, 0.14), transparent 68%),
        radial-gradient(60% 26% at 4% -4%, rgba(100, 13, 20, 0.08), transparent 70%);
}

.brand {
    display: flex;
    align-items: center;
    /* Same 10px side inset as .nav, so the lockup's edges line up with the Dashboard chip. */
    padding: 12px 10px 10px;
}

.brand-logo {
    display: block;
    width: 100%;
    height: auto;
}

.nav {
    flex: 1 1 auto;
    min-height: 0;
    overflow-y: auto;
    padding: 2px 10px 0;
}

/*
 * Each row is its own raised chip, which is what gives the reference panel its stacked-card rhythm:
 * a hairline edge and a gradient that catches the light at the top, rather than a flat wash.
 * The descendant selector is load-bearing: Vuetify's `.v-list--nav .v-list-item` sets
 * border-radius: 4px at the same weight as a bare `.nav-item`, and it is injected later, so every
 * chip came out square-cornered until this rule outranked it.
 */
.nav .nav-item {
    min-height: 46px !important;
    margin-bottom: 8px;
    border-radius: 12px;
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.065) 0%, rgba(255, 255, 255, 0.018) 100%) !important;
    border: 1px solid rgba(255, 255, 255, 0.075);
    color: var(--rahat-text-dim) !important;
    transition: background-color 160ms ease, border-color 160ms ease, color 160ms ease;
}

.nav-item:hover {
    background: var(--rahat-chip-hot) !important;
    border-color: var(--rahat-border);
    color: var(--rahat-text) !important;
}

html.light .nav .nav-item {
    background: linear-gradient(180deg, #ffffff 0%, #fdf5f5 100%) !important;
    border-color: rgba(100, 13, 20, 0.12);
}

/* Restated at this weight so the flat hover fill still wins on the light theme. */
html.light .nav .nav-item:hover {
    background: var(--rahat-chip-hot) !important;
    border-color: var(--rahat-border-strong);
}

/* Kills Vuetify's ripple wash; the chip supplies its own fill. */
.nav-item::before {
    opacity: 0 !important;
    border-radius: inherit;
}

.nav-icon {
    color: inherit;
    min-width: 30px;
}

.nav-label {
    font-size: 13px;
    font-weight: 500;
    letter-spacing: 0.01em;
}

.nav-chevron {
    min-width: 16px;
    margin-left: 4px;
    color: inherit;
    opacity: 0.4;
    transition: transform 160ms ease, opacity 160ms ease;
}

.nav-item:hover .nav-chevron,
.nav-item--active .nav-chevron,
.v-list-item--active .nav-chevron {
    opacity: 0.9;
}

.nav-item:hover .nav-chevron {
    transform: translateX(2px);
}

/*
 * The active row is driven by our own class rather than Vuetify's: v-list-item's `exact` matching
 * compares the whole route including the query, so any URL carrying one (?theme=light, a shared
 * link, an analytics tag) silently dropped the highlight. Paired with .v-list-item--active so the
 * clean-URL case keeps the same look whichever class turns up.
 */
.nav-item.nav-item--active,
.nav-item.v-list-item--active {
    background: linear-gradient(135deg, var(--crimson-vivid) 0%, var(--crimson-bright) 100%) !important;
    border-color: transparent;
    color: var(--rahat-on-accent) !important;
    box-shadow: 0 8px 22px rgba(164, 22, 26, 0.42),
        inset 0 1px 0 rgba(255, 255, 255, 0.18);
}

/* On white the bright end of the ramp washes out, so the light theme states the active chip in deep crimson. */
html.light .nav-item.nav-item--active,
html.light .nav-item.v-list-item--active {
    background: linear-gradient(135deg, var(--crimson-deep) 0%, var(--crimson-vivid) 100%) !important;
    color: var(--rahat-on-accent) !important;
}

.nav-badge {
    min-width: 18px;
    height: 18px;
    border-radius: 9px;
    background: var(--rahat-accent);
    color: var(--rahat-on-accent);
    font-size: 11px;
    font-weight: 700;
    display: grid;
    place-items: center;
    margin-left: 8px;
    box-shadow: 0 0 12px rgba(164, 22, 26, 0.55);
}

/* On the gradient chip the crimson badge would disappear into the fill. */
.nav-item--active .nav-badge,
.v-list-item--active .nav-badge {
    background: rgba(255, 255, 255, 0.24);
    color: #ffffff;
    box-shadow: none;
}

/* The version slab from the reference, filled with this project's live state rather than a mock badge. */
.status-card {
    margin: 8px 10px 0;
    padding: 12px;
    border-radius: 14px;
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.055) 0%, rgba(164, 22, 26, 0.07) 100%);
    border: 1px solid var(--rahat-border);
}

html.light .status-card {
    background: linear-gradient(180deg, #ffffff 0%, #fdf3f4 100%);
    border-color: rgba(100, 13, 20, 0.12);
}

.status-head {
    display: flex;
    align-items: center;
    gap: 10px;
}

.status-tile {
    width: 34px;
    height: 34px;
    flex: 0 0 auto;
    display: grid;
    place-items: center;
    border-radius: 9px;
    color: var(--rahat-highlight);
    background: linear-gradient(135deg, rgba(164, 22, 26, 0.42), rgba(208, 30, 44, 0.16));
    border: 1px solid rgba(164, 22, 26, 0.45);
}

html.light .status-tile {
    color: var(--rahat-accent);
    background: linear-gradient(135deg, rgba(100, 13, 20, 0.14), rgba(208, 30, 44, 0.06));
    border-color: rgba(100, 13, 20, 0.22);
}

.status-titles {
    flex: 1 1 auto;
    min-width: 0;
}

.status-title {
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.04em;
    color: var(--rahat-text);
}

.status-sub {
    margin-top: 2px;
    font-size: 10px;
    color: var(--rahat-text-faint);
}

.status-pill {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    /* Third child of the head row in the reference: the state rides beside the title, not under it. */
    margin-left: auto;
    flex: 0 0 auto;
    padding: 2px 9px 2px 7px;
    border-radius: 999px;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.05em;
    color: var(--rahat-text);
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid var(--rahat-border);
}

.status-pill-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--rahat-text-faint);
}

.status-pill--ok {
    color: var(--rahat-ok);
    background: var(--rahat-ok-soft);
    border-color: rgba(52, 211, 153, 0.35);
}

.status-pill--ok .status-pill-dot {
    background: var(--rahat-ok);
    box-shadow: 0 0 8px var(--rahat-ok);
}

.status-pill--warn {
    color: var(--rahat-warn);
    background: var(--rahat-warn-soft);
    border-color: rgba(251, 185, 49, 0.35);
}

.status-pill--warn .status-pill-dot {
    background: var(--rahat-warn);
    box-shadow: 0 0 8px var(--rahat-warn);
}

.status-pill--bad {
    color: var(--rahat-danger);
    background: var(--rahat-danger-soft);
    border-color: rgba(251, 113, 133, 0.35);
}

.status-pill--bad .status-pill-dot {
    background: var(--rahat-danger);
    box-shadow: 0 0 8px var(--rahat-danger);
}

/* The translucent borders above are tuned for a black canvas; on cream the same mint read as neon. */
html.light .status-pill--ok {
    border-color: rgba(4, 120, 87, 0.32);
}

html.light .status-pill--warn {
    border-color: rgba(180, 83, 9, 0.32);
}

html.light .status-pill--bad {
    border-color: rgba(190, 18, 60, 0.32);
}

.status-rows {
    margin-top: 10px;
    padding-top: 8px;
    border-top: 1px solid var(--rahat-border);
    font-size: 11px;
    color: var(--rahat-text-faint);
}

.foot-row {
    display: flex;
    align-items: center;
    gap: 7px;
    padding: 6px 0;
}

/* A hairline between the rows, as in the reference, instead of one rule above the pair. */
.foot-row + .foot-row {
    border-top: 1px solid var(--rahat-border);
}

.foot-value {
    margin-left: auto;
    color: var(--rahat-text-dim);
    font-family: var(--rahat-mono);
    font-size: 10px;
}

/*
 * The footer is a real button: the sync glyph in the reference reads as an action, so it repeats the
 * same refresh the top bar offers rather than sitting there as decoration.
 */
.drawer-foot {
    display: flex;
    align-items: center;
    gap: 7px;
    width: 100%;
    padding: 10px 14px 12px;
    border: 0;
    background: none;
    font-family: inherit;
    font-size: 10px;
    text-align: left;
    color: var(--rahat-text-faint);
    cursor: pointer;
    transition: color 160ms ease;
}

.drawer-foot:hover {
    color: var(--rahat-text);
}

.drawer-foot:focus-visible {
    outline: 1px solid var(--rahat-accent);
    outline-offset: -3px;
    border-radius: 8px;
}

.dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--rahat-text-faint);
    flex: 0 0 auto;
}

.dot--ok {
    background: var(--rahat-ok);
    box-shadow: 0 0 0 3px var(--rahat-ok-soft), 0 0 10px var(--rahat-ok);
}

.dot--warn {
    background: var(--rahat-warn);
    box-shadow: 0 0 0 3px var(--rahat-warn-soft), 0 0 10px var(--rahat-warn);
}

.dot--bad {
    background: var(--rahat-danger);
    box-shadow: 0 0 0 3px var(--rahat-danger-soft), 0 0 10px var(--rahat-danger);
}

/*
 * The dock: glass only. It used to carry a solid crimson rule plus a blurred red band beneath the
 * title, which read as a red line under every page name; the 1px border is the whole separation
 * now, and the shadow comes from the theme so no crimson bleeds onto the page.
 */
.rahat-bar {
    background: var(--rahat-glass) !important;
    backdrop-filter: blur(24px) saturate(1.4);
    -webkit-backdrop-filter: blur(24px) saturate(1.4);
    border-bottom: 1px solid var(--rahat-border) !important;
    padding: 0 22px;
    box-shadow: var(--rahat-shadow-soft) !important;
}

.bar-title {
    min-width: 0;
    flex: 1 1 auto;
    overflow: hidden;
}

// The bar is a fixed 64px tall, so a wrapping subtitle would spill over the page content.
// Every line is kept to a single row and truncated with an ellipsis instead.
.bar-title .page-title,
.bar-title .page-subtitle {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.zone-select {
    max-width: 300px;
    flex: 0 1 300px;
    margin: 0 14px 0 0;
    font-size: 13px;
}

/*
 * The trigger is the same glass as the panel it opens, so the two read as one control: a rounded
 * field with a crimson pin, a dimmed caret, and a theme hairline instead of Vuetify's underline.
 */
.zone-select::v-deep .v-input__slot {
    background: var(--rahat-glass) !important;
    border-radius: 11px;
}

.zone-select::v-deep fieldset {
    border-radius: 11px !important;
    border-color: var(--rahat-border) !important;
}

.zone-select:hover::v-deep fieldset,
.zone-select.v-input--is-focused::v-deep fieldset {
    border-color: var(--rahat-accent-2) !important;
}

/* The field is a picker, not a text box: the caret only ever flashed between the label and the
   chevron while the menu was open. */
.zone-select::v-deep input {
    caret-color: transparent;
}

.zone-select::v-deep .v-input__icon--prepend-inner {
    min-width: 22px;
    color: var(--rahat-highlight);
}

.zone-select::v-deep .v-input__append-inner .v-icon {
    font-size: 19px;
    color: var(--rahat-text-faint);
}

.zone-select::v-deep .v-select__selection--comma {
    font-size: 12.5px;
    font-weight: 500;
    color: var(--rahat-text);
}

.theme-toggle,
.refresh {
    color: var(--rahat-text-dim);
}

.theme-toggle:hover,
.refresh:hover {
    color: var(--rahat-highlight) !important;
    background: rgba(164, 22, 26, 0.14) !important;
}

html.light .theme-toggle:hover,
html.light .refresh:hover {
    color: var(--rahat-accent) !important;
}

.theme-toggle .v-icon {
    transition: transform 320ms cubic-bezier(0.22, 0.61, 0.36, 1);
}

.theme-toggle:hover .v-icon {
    transform: rotate(24deg) scale(1.08);
}

/* .rahat-main's canvas colour and ambient aura live in app.scss so they apply on every route. */
</style>
