/// <reference types="jest" />
import { createLocalVue, mount } from "@vue/test-utils";
import VueRouter from "vue-router";
import Vuetify from "vuetify";
import { getModule } from "vuex-module-decorators";

const mockMapInstance = {
    setView: jest.fn().mockReturnThis(),
    flyTo: jest.fn().mockReturnThis(),
    invalidateSize: jest.fn(),
    createPane: jest.fn(() => ({ style: { zIndex: "" } })),
    on: jest.fn(),
    remove: jest.fn(),
    getZoom: jest.fn(() => 18),
    getCenter: jest.fn(() => ({ lat: 29.843463, lng: -95.632594 })),
    getBounds: jest.fn(() => ({
        getNorthEast: () => ({ lat: 29.85, lng: -95.62 }),
        getSouthWest: () => ({ lat: 29.83, lng: -95.64 }),
    })),
};

const mockTileLayers: Array<{ url: string; addTo: jest.Mock; remove: jest.Mock }> = [];
const mockGeoJsonLayers: Array<{ addTo: jest.Mock; remove: jest.Mock }> = [];
const mockHeatLayers: Array<{ addTo: jest.Mock; remove: jest.Mock }> = [];

jest.mock("leaflet", () => ({
    map: jest.fn(() => mockMapInstance),
    control: { scale: jest.fn(() => ({ addTo: jest.fn() })) },
    tileLayer: jest.fn((url: string) => {
        const layer = { url, addTo: jest.fn().mockReturnThis(), remove: jest.fn() };
        mockTileLayers.push(layer);
        return layer;
    }),
    geoJSON: jest.fn(() => {
        const layer = { addTo: jest.fn().mockReturnThis(), remove: jest.fn() };
        mockGeoJsonLayers.push(layer);
        return layer;
    }),
    heatLayer: jest.fn(() => {
        const layer = { addTo: jest.fn().mockReturnThis(), remove: jest.fn() };
        mockHeatLayers.push(layer);
        return layer;
    }),
    icon: jest.fn(() => ({})),
    marker: jest.fn(() => ({ bindTooltip: jest.fn() })),
}));

jest.mock("leaflet.heat", () => ({}));

import * as L from "leaflet";
import store from "@/store";
import { AppModule } from "@/store/app";
import MapView from "@/ui/views/MapView.vue";
import { IDisasterZone } from "@/models";

describe("MapView", () => {
    const localVue = createLocalVue();
    localVue.use(VueRouter);

    const sampleZone: IDisasterZone = {
        id: "6d6cb92d-921e-5144-9d5e-0af39457e8e0" as any,
        name: "Harvey 2017 - Houston, TX",
        center: { lat: 29.843463, lng: -95.632594, zoom: 18 },
        beforeLayer: {
            urlTemplate: "/tiles/demo-hurricane-harvey_00000146/before/{z}/{x}/{y}.png",
            attributionHtml: "xBD",
        },
        afterLayer: {
            urlTemplate: "/tiles/demo-hurricane-harvey_00000146/after/{z}/{x}/{y}.png",
            attributionHtml: "xBD",
        },
        amenitiesUrl: null,
        affectedStructuresUrl: "http://127.0.0.1:8088/geo/demo-hurricane-harvey_00000146/structures-affected",
        unaffectedStructuresUrl: "http://127.0.0.1:8088/geo/demo-hurricane-harvey_00000146/structures-unaffected",
        heatmapUrl: "http://127.0.0.1:8088/geo/demo-hurricane-harvey_00000146/structures-affected/heatmap",
    };

    beforeEach(() => {
        mockTileLayers.length = 0;
        mockGeoJsonLayers.length = 0;
        mockHeatLayers.length = 0;
        jest.clearAllMocks();

        (window as any).fetch = jest.fn(async (url: string) => {
            if(String(url).includes("/heatmap")) {
                return { ok: true, json: async () => [[29.84, -95.63]] };
            }
            return {
                ok: true,
                json: async () => [
                    {
                        type: "Feature",
                        properties: { severity: "severe", damage_probability: 0.92, confidence: 0.92 },
                        geometry: { type: "Polygon", coordinates: [[[-95.63, 29.84], [-95.629, 29.84], [-95.629, 29.841], [-95.63, 29.84]]] },
                    },
                ],
            };
        });
    });

    it("initializes Leaflet panes, cycles before/after layers, and loads structure GeoJSON", async () => {
        const vuetify = new Vuetify();
        const router = new VueRouter({
            mode: "abstract",
            routes: [{ path: "/map/:options?", name: "Map" }],
        });
        await router.push("/map");

        const appModule = getModule(AppModule, store);
        appModule.setDisasterZones([sampleZone]);
        appModule.setSelectedDisasterZone(sampleZone);

        const wrapper = mount(MapView, { localVue, store, vuetify, router });
        await new Promise(resolve => setTimeout(resolve, 20));
        await wrapper.vm.$nextTick();

        expect(L.map).toHaveBeenCalled();
        expect(mockMapInstance.createPane).toHaveBeenCalledWith("structures");
        expect(mockMapInstance.createPane).toHaveBeenCalledWith("basemap");
        expect(wrapper.text()).toContain("Harvey 2017 - Houston, TX");

        const vm = wrapper.vm as any;
        expect(vm.visibleLayer).toBe("before");

        vm.onToggleLayers();
        await wrapper.vm.$nextTick();
        expect(vm.visibleLayer).toBe("after");

        vm.onToggleLayers();
        await wrapper.vm.$nextTick();
        expect(vm.visibleLayer).toBe("none");

        vm.onToggleDamagePolygons();
        await new Promise(resolve => setTimeout(resolve, 20));
        await wrapper.vm.$nextTick();
        expect(vm.showStructures).toBe(true);
        expect(L.geoJSON).toHaveBeenCalledTimes(2);
        expect(wrapper.find(".map-legend").exists()).toBe(true);

        wrapper.destroy();
    });
});
