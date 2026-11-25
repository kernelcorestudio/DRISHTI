<!--
    DISASTER RESPONSE APP
    Copyright (c) 2021 SilentByte <https://silentbyte.com/>
-->

<template>
    <div class="upload">
        <div class="upload-grid">
            <v-select dense outlined hide-details
                      class="upload-zone"
                      label="target zone"
                      item-value="id"
                      item-text="name"
                      :items="zoneOptions"
                      :menu-props="menuProps"
                      v-model="zoneId" />

            <v-file-input dense outlined hide-details
                          accept=".tif,.tiff"
                          prepend-icon=""
                          prepend-inner-icon="mdi-image-outline"
                          label="before GeoTIFF"
                          :error-messages="beforeError"
                          @change="onBeforeSelected" />

            <v-file-input dense outlined hide-details
                          accept=".tif,.tiff"
                          prepend-icon=""
                          prepend-inner-icon="mdi-image-filter-hdr"
                          label="after GeoTIFF"
                          :error-messages="afterError"
                          @change="onAfterSelected" />
        </div>

        <div class="upload-actions">
            <v-btn small
                   depressed
                   class="submit"
                   :loading="submitting"
                   :disabled="!canSubmit"
                   @click="onSubmit">
                run stage-1 + stage-2
            </v-btn>

            <span class="upload-hint">
                georeferenced .tif / .tiff only, max {{ maxUploadMb }} MB each.
                first run loads both models (~60 s), afterwards ~10-12 s per tile pair.
            </span>
        </div>

        <v-alert v-if="error" dense text type="error" class="upload-alert">{{ error }}</v-alert>

        <div v-if="job" class="job-live">
            <div class="job-head">
                <span class="chip" :class="`chip--${job.status}`">{{ job.status }}</span>
                <span class="mono job-id">{{ job.job_id }}</span>
                <span v-if="job.duration_seconds !== null" class="dim">
                    {{ job.duration_seconds.toFixed(1) }}s
                </span>
                <span class="dim job-zone">{{ job.zone_id }}</span>
            </div>

            <v-progress-linear v-if="!isTerminal"
                               indeterminate
                               height="3"
                               color="warning"
                               class="job-progress" />

            <div v-if="job.status === 'succeeded'" class="job-counts">
                <div class="count count--affected">
                    <span class="count-value">{{ job.affected_structures }}</span>
                    <span class="count-label">affected</span>
                </div>
                <div class="count count--severe">
                    <span class="count-value">{{ job.severe_structures }}</span>
                    <span class="count-label">severe</span>
                </div>
                <div class="count count--moderate">
                    <span class="count-value">{{ job.moderate_structures }}</span>
                    <span class="count-label">moderate</span>
                </div>
                <div class="count count--intact">
                    <span class="count-value">{{ job.unaffected_structures }}</span>
                    <span class="count-label">intact</span>
                </div>
            </div>

            <v-alert v-if="job.warning" dense text type="warning" class="upload-alert">
                {{ job.warning }}
            </v-alert>

            <v-alert v-if="job.error" dense text type="error" class="upload-alert">
                {{ job.error }}
            </v-alert>

            <div v-if="job.artifacts.length" class="artifacts">
                <div v-for="artifact in job.artifacts" :key="artifact" class="mono artifact">
                    {{ artifact }}
                </div>
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
    Watch,
} from "vue-property-decorator";

import { IJob } from "@/models";
import {
    ApiRequestError,
    fetchJob,
    isTerminalJob,
    submitInference,
} from "@/modules/api";
import { SELECT_MENU_PROPS } from "@/modules/utils";

const POLL_INTERVAL_MS = 2000;
const MEGABYTE = 1024 * 1024;

@Component
export default class UploadForm extends Vue {
    @Prop({type: Array, required: true})
    private readonly sceneIds!: string[];

    @Prop({type: Number, default: 512})
    private readonly maxUploadMb!: number;

    private zoneId = "";

    /** Keep the zone panel under its field instead of on top of it; see modules/utils. */
    private readonly menuProps = SELECT_MENU_PROPS;

    private beforeFile: File | null = null;

    private afterFile: File | null = null;

    private beforeError: string | null = null;

    private afterError: string | null = null;

    private submitting = false;

    private job: IJob | null = null;

    private error: string | null = null;

    private timer: number | null = null;

    private get zoneOptions(): Array<{id: string; name: string}> {
        return this.sceneIds.map(sceneId => ({id: sceneId, name: sceneId}));
    }

    private get canSubmit(): boolean {
        return Boolean(this.zoneId && this.beforeFile && this.afterFile) && !this.submitting;
    }

    private get isTerminal(): boolean {
        return Boolean(this.job && isTerminalJob(this.job));
    }

    @Watch("sceneIds", {immediate: true})
    private onSceneIdsChanged(sceneIds: string[]) {
        if(!this.zoneId && sceneIds.length) {
            this.zoneId = sceneIds[0];
        }
    }

    private onBeforeSelected(file: File | File[] | null) {
        this.beforeFile = this.normalizeFile(file);
        this.beforeError = this.validate(this.beforeFile);
    }

    private onAfterSelected(file: File | File[] | null) {
        this.afterFile = this.normalizeFile(file);
        this.afterError = this.validate(this.afterFile);
    }

    private normalizeFile(file: File | File[] | null): File | null {
        return Array.isArray(file) ? file[0] || null : file;
    }

    private validate(file: File | null): string | null {
        if(!file) {
            return null;
        }

        if(!/\.tiff?$/i.test(file.name)) {
            return "must be a .tif or .tiff GeoTIFF";
        }

        if(file.size > this.maxUploadMb * MEGABYTE) {
            return `larger than the ${this.maxUploadMb} MB limit`;
        }

        return null;
    }

    private async onSubmit(): Promise<void> {
        if(!this.canSubmit || !this.beforeFile || !this.afterFile) {
            return;
        }

        this.submitting = true;
        this.error = null;
        this.job = null;

        try {
            const job = await submitInference(this.zoneId, this.beforeFile, this.afterFile);
            this.job = job;
            this.pollJob(job.job_id);
        } catch(reason) {
            this.error = reason instanceof ApiRequestError
                ? reason.message
                : String(reason);
        } finally {
            this.submitting = false;
        }
    }

    private pollJob(jobId: string) {
        this.stopPolling();

        this.timer = window.setTimeout(async () => {
            try {
                const job = await fetchJob(jobId);
                this.job = job;

                if(isTerminalJob(job)) {
                    this.stopPolling();
                    this.$emit("completed", job);
                } else {
                    this.pollJob(jobId);
                }
            } catch(reason) {
                this.stopPolling();
                this.error = reason instanceof ApiRequestError ? reason.message : String(reason);
            }
        }, POLL_INTERVAL_MS);
    }

    private stopPolling() {
        if(this.timer !== null) {
            window.clearTimeout(this.timer);
            this.timer = null;
        }
    }

    beforeDestroy(): void {
        this.stopPolling();
    }
}
</script>

<style lang="scss" scoped>
.upload {
    display: flex;
    flex-direction: column;
    gap: 14px;
}

.upload-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 12px;
    align-items: start;
}

.upload-actions {
    display: flex;
    align-items: center;
    gap: 14px;
    flex-wrap: wrap;
}

.submit {
    background: linear-gradient(135deg, var(--crimson-deep) 0%, var(--crimson-vivid) 100%) !important;
    color: var(--rahat-on-accent) !important;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    box-shadow: 0 0 20px rgba(164, 22, 26, 0.45);
    font-size: 11px !important;
}

.submit.v-btn--disabled {
    background: var(--rahat-border-strong) !important;
    color: var(--rahat-text-faint) !important;
}

.upload-hint {
    font-size: 11px;
    color: var(--rahat-text-faint);
    max-width: 520px;
    line-height: 1.5;
}

.upload-alert {
    border-radius: 2px;
    font-size: 12px;
}

.job-live {
    border: 1px solid var(--rahat-border);
    border-radius: 3px;
    padding: 13px 14px;
    background: var(--rahat-panel);
    display: flex;
    flex-direction: column;
    gap: 10px;
}

.job-head {
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 12px;
    flex-wrap: wrap;
}

.job-id {
    color: var(--rahat-text-dim);
}

.job-zone {
    margin-left: auto;
    font-family: var(--rahat-mono);
    font-size: 11px;
}

.chip {
    padding: 2px 8px;
    border-radius: 2px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.06em;
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

.job-progress {
    margin: 0;
}

.job-counts {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(90px, 1fr));
    gap: 10px;
}

.count {
    border: 1px solid var(--rahat-border);
    border-radius: 3px;
    padding: 9px 11px;
    background: var(--rahat-card);
}

.count-value {
    display: block;
    font-size: 20px;
    font-weight: 600;
    font-variant-numeric: tabular-nums;
}

.count-label {
    font-size: 10px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--rahat-text-faint);
}

.count--affected .count-value {
    color: var(--rahat-yellow);
}

.count--severe .count-value {
    color: var(--rahat-danger);
}

.count--moderate .count-value {
    color: var(--rahat-warn);
}

.count--intact .count-value {
    color: var(--rahat-ok);
}

.artifacts {
    display: flex;
    flex-direction: column;
    gap: 2px;
}

.artifact {
    color: var(--rahat-text-faint);
    font-size: 10px;
    word-break: break-all;
}
</style>
