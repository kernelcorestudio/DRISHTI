<!--
    DISASTER RESPONSE APP
    Copyright (c) 2021 SilentByte <https://silentbyte.com/>
-->

<template>
    <section class="section-card">
        <header class="section-head">
            <div class="section-titles">
                <div class="section-title">{{ title }}</div>
                <div v-if="subtitle" class="section-subtitle">{{ subtitle }}</div>
            </div>

            <div class="section-actions">
                <slot name="actions" />
            </div>
        </header>

        <div class="section-body" :class="{'section-body--flush': flush}">
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

@Component
export default class SectionCard extends Vue {
    @Prop({type: String, required: true})
    private readonly title!: string;

    @Prop({type: String, default: ""})
    private readonly subtitle!: string;

    @Prop({type: Boolean, default: false})
    private readonly flush!: boolean;
}
</script>

<style lang="scss" scoped>
.section-card {
    background: var(--rahat-card);
    border: 1px solid var(--rahat-border);
    border-radius: 4px;
    display: flex;
    flex-direction: column;
    min-width: 0;
    overflow: hidden;
}

.section-head {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 13px 16px 12px;
    border-bottom: 1px solid var(--rahat-border);
}

.section-titles {
    min-width: 0;
    flex: 1 1 auto;
}

.section-title {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--rahat-yellow);
}

.section-subtitle {
    margin-top: 3px;
    font-size: 12px;
    color: var(--rahat-text-faint);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.section-actions {
    flex: 0 0 auto;
    display: flex;
    align-items: center;
    gap: 8px;
}

.section-body {
    padding: 14px 16px 16px;
    flex: 1 1 auto;
    min-width: 0;
}

.section-body--flush {
    padding: 0;
}
</style>
