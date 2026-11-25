/*
 * DISASTER RESPONSE APP
 * Copyright (c) 2021 SilentByte <https://silentbyte.com/>
 */

import Vue from "vue";
import Vuetify from "vuetify/lib/framework";

import { readStoredTheme } from "@/modules/theme";

Vue.use(Vuetify);

/*
 * Vuetify gets the same Crimson Hues values as _tokens.scss. Most of the UI reads the CSS custom
 * properties directly, but the components Vuetify paints itself - menus, ripples, skeletons,
 * expansion panels - only understand --v-*, so the two have to stay in step.
 */
const dark = readStoredTheme() === "dark";

export default new Vuetify({
    theme: {
        dark,
        options: {
            customProperties: true,
            variations: false,
        },
        themes: {
            // Pure Black OLED.
            dark: {
                primary: "#a4161a",
                secondary: "#d01e2c",
                accent: "#e0424e",
                error: "#fb7185",
                info: "#38bdf8",
                success: "#34d399",
                warning: "#fbb931",

                background: "#000000",
                card: "#080808",
                surface: "#080808",
                panel: "#080808",
                divider: "rgba(255, 255, 255, 0.08)",
                disabled: "#4a4a55",
            },
            // Rose-white.
            light: {
                primary: "#640d14",
                secondary: "#a4161a",
                accent: "#c81e2b",
                error: "#be123c",
                info: "#0e7490",
                success: "#047857",
                warning: "#b45309",

                background: "#fbf2f3",
                card: "#ffffff",
                surface: "#ffffff",
                panel: "#ffffff",
                divider: "rgba(100, 13, 20, 0.2)",
                disabled: "#c2a3a7",
            },
        },
    },
});
