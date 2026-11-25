/*
 * DISASTER RESPONSE APP
 * Copyright (c) 2021 SilentByte <https://silentbyte.com/>
 */

/*
 * "Cyber-Sunset" design system: Pure Black OLED (dark) + Warm Sunset Cream (light).
 *
 * Tailwind runs as a standalone CLI step (see the `tw` script in package.json) rather than as a
 * PostCSS plugin, because this project is on Vue CLI 4 / PostCSS 7 and Tailwind 3 needs
 * PostCSS 8. The CLI carries its own PostCSS 8, so nothing in the existing build chain moves.
 */

/** @type {import("tailwindcss").Config} */
module.exports = {
    // Vuetify ships its own reset. Tailwind's preflight zeroes border-widths on every element
    // and rewrites form/heading defaults, which breaks Vuetify's outlined fieldsets and
    // v-application typography - so only the utility layer is generated.
    corePlugins: {
        preflight: false,
    },

    // The theme is a `dark` / `light` class on <html>, applied before mount by an inline
    // script in public/index.html so the first paint is already the right colour.
    darkMode: "class",

    content: [
        "./public/**/*.html",
        "./src/**/*.vue",
        "./src/**/*.ts",
    ],

    theme: {
        extend: {
            colors: {
                // Raw palette. Every value here is quoted from the design spec.
                sunset: {
                    deep: "#EA6113",
                    vivid: "#F88F22",
                    amber: "#FBB931",
                    cream: "#FFE3B3",
                },
                oled: {
                    canvas: "#000000",
                    surface: "#080808",
                    soft: "#121212",
                    warm: "#16110D",
                },
                parchment: {
                    canvas: "#FFE3B3",
                    surface: "#FFF8EB",
                    soft: "#FFEDCC",
                    deep: "#F7D8A7",
                },
                espresso: {
                    DEFAULT: "#1F0E02",
                    soft: "#6B3B10",
                    muted: "#8C5523",
                },

                // Semantic aliases. These resolve through CSS custom properties, so a single
                // `.dark` / `.light` swap on <html> retints every component at once.
                rahat: {
                    bg: "var(--rahat-bg)",
                    panel: "var(--rahat-panel)",
                    card: "var(--rahat-card)",
                    surface: "var(--rahat-surface-2)",
                    warm: "var(--rahat-surface-warm)",
                    line: "var(--rahat-border)",
                    "line-strong": "var(--rahat-border-strong)",
                    text: "var(--rahat-text)",
                    bright: "var(--rahat-text-bright)",
                    dim: "var(--rahat-text-dim)",
                    faint: "var(--rahat-text-faint)",
                    accent: "var(--rahat-accent)",
                    accent2: "var(--rahat-accent-2)",
                    highlight: "var(--rahat-highlight)",
                    ok: "var(--rahat-ok)",
                    warn: "var(--rahat-warn)",
                    danger: "var(--rahat-danger)",
                    info: "var(--rahat-info)",
                    purple: "var(--rahat-purple)",
                },
            },

            borderRadius: {
                card: "10px",
                control: "8px",
            },

            boxShadow: {
                // The signature warm glow under primary actions.
                glow: "0 0 20px rgba(234, 97, 19, 0.35)",
                "glow-soft": "0 0 14px rgba(234, 97, 19, 0.22)",
                "glow-amber": "0 0 18px rgba(251, 185, 49, 0.30)",
                // Floating panels lift off the canvas without turning into a grey drop shadow.
                panel: "0 18px 48px rgba(0, 0, 0, 0.55)",
                "panel-light": "0 18px 48px rgba(120, 53, 15, 0.14)",
            },

            backgroundImage: {
                sunset: "linear-gradient(135deg, #EA6113 0%, #F88F22 100%)",
                "sunset-soft": "linear-gradient(135deg, rgba(234, 97, 19, 0.16) 0%, rgba(251, 185, 49, 0.10) 100%)",
                "dock-aura": "linear-gradient(90deg, rgba(234, 97, 19, 0.25) 0%, rgba(248, 143, 34, 0.45) 50%, rgba(234, 97, 19, 0.25) 100%)",
            },

            backdropBlur: {
                dock: "24px",
            },

            fontFamily: {
                mono: ["SFMono-Regular", "Consolas", "Liberation Mono", "monospace"],
            },

            transitionTimingFunction: {
                sunset: "cubic-bezier(0.22, 0.61, 0.36, 1)",
            },
        },
    },

    plugins: [],
};
