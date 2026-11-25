<!--
    DISASTER RESPONSE APP
    Copyright (c) 2021 SilentByte <https://silentbyte.com/>
-->

<template>
    <div class="page">
        <div class="grid grid--kpi">
            <StatCard label="queue" :value="queueLabel" hint="jobs run one at a time" />
            <StatCard label="upload cap" :value="uploadCapValue" unit="MB" hint="per GeoTIFF" />
            <StatCard label="min area" :value="minArea" unit="px" hint="speckle filter" />
            <StatCard label="mode" :value="modeLabel" hint="real models loaded" />
        </div>

        <SectionCard class="block"
                     title="run inference"
                     subtitle="stage-1 footprints + stage-2 damage -> geojson -> geoserv reload">
            <UploadForm :scene-ids="sceneIds"
                        :max-upload-mb="maxUploadMb"
                        @completed="onCompleted" />
        </SectionCard>

        <SectionCard class="block"
                     title="active jobs"
                     subtitle="serialized worker, one tile pair at a time"
                     flush>
            <div class="active">
                <div v-for="job in pendingJobs" :key="job.job_id" class="active-row">
                    <span class="chip" :class="`chip--${job.status}`">{{ job.status }}</span>
                    <span class="mono">{{ job.zone_id }}</span>
                    <span class="faint">{{ job.job_id.slice(0, 8) }}</span>
                    <v-progress-linear indeterminate height="2" color="warning" class="active-bar" />
                </div>

                <div v-if="!pendingJobs.length" class="empty">
                    idle - no job running or queued
                </div>
            </div>
        </SectionCard>

        <SectionCard class="block"
                     title="job history"
                     :subtitle="historyLabel"
                     flush>
            <JobTable :jobs="jobs" />
        </SectionCard>

        <SectionCard class="block" title="what the job writes" subtitle="artefacts land in the geoserv data directory">
            <div class="artefact-list">
                <div class="artefact">
                    <span class="mono path">structures-affected.geojson</span>
                    <span class="faint">damaged footprints with severity, damage_probability, confidence</span>
                </div>
                <div class="artefact">
                    <span class="mono path">structures-unaffected.geojson</span>
                    <span class="faint">intact footprints, severity "none"</span>
                </div>
                <div class="artefact">
                    <span class="mono path">heatmap.json</span>
                    <span class="faint">point list rendered by leaflet.heat</span>
                </div>
                <div class="artefact">
                    <span class="mono path">before-after previews</span>
                    <span class="faint">shown once the map redraws for the zone</span>
                </div>
            </div>
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

import JobTable from "@/ui/components/JobTable.vue";
import SectionCard from "@/ui/components/SectionCard.vue";
import StatCard from "@/ui/components/StatCard.vue";
import UploadForm from "@/ui/components/UploadForm.vue";

import { IJob } from "@/models";
import { fetchJobs } from "@/modules/api";

@Component({
    components: {
        JobTable,
        SectionCard,
        StatCard,
        UploadForm,
    },
})
export default class InferenceView extends Vue {
    private readonly app = getModule(AppModule);

    private get diagnostics() {
        return this.app.diagnostics;
    }

    private get health() {
        return this.app.health;
    }

    private get jobs(): IJob[] {
        return this.app.jobs;
    }

    private get sceneIds(): string[] {
        return (this.diagnostics?.zones || []).map(zone => zone.zone_id);
    }

    private get activeJobs(): number {
        return this.app.health?.active_jobs || 0;
    }

    private get maxJobs(): number {
        return this.app.health?.max_jobs || this.diagnostics?.queue.max || 0;
    }

    private get pendingJobs(): IJob[] {
        return this.jobs.filter(job => job.status === "running" || job.status === "queued");
    }

    // Templates cannot use optional chaining (vue-template-es2015-compiler), so resolve here.
    private get queueLabel(): string {
        return `${this.activeJobs}/${this.maxJobs}`;
    }

    private get uploadCapValue(): number {
        return this.diagnostics ? this.diagnostics.max_upload_mb : 0;
    }

    private get maxUploadMb(): number {
        return this.uploadCapValue || 512;
    }

    private get minArea(): number {
        return this.diagnostics ? this.diagnostics.min_area : 0;
    }

    private get modeLabel(): string {
        if(this.diagnostics) {
            return this.diagnostics.mode;
        }

        return this.health ? this.health.mode : "-";
    }

    private get historyLabel(): string {
        return `${this.jobs.length} job(s) this session (in-memory, cleared on api restart)`;
    }

    private async onCompleted(job: IJob) {
        // Pull the job list straight away instead of waiting for the shell's 10 s poll.
        try {
            this.app.setJobs(await fetchJobs());
            this.app.markSynced();
        } catch(error) {
            this.app.setServiceError(error instanceof Error ? error.message : String(error));
        }

        if(job.status === "failed") {
            this.app.setServiceError(job.error || "inference job failed");
        }
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

.active {
    padding: 6px 0;
}

.active-row {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 16px;
    font-size: 12px;
    border-bottom: 1px solid var(--rahat-border);
}

.active-bar {
    flex: 1 1 auto;
    max-width: 220px;
    margin-left: auto;
}

.empty {
    padding: 22px 16px;
    text-align: center;
    font-size: 12px;
    color: var(--rahat-text-faint);
}

.chip {
    padding: 2px 8px;
    border-radius: 2px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}

.chip--running {
    background: var(--rahat-warn-soft);
    color: var(--rahat-warn);
}

.chip--queued {
    background: var(--rahat-info-soft);
    color: var(--rahat-info);
}

.artefact-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.artefact {
    display: flex;
    flex-direction: column;
    gap: 2px;
    padding: 6px 0;
    border-bottom: 1px solid var(--rahat-border);
}

.artefact:last-child {
    border-bottom: none;
}

.path {
    color: var(--rahat-yellow);
    font-size: 11.5px;
}

.artefact .faint {
    font-size: 11px;
}
</style>
