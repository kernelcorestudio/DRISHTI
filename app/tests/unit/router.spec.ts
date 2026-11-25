/// <reference types="jest" />
import { createLocalVue, shallowMount } from "@vue/test-utils";
import Vuetify from "vuetify";
import { getModule } from "vuex-module-decorators";

import App from "@/App.vue";
import router from "@/router";
import store from "@/store";
import { AppModule } from "@/store/app";
import * as api from "@/modules/api";
import * as zones from "@/modules/zones";

describe("Router and App navigation", () => {
    const localVue = createLocalVue();

    afterEach(() => {
        jest.restoreAllMocks();
    });

    it("resolves all 10 configured routes and redirects unknown paths to Dashboard", async () => {
        const expectedRoutes = [
            "/",
            "/map",
            "/map/@29.96,-90.02,17z",
            "/report",
            "/analytics",
            "/zones",
            "/inference",
            "/super-resolution",
            "/spectral",
            "/models",
            "/system",
        ];

        for(const path of expectedRoutes) {
            const resolved = router.resolve(path);
            expect(resolved.route.name).toBeTruthy();
        }

        const wildcard = router.resolve("/does-not-exist");
        expect(wildcard.resolved.redirectedFrom).toBe("/does-not-exist");
        expect(wildcard.route.path).toBe("/");
    });

    it("renders navigation rail and surfaces API error in store when refresh fails", async () => {
        jest.spyOn(api, "fetchHealth").mockRejectedValue(new api.ApiRequestError("Failed to fetch"));
        jest.spyOn(api, "fetchDiagnostics").mockRejectedValue(new api.ApiRequestError("Failed to fetch"));
        jest.spyOn(api, "fetchJobs").mockRejectedValue(new api.ApiRequestError("Failed to fetch"));
        jest.spyOn(zones, "fetchDisasterZones").mockResolvedValue([
            {
                id: "zone-uuid-1" as any,
                name: "Harvey 2017",
                center: { lat: 29.84, lng: -95.63, zoom: 18 },
                beforeLayer: null,
                afterLayer: null,
                amenitiesUrl: null,
                affectedStructuresUrl: null,
                unaffectedStructuresUrl: null,
                heatmapUrl: null,
            },
        ]);

        const vuetify = new Vuetify();
        const wrapper = shallowMount(App, {
            localVue,
            store,
            router,
            vuetify,
            stubs: ["router-view"],
        });

        await new Promise(resolve => setTimeout(resolve, 20));
        await wrapper.vm.$nextTick();

        const navItems = wrapper.findAll(".nav-item");
        expect(navItems.length).toBe(10);

        const appModule = getModule(AppModule, store);
        expect(appModule.serviceError).toBe("inference API unreachable - start uvicorn on :8099");
        expect(appModule.disasterZones.length).toBe(1);

        wrapper.destroy();
    });
});
