<!--
    DISASTER RESPONSE APP
    Copyright (c) 2021 SilentByte <https://silentbyte.com/>
-->

<template>
    <div class="job-table">
        <table>
            <thead>
            <tr>
                <th v-for="col in columns" :key="col.key" :class="{num: col.num}">
                    <span v-if="withIcons" class="th-icon" aria-hidden="true">
                        <svg viewBox="0 0 24 24"
                             fill="none" stroke="currentColor" stroke-width="1.7"
                             stroke-linecap="round" stroke-linejoin="round">
                            <path v-for="(d, i) in col.paths" :key="i" :d="d" />
                        </svg>
                    </span>
                    {{ col.label }}
                </th>
            </tr>
            </thead>

            <tbody>
            <tr v-for="job in visibleJobs" :key="job.job_id">
                <td class="mono dim">{{ clock(job.created_at) }}</td>

                <td>
                    <span class="chip" :class="`chip--${job.status}`">{{ job.status }}</span>
                </td>

                <td class="zone">
                    <span class="zone-name">{{ zone(job.zone_id) }}</span>
                    <span class="zone-suffix">{{ suffix(job.zone_id) }}</span>
                </td>

                <td class="num">{{ job.tiles }}</td>
                <td class="num strong">{{ job.affected_structures }}</td>
                <td class="num severe">{{ job.severe_structures }}</td>
                <td class="num moderate">{{ job.moderate_structures }}</td>
                <td class="num dim">{{ duration(job.duration_seconds) }}</td>
            </tr>

            <tr v-if="!visibleJobs.length">
                <td colspan="8" class="empty">
                    <slot name="empty">{{ emptyLabel }}</slot>
                </td>
            </tr>
            </tbody>
        </table>

        <p v-for="job in failedJobs" :key="`${job.job_id}-error`" class="job-error">
            <span class="mono">{{ job.job_id.slice(0, 8) }}</span>
            {{ job.error }}
        </p>
    </div>
</template>

<!--suppress JSUnusedGlobalSymbols -->
<script lang="ts">
import {
    Component,
    Prop,
    Vue,
} from "vue-property-decorator";

import { IJob } from "@/models";
import {
    formatClock,
    formatDuration,
    sceneSuffix,
    shortScene,
} from "@/modules/format";

interface IColumn {
    key: string;
    label: string;
    num?: boolean;
    paths: string[];
}

@Component
export default class JobTable extends Vue {
    @Prop({type: Array, required: true})
    private readonly jobs!: IJob[];

    @Prop({type: Number, default: 0})
    private readonly limit!: number;

    @Prop({type: String, default: "no jobs yet - submit a GeoTIFF pair on the Inference page"})
    private readonly emptyLabel!: string;

    /** Draws a small glyph before each column label; the dashboard wants them, other pages do not. */
    @Prop({type: Boolean, default: false})
    private readonly withIcons!: boolean;

    /**
     * Header definitions. The glyphs are inline paths rather than an icon font so the table keeps
     * its column order and meaning in one place.
     */
    private readonly columns: IColumn[] = [
        {
            key: "time",
            label: "time",
            paths: ["M12 20.8a8.8 8.8 0 1 1 0-17.6 8.8 8.8 0 0 1 0 17.6Z", "M12 7.4v5l3.3 2"],
        },
        {
            key: "status",
            label: "status",
            paths: ["M3.4 12h3.1l2-5.1 3 10.2 2.2-5.9 1.6 3.1h4.7"],
        },
        {
            key: "zone",
            label: "zone",
            paths: [
                "M12 21.2s6.4-6.1 6.4-10.4a6.4 6.4 0 1 0-12.8 0c0 4.3 6.4 10.4 6.4 10.4Z",
                "M12 10.6a1.6 1.6 0 1 0 0-3.2 1.6 1.6 0 0 0 0 3.2Z",
            ],
        },
        {
            key: "tiles",
            label: "tiles",
            num: true,
            paths: [
                "M4.8 4.8h4.4v4.4H4.8zM14.8 4.8h4.4v4.4h-4.4z",
                "M4.8 14.8h4.4v4.4H4.8zM14.8 14.8h4.4v4.4h-4.4z",
            ],
        },
        {
            key: "affected",
            label: "affected",
            num: true,
            paths: ["M13.4 3.4 6.6 13.4h4.4l-1 7.2 6.8-9.8h-4.4l1-7.4Z"],
        },
        {
            key: "severe",
            label: "severe",
            num: true,
            paths: ["M12 4.4 2.9 20h18.2L12 4.4Z", "M12 9.8v4.2", "M12 17.2h.01"],
        },
        {
            key: "moderate",
            label: "moderate",
            num: true,
            paths: ["M12 20.8a8.8 8.8 0 1 1 0-17.6 8.8 8.8 0 0 1 0 17.6Z", "M12 8.2v4.6", "M12 16.2h.01"],
        },
        {
            key: "duration",
            label: "duration",
            num: true,
            paths: [
                "M12 21a7.6 7.6 0 1 0 0-15.2 7.6 7.6 0 0 0 0 15.2Z",
                "M12 10.6V14l2.4 1.5",
                "M9.8 2.8h4.4",
            ],
        },
    ];

    private get visibleJobs(): IJob[] {
        return this.limit > 0 ? this.jobs.slice(0, this.limit) : this.jobs;
    }

    private get failedJobs(): IJob[] {
        return this.visibleJobs.filter(job => job.status === "failed" && job.error);
    }

    // Wrappers keep the template free of name clashes with the imported helpers.
    private clock(iso: string | null): string {
        return formatClock(iso);
    }

    private duration(seconds: number | null): string {
        return formatDuration(seconds);
    }

    private zone(zoneId: string): string {
        return shortScene(zoneId);
    }

    private suffix(zoneId: string): string {
        return sceneSuffix(zoneId);
    }
}
</script>

<style lang="scss" scoped>
.job-table {
    width: 100%;
    overflow-x: auto;
}

table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
}

th {
    text-align: left;
    padding: 7px 10px;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--rahat-text-faint);
    border-bottom: 1px solid var(--rahat-border);
    white-space: nowrap;
}

td {
    padding: 8px 10px;
    border-bottom: 1px solid var(--rahat-border);
    color: var(--rahat-text-dim);
    white-space: nowrap;
}

.th-icon {
    display: inline-flex;
    width: 12px;
    height: 12px;
    margin-right: 5px;
    vertical-align: -2px;
    opacity: 0.75;
}

.th-icon svg {
    width: 100%;
    height: 100%;
}

tbody tr:hover {
    background: var(--rahat-accent-soft);
}

.num {
    text-align: right;
    font-variant-numeric: tabular-nums;
}

.strong {
    color: var(--rahat-text);
    font-weight: 600;
}

.severe {
    color: var(--rahat-danger);
}

.moderate {
    color: var(--rahat-warn);
}

.zone-name {
    color: var(--rahat-text);
}

.zone-suffix {
    margin-left: 3px;
    color: var(--rahat-text-faint);
    font-family: var(--rahat-mono);
    font-size: 10px;
}

.chip {
    display: inline-block;
    padding: 2px 7px;
    border-radius: 2px;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    background: var(--rahat-surface-2);
    color: var(--rahat-text-dim);
}

.chip--succeeded {
    background: var(--rahat-ok-soft);
    color: var(--rahat-ok);
}

.chip--running {
    background: var(--rahat-warn-soft);
    color: var(--rahat-warn);
}

.chip--queued {
    background: var(--rahat-info-soft);
    color: var(--rahat-info);
}

.chip--failed {
    background: var(--rahat-danger-soft);
    color: var(--rahat-danger);
}

.empty {
    padding: 26px 10px;
    text-align: center;
    color: var(--rahat-text-faint);
    white-space: normal;
}

.job-error {
    margin: 8px 0 0;
    font-size: 11px;
    color: var(--rahat-danger);
    white-space: normal;
}
</style>
