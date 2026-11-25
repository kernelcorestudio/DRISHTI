/*
 * DISASTER RESPONSE APP
 * Copyright (c) 2021 SilentByte <https://silentbyte.com/>
 */

import {
    Module,
    Mutation,
    VuexModule,
} from "vuex-module-decorators";

import store from "@/store";
import vuetify from "@/plugins/vuetify";

import {
    applyTheme,
    bumpThemeRevision,
    persistTheme,
    readStoredTheme,
    ThemeName,
} from "@/modules/theme";

/**
 * The work both mutations need.
 *
 * A @Mutation body is invoked with `this` bound to the module *state object*, not to the class
 * instance, so `this.setTheme(...)` from inside `toggleTheme` threw "setTheme is not a function"
 * and the toggle silently did nothing. Sharing the logic through a plain function keeps the state
 * write and the side effects in one place without nesting mutations.
 */
function writeTheme(state: { theme: ThemeName }, theme: ThemeName): void {
    state.theme = theme;

    applyTheme(theme);
    persistTheme(theme);
    vuetify.framework.theme.dark = theme === "dark";
    bumpThemeRevision();
}

@Module({
    store,
    dynamic: true,
    namespaced: true,
    name: "theme",
})
export class ThemeModule extends VuexModule {
    theme: ThemeName = readStoredTheme();

    get isDark(): boolean {
        return this.theme === "dark";
    }

    /**
     * Switches theme. Vuetify tracks its own `dark` flag for the components it paints itself
     * (menus, ripples, skeletons), so it has to be flipped alongside the CSS classes on <html> -
     * otherwise the page is cream while its dropdowns are still black.
     */
    @Mutation
    setTheme(theme: ThemeName): void {
        writeTheme(this, theme);
    }

    @Mutation
    toggleTheme(): void {
        writeTheme(this, this.theme === "dark" ? "light" : "dark");
    }
}
