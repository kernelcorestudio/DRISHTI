import Vue from "vue";
import Vuetify from "vuetify";

Vue.config.productionTip = false;
Vue.use(Vuetify);

if(typeof window !== "undefined") {
    if(!window.matchMedia) {
        (window as any).matchMedia = (query: string) => ({
            matches: query.includes("prefers-reduced-motion"),
            media: query,
            onchange: null,
            addListener: () => undefined,
            removeListener: () => undefined,
            addEventListener: () => undefined,
            removeEventListener: () => undefined,
            dispatchEvent: () => false,
        });
    }
    if(!window.requestAnimationFrame) {
        window.requestAnimationFrame = (cb: FrameRequestCallback): number => window.setTimeout(() => cb(Date.now()), 0);
    }
    if(!window.cancelAnimationFrame) {
        window.cancelAnimationFrame = (id: number): void => window.clearTimeout(id);
    }
}
