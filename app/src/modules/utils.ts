/*
 * DISASTER RESPONSE APP
 * Copyright (c) 2021 SilentByte <https://silentbyte.com/>
 */

/*
 * Vuetify 2 positions a v-select menu from the activator's top edge and never adds the field's own
 * height, so an outlined select opens a panel that sits exactly on top of itself. offsetY drops the
 * panel below the field; the nudge leaves the same 8px gap the bento grid uses between cards.
 *
 * Every select in the app renders the same field, so they all pass this same object.
 */
export const SELECT_MENU_PROPS = {
    offsetY: true,
    nudgeBottom: 8,
};
