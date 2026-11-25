<!--
    DISASTER RESPONSE APP
    Copyright (c) 2021 SilentByte <https://silentbyte.com/>
-->

<template>
    <div class="page">
        <div class="grid grid--kpi">
            <StatCard label="inference api" :value="apiStatus"
                      :tone="apiTone"
                      hint="uvicorn 127.0.0.1:8099" />
            <StatCard label="geoserv" :value="geoservStatus"
                      :tone="geoservTone"
                      hint="rust index on :8088" />
            <StatCard label="models" :value="modelsLabel" hint="checkpoints present" />
            <StatCard label="queue" :value="queueLabel" hint="active / slots" />
        </div>

        <v-alert v-if="serviceError" dense text type="error" class="block">
            {{ serviceError }}
        </v-alert>

        <div class="grid grid--two block">
            <SectionCard title="services" subtitle="live health payload">
                <div class="rows">
                    <div v-for="row in serviceRows" :key="row.label" class="row">
                        <span class="dot" :class="`dot--${row.state}`" />
                        <span class="row-label">{{ row.label }}</span>
                        <span class="row-value mono">{{ row.value }}</span>
                    </div>
                </div>
            </SectionCard>

            <SectionCard title="api endpoints" subtitle="what the UI calls">
                <div class="endpoints">
                    <div v-for="endpoint in endpoints" :key="endpoint.path" class="endpoint">
                        <span class="method" :class="`method--${endpoint.method.toLowerCase()}`">
                            {{ endpoint.method }}
                        </span>
                        <span class="mono endpoint-path">{{ endpoint.path }}</span>
                        <span class="endpoint-note">{{ endpoint.note }}</span>
                    </div>
                </div>
            </SectionCard>
        </div>

        <SectionCard class="block" title="model files" subtitle="resolved paths and metadata files" flush>
            <div class="table-wrap">
                <table>
                    <thead>
                    <tr>
                        <th>role</th>
                        <th>path</th>
                        <th class="num">size</th>
                        <th>meta</th>
                        <th>state</th>
                    </tr>
                    </thead>
                    <tbody>
                    <tr v-for="model in models" :key="model.role">
                        <td class="mono role">{{ model.role }}</td>
                        <td class="mono path">{{ model.path }}</td>
                        <td class="num">{{ model.size_mb !== null ? `${model.size_mb} MB` : "-" }}</td>
                        <td class="mono faint">{{ model.meta.model || model.meta.arch || "-" }}</td>
                        <td>
                            <span class="state" :class="model.exists ? 'state--ok' : 'state--bad'">
                                {{ model.exists ? "present" : "missing" }}
                            </span>
                        </td>
                    </tr>
                    <tr v-if="!models.length">
                        <td colspan="5" class="empty">diagnostics not loaded</td>
                    </tr>
                    </tbody>
                </table>
            </div>
        </SectionCard>

        <SectionCard class="block" title="offline imagery" subtitle="tiles served by the vue app, not by geoserv" flush>
            <div class="table-wrap">
                <table>
                    <thead>
                    <tr>
                        <th>zone</th>
                        <th v-for="role in imageryRoles" :key="role" class="num">{{ role }}</th>
                        <th>zooms</th>
                        <th class="num">total</th>
                    </tr>
                    </thead>
                    <tbody>
                    <tr v-for="row in imageryRows" :key="row.zone">
                        <td class="mono path">{{ row.zone }}</td>
                        <td v-for="role in imageryRoles" :key="role" class="num">
                            {{ row.roles[role] || 0 }}
                        </td>
                        <td class="mono faint">{{ row.zooms }}</td>
                        <td class="num strong">{{ row.total }}</td>
                    </tr>
                    <tr v-if="!imageryRows.length">
                        <td :colspan="imageryRoles.length + 3" class="empty">no tiles found</td>
                    </tr>
                    </tbody>
                </table>
            </div>
        </SectionCard>

        <SectionCard class="block" title="paths" subtitle="where the API reads and writes">
            <div class="rows">
                <div class="row">
                    <span class="row-label">data dir</span>
                    <span class="row-value mono">{{ dataDir }}</span>
                </div>
                <div class="row">
                    <span class="row-label">geoserv url</span>
                    <span class="row-value mono">{{ geoservUrlLabel }}</span>
                </div>
                <div class="row">
                    <span class="row-label">mode</span>
                    <span class="row-value mono">{{ modeLabel }}</span>
                </div>
                <div class="row">
                    <span class="row-label">upload cap</span>
                    <span class="row-value mono">{{ uploadCap }}</span>
                </div>
                <div class="row">
                    <span class="row-label">min area</span>
                    <span class="row-value mono">{{ minAreaLabel }}</span>
                </div>
            </div>
        </SectionCard>

        <SectionCard class="block" title="raw diagnostics" subtitle="exactly what GET /diagnostics returns"
                     flush>
            <pre class="raw">{{ rawDiagnostics }}</pre>
        </SectionCard>
    </div>
</template>

<script lang="ts">
import {
    Component,
    Vue,
} from "vue-property-decorator";

import { getModule } from "vuex-module-decorators";
import { AppModule } from "@/store/app";

import SectionCard from "@/ui/components/SectionCard.vue";
import StatCard from "@/ui/components/StatCard.vue";

import { IModelInfo } from "@/models";

type RowState = "ok" | "warn" | "bad";

interface IRow {
    label: string;
    value: string;
    state: RowState;
}

interface IEndpoint {
    method: string;
    path: string;
    note: string;
}

interface IImageryRow {
    zone: string;
    roles: Record<string, number>;
    zooms: string;
    total: number;
}

@Component({
    components: {
        SectionCard,
        StatCard,
    },
})
export default class SystemView extends Vue {
    private readonly app = getModule(AppModule);

    private get diagnostics() {
        return this.app.diagnostics;
    }

    private get health() {
        return this.app.health;
    }

    private get serviceError(): string | null {
        return this.app.serviceError;
    }

    private get models(): IModelInfo[] {
        return this.diagnostics?.models || [];
    }

    private get loadedModels(): number {
        return this.models.filter(model => model.exists).length;
    }

    // Templates are compiled by vue-template-es2015-compiler, which rejects optional chaining
    // and the nullish operator, so every nullable value is resolved here.
    private get apiStatus(): string {
        return this.health ? this.health.status : "offline";
    }

    private get apiTone(): string {
        return this.health && this.health.status === "ready" ? "good" : "bad";
    }

    private get geoservStatus(): string {
        return this.health && this.health.geoserv_reachable ? "indexed" : "down";
    }

    private get geoservTone(): string {
        return this.health && this.health.geoserv_reachable ? "good" : "bad";
    }

    private get modelsLabel(): string {
        return `${this.loadedModels}/${this.models.length}`;
    }

    private get queueLabel(): string {
        const active = this.health ? this.health.active_jobs : 0;
        const max = this.health ? this.health.max_jobs : 0;
        return `${active}/${max}`;
    }

    private get dataDir(): string {
        return this.diagnostics ? this.diagnostics.data_dir : "-";
    }

    private get geoservUrlLabel(): string {
        if(this.diagnostics) {
            return this.diagnostics.geoserv_url;
        }

        return this.health ? this.health.geoserv_url : "-";
    }

    private get modeLabel(): string {
        if(this.diagnostics) {
            return this.diagnostics.mode;
        }

        return this.health ? this.health.mode : "-";
    }

    private get uploadCap(): string {
        return this.diagnostics ? `${this.diagnostics.max_upload_mb} MB / file` : "-";
    }

    private get minAreaLabel(): string {
        return this.diagnostics ? `${this.diagnostics.min_area} px` : "-";
    }

    private get serviceRows(): IRow[] {
        const health = this.health;

        return [
            {label: "status", value: health?.status || "offline", state: health?.status === "ready" ? "ok" : "bad"},
            {
                label: "geoserv",
                value: health?.geoserv_reachable ? "reachable" : "unreachable",
                state: health?.geoserv_reachable ? "ok" : "bad",
            },
            {
                label: "missing models",
                value: String(health?.missing_models?.length ?? 0),
                state: (health?.missing_models?.length ?? 0) === 0 ? "ok" : "warn",
            },
            {label: "active jobs", value: String(health?.active_jobs ?? 0), state: "ok"},
            {label: "max jobs", value: String(health?.max_jobs ?? 0), state: "ok"},
            {label: "mode", value: health?.mode || "-", state: "ok"},
            {label: "data dir", value: health?.data_dir || "-", state: "ok"},
            {label: "geoserv url", value: health?.geoserv_url || "-", state: "ok"},
        ];
    }

    private get endpoints(): IEndpoint[] {
        return [
            {method: "GET", path: "/health", note: "service state, models, queue"},
            {method: "GET", path: "/diagnostics", note: "everything on this page"},
            {method: "GET", path: "/jobs", note: "job history"},
            {method: "GET", path: "/jobs/{id}", note: "single job poll"},
            {method: "POST", path: "/predict/disaster", note: "upload a GeoTIFF pair"},
        ];
    }

    private get imageryRoles(): string[] {
        const roles = new Set<string>();

        for(const zone of this.diagnostics?.imagery || []) {
            Object.keys(zone.roles).forEach(role => roles.add(role));
        }

        return [...roles].sort();
    }

    private get imageryRows(): IImageryRow[] {
        return (this.diagnostics?.imagery || []).map(zone => {
            const roles: Record<string, number> = {};
            const zooms = new Set<string>();
            let total = 0;

            for(const [role, data] of Object.entries(zone.roles)) {
                roles[role] = data.tiles;
                total += data.tiles;
                Object.keys(data.by_zoom).forEach(zoom => zooms.add(zoom));
            }

            const sorted = [...zooms].map(Number).sort((a, b) => a - b);

            return {
                zone: zone.zone_id,
                roles,
                zooms: sorted.length ? `z${sorted[0]}-${sorted[sorted.length - 1]}` : "-",
                total,
            };
        });
    }

    private get rawDiagnostics(): string {
        return this.diagnostics
            ? JSON.stringify(this.diagnostics, null, 2)
            : "// diagnostics not loaded - check that uvicorn is running on :8099";
    }
}
</script>

<style lang="scss" scoped>
.block {
    margin-top: 16px;
}

.block:last-child {
    margin-bottom: 10px;
}

.rows {
    display: flex;
    flex-direction: column;
}

.row {
    display: flex;
    align-items: center;
    gap: 9px;
    padding: 6px 0;
    border-bottom: 1px solid var(--rahat-border);
    font-size: 12px;
}

.row:last-child {
    border-bottom: none;
}

.row-label {
    color: var(--rahat-text-dim);
    min-width: 120px;
}

.row-value {
    margin-left: auto;
    color: var(--rahat-text);
    font-size: 11px;
    max-width: 70%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    flex: 0 0 auto;
    background: var(--rahat-text-faint);
}

.dot--ok {
    background: var(--rahat-ok);
}

.dot--warn {
    background: var(--rahat-warn);
}

.dot--bad {
    background: var(--rahat-danger);
}

.endpoints {
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.endpoint {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 5px 0;
    border-bottom: 1px solid var(--rahat-border);
    font-size: 11.5px;
}

.endpoint:last-child {
    border-bottom: none;
}

.method {
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.06em;
    padding: 2px 6px;
    border-radius: 2px;
    min-width: 42px;
    text-align: center;
}

.method--get {
    background: var(--rahat-ok-soft);
    color: var(--rahat-ok);
}

.method--post {
    background: var(--rahat-warn-soft);
    color: var(--rahat-warn);
}

.endpoint-path {
    color: var(--rahat-text);
    font-size: 11.5px;
}

.endpoint-note {
    margin-left: auto;
    color: var(--rahat-text-faint);
    font-size: 11px;
}

.table-wrap {
    overflow-x: auto;
}

table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
}

th {
    text-align: left;
    padding: 9px 14px;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--rahat-text-faint);
    border-bottom: 1px solid var(--rahat-border);
}

td {
    padding: 9px 14px;
    border-bottom: 1px solid var(--rahat-border);
    color: var(--rahat-text-dim);
    white-space: nowrap;
}

.role {
    color: var(--rahat-yellow);
}

.path {
    font-size: 11px;
    max-width: 520px;
    overflow: hidden;
    text-overflow: ellipsis;
}

.num {
    text-align: right;
    font-variant-numeric: tabular-nums;
}

.strong {
    color: var(--rahat-text);
    font-weight: 600;
}

.state {
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 2px 7px;
    border-radius: 2px;
}

.state--ok {
    background: var(--rahat-ok-soft);
    color: var(--rahat-ok);
}

.state--bad {
    background: var(--rahat-danger-soft);
    color: var(--rahat-danger);
}

.empty {
    padding: 26px;
    text-align: center;
    color: var(--rahat-text-faint);
}

.raw {
    margin: 0;
    padding: 16px;
    max-height: 420px;
    overflow: auto;
    font-family: var(--rahat-mono);
    font-size: 11px;
    line-height: 1.55;
    color: var(--rahat-text-dim);
    background: var(--rahat-panel);
}
</style>
