/// <reference types="jest" />
import { createLocalVue, mount } from "@vue/test-utils";
import VueRouter from "vue-router";
import Vuetify from "vuetify";
import { getModule } from "vuex-module-decorators";

import store from "@/store";
import { AppModule } from "@/store/app";
import DashboardView from "@/ui/views/DashboardView.vue";
import { IDiagnostics, IHealth, IJob } from "@/models";

describe("DashboardView", () => {
    const localVue = createLocalVue();
    localVue.use(VueRouter);

    let vuetify: Vuetify;
    let router: VueRouter;
    let appModule: AppModule;

    const sampleHealth: IHealth = {
        status: "ready",
        mode: "real",
        data_dir: "/data",
        geoserv_url: "http://127.0.0.1:8088",
        geoserv_reachable: true,
        missing_models: [],
        active_jobs: 0,
        max_jobs: 4,
    };

    const sampleDiagnostics: IDiagnostics = {
        mode: "real",
        min_area: 20,
        max_upload_mb: 512,
        data_dir: "/data",
        geoserv_url: "http://127.0.0.1:8088",
        models: [
            {
                role: "stage1",
                path: "models/predict_footprint_fine_tuned.pkl",
                exists: true,
                size_mb: 236.7,
                meta: {
                    metrics: { footprint_recall: 0.857, footprint_precision: 0.731 },
                },
            },
            {
                role: "stage2",
                path: "models/predict_damage_unfrozen.pkl",
                exists: true,
                size_mb: 115.7,
                meta: {
                    metrics: { matthew_macro_f1_3class_merged: 0.389 },
                },
            },
        ],
        zones: [
            {
                zone_id: "new-orleans",
                layers: {
                    "structures-affected": {
                        features: 12,
                        bytes: 2048,
                        severity: { severe: 5, moderate: 7 },
                    },
                    "structures-unaffected": {
                        features: 30,
                        bytes: 4096,
                        severity: { none: 30 },
                    },
                },
            },
        ],
        imagery: [
            {
                zone_id: "demo-hurricane-harvey_00000146",
                roles: {
                    before: { tiles: 21, by_zoom: { "15": 1, "16": 4, "17": 16 } },
                    after: { tiles: 21, by_zoom: { "15": 1, "16": 4, "17": 16 } },
                },
            },
        ],
        queue: { active: 0, max: 4 },
        evaluation: {
            measured_on: "2026-11-07",
            scenes: ["hurricane-harvey_00000146"],
            footprint_iou_mean: 0.408,
            footprint_iou_by_scene: { "hurricane-harvey_00000146": 0.425 },
            buildings_classified: 908,
            min_area_sweep: [{ min_area: 20, mean_iou: 0.473, polygons_per_tile: 184 }],
            selected_min_area: 20,
            tile_alignment_drgb_mean: 5.6,
            notes: [],
        },
    };

    const sampleJobs: IJob[] = [
        {
            job_id: "12345678-1234-4234-8234-1234567890ab",
            zone_id: "new-orleans",
            status: "succeeded",
            created_at: "2026-11-25T07:00:00Z",
            started_at: "2026-11-25T07:00:01Z",
            finished_at: "2026-11-25T07:00:12Z",
            duration_seconds: 11.2,
            tiles: 1,
            affected_structures: 12,
            unaffected_structures: 30,
            severe_structures: 5,
            moderate_structures: 7,
            artifacts: ["structures-affected.geojson"],
            error: null,
            warning: null,
        },
    ];

    beforeEach(() => {
        vuetify = new Vuetify();
        router = new VueRouter({ mode: "abstract", routes: [{ path: "/inference", name: "Inference" }] });
        appModule = getModule(AppModule, store);
        appModule.setHealth(sampleHealth);
        appModule.setDiagnostics(sampleDiagnostics);
        appModule.setJobs(sampleJobs);
        appModule.setServiceError(null);
    });

    it("renders KPI totals, pipeline health, and job history from store diagnostics", () => {
        const wrapper = mount(DashboardView, { localVue, store, vuetify, router });
        const text = wrapper.text();

        expect(text).toContain("zones indexed");
        expect(text).toContain("buildings mapped");
        expect(text).toContain("live");
        expect(text).toContain("0.408");
        expect(text).toContain("offline tiles 42");
        expect(text).toContain("new-orleans");
        expect(wrapper.find(".service-alert").exists()).toBe(false);

        wrapper.destroy();
    });

    it("renders service alert when API error is present in store", async () => {
        appModule.setServiceError("inference API unreachable - start uvicorn on :8099");
        appModule.setHealth(null);

        const wrapper = mount(DashboardView, { localVue, store, vuetify, router });
        await wrapper.vm.$nextTick();

        expect(wrapper.find(".service-alert").exists()).toBe(true);
        expect(wrapper.text()).toContain("inference API unreachable - start uvicorn on :8099");
        expect(wrapper.text()).toContain("offline");

        wrapper.destroy();
    });
});
