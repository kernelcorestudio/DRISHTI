/*
 * DISASTER RESPONSE APP
 * Copyright (c) 2021 SilentByte <https://silentbyte.com/>
 */

import { themeRevision } from "@/modules/theme";

/**
 * Resolves a colour for the theme that is currently live.
 *
 * Severity colours have to be concrete hex rather than `var(--...)`: the donut chart does maths
 * on them to shade each slice, and Leaflet writes them as SVG presentation attributes, where a
 * custom property does not resolve. Reading themeRevision.version here makes every chart computed
 * that touches a colour depend on the theme, so a toggle repaints the charts without having to
 * remount the route and throw away page state.
 */
function pick(dark: string, light: string): string {
    void themeRevision.version;
    return document.documentElement.classList.contains("light") ? light : dark;
}

export const SEVERITY_COLORS = {
    get severe(): string { return pick("#fb7185", "#be123c"); },
    get moderate(): string { return pick("#fbb931", "#b45309"); },
    get intact(): string { return pick("#34d399", "#047857"); },
    get affected(): string { return pick("#e0424e", "#a4161a"); },
    get amenities(): string { return pick("#38bdf8", "#0e7490"); },
};

export function formatClock(iso: string | null): string {
    if(!iso) {
        return "-";
    }

    const date = new Date(iso);
    if(Number.isNaN(date.getTime())) {
        return "-";
    }

    return date.toLocaleTimeString([], {hour: "2-digit", minute: "2-digit", second: "2-digit"});
}

export function formatDuration(seconds: number | null): string {
    if(seconds === null || seconds === undefined) {
        return "-";
    }

    if(seconds < 60) {
        return `${seconds.toFixed(1)}s`;
    }

    const minutes = Math.floor(seconds / 60);
    return `${minutes}m ${Math.round(seconds % 60)}s`;
}

export function formatBytes(bytes: number): string {
    if(bytes < 1024) {
        return `${bytes} B`;
    }

    if(bytes < 1024 * 1024) {
        return `${(bytes / 1024).toFixed(1)} KB`;
    }

    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/** Zone ids are scene ids (`palu-tsunami_00000118`); the last segment is the tile number. */
export function shortScene(sceneId: string): string {
    return sceneId.replace(/_\d+$/, "");
}

/**
 * Zone ids are slugs like `demo-hurricane-harvey_00000146`. In a narrow column the ellipsis ate the
 * END of that string, which is the only part that told Harvey, Matthew and Michael apart - every row
 * read `demo-hurrican...`. The UI therefore gets a readable name instead: "Hurricane Harvey".
 */
export function zoneName(zoneId: string): string {
    return shortScene(zoneId)
        .replace(/^(demo|test|sample)[-_]/i, "")
        .split(/[-_]+/)
        .filter(part => !!part)
        .map(part => part.charAt(0).toUpperCase() + part.slice(1))
        .join(" ");
}

export function sceneSuffix(sceneId: string): string {
    const match = /_(\d+)$/.exec(sceneId);
    return match ? `#${match[1]}` : "";
}

export function formatTimestamp(): string {
    return new Date().toLocaleString();
}
