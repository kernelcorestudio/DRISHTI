/*
 * DISASTER RESPONSE APP
 * Copyright (c) 2021 SilentByte <https://silentbyte.com/>
 */

import Vue from "vue";

export type ThemeName = "dark" | "light";

export const THEME_STORAGE_KEY = "rahat.theme";

export const DEFAULT_THEME: ThemeName = "dark";

/*
 * Charts and the map compute their colours in JavaScript (SVG fills, Leaflet path styles), so a
 * CSS custom property swap on <html> cannot reach them. Bumping this counter re-runs every
 * getter that reads it, which repaints those surfaces without remounting the route and throwing
 * away page state such as the map's zoom and selected zone.
 */
export const themeRevision = Vue.observable({version: 0});

/**
 * `?theme=light` / `?theme=dark` forces a theme for a single page load without persisting it.
 * It makes a link shareable in a specific theme and keeps screenshots deterministic; the toggle
 * still wins for the rest of the session.
 */
function readForcedTheme(): ThemeName | null {
    try {
        const forced = new URLSearchParams(window.location.search).get("theme");
        if(forced === "dark" || forced === "light") {
            return forced;
        }
    } catch(error) {
        // No URLSearchParams support means no override, which is the normal path anyway.
    }

    return null;
}

/**
 * Reads the persisted theme. Anything that is not an explicit choice falls back to the OLED
 * default, including localStorage being unavailable in private browsing.
 */
export function readStoredTheme(): ThemeName {
    const forced = readForcedTheme();
    if(forced) {
        return forced;
    }

    try {
        const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
        if(stored === "dark" || stored === "light") {
            return stored;
        }
    } catch(error) {
        // Storage can throw when blocked by policy; the default theme is a fine answer.
    }

    return DEFAULT_THEME;
}

export function persistTheme(theme: ThemeName): void {
    try {
        window.localStorage.setItem(THEME_STORAGE_KEY, theme);
    } catch(error) {
        // Persisting is a convenience, not a requirement; the session still works without it.
    }
}

export function bumpThemeRevision(): void {
    themeRevision.version += 1;
}

/**
 * Puts the `dark` / `light` class on <html> without any animation. Used at boot, where an
 * animated fade from the previous theme would be visible as a flash.
 */
export function applyThemeClass(theme: ThemeName): void {
    const root = document.documentElement;
    root.classList.remove("dark", "light");
    root.classList.add(theme);

    // `color-scheme` hands the native scrollbars, form controls and caret to the right palette.
    // Set through the property API because this TypeScript DOM lib predates style.colorScheme.
    root.style.setProperty("color-scheme", theme);
}

/**
 * Swaps the theme with the one-shot colour transition from _tokens.scss. The class is removed
 * again as soon as the animation window closes so hovers are not routed through `transition`
 * for the rest of the session.
 */
export function applyTheme(theme: ThemeName): void {
    const root = document.documentElement;
    root.classList.add("theme-switching");
    applyThemeClass(theme);
    window.setTimeout(() => root.classList.remove("theme-switching"), 320);
}
