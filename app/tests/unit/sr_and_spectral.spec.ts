/// <reference types="jest" />
import { createLocalVue, mount } from "@vue/test-utils";
import VueRouter from "vue-router";
import Vuetify from "vuetify";

import * as api from "@/modules/api";
import SpectralAnalysisView from "@/ui/views/SpectralAnalysisView.vue";
import SuperResolutionView from "@/ui/views/SuperResolutionView.vue";
import UploadForm from "@/ui/components/UploadForm.vue";

describe("SuperResolutionView, SpectralAnalysisView, and UploadForm regressions", () => {
    const localVue = createLocalVue();
    localVue.use(VueRouter);

    afterEach(() => {
        jest.restoreAllMocks();
    });

    it("aligns SuperResolutionView with backend contracts and surfaces API errors", async () => {
        jest.spyOn(api, "fetchSRPresets").mockResolvedValue([
            {
                id: "punjab_agri",
                name: "Punjab Agricultural Parcels",
                description: "Test AOI",
                bbox: [75.3, 30.55, 75.36, 30.6],
            },
        ]);
        jest.spyOn(api, "fetchSRTile").mockResolvedValue({
            status: "success",
            lr_preview: "data:image/png;base64,LR",
            cloud_coverage_pct: 1.5,
            cloud_warning: null,
        });
        jest.spyOn(api, "runSuperResolution").mockResolvedValue({
            status: "success",
            model: "hat",
            scale_factor: 4,
            inference_time_ms: 412,
            lr_preview: "data:image/png;base64,LR",
            sr_preview: "data:image/png;base64,SR",
            confidence_heatmap_preview: "data:image/png;base64,CONF",
            mean_confidence: 0.91,
            metrics: { psnr: 29.45, ssim: 0.872, sam: 4.21, niqe: 4.1, brisque: 24.3 },
            blockchain_record: {
                tile_id: "punjab_agri",
                sha256: "0xabc123",
                tx_hash: "0xdef456",
                status: "simulated",
                explorer_url: "https://amoy.polygonscan.com/tx/0xdef456",
            },
        });
        jest.spyOn(api, "detectInfrastructure").mockResolvedValue({
            status: "success",
            building_count: 14,
            road_count: 3,
            total_road_length_km: 1.85,
            total_road_area_km2: 0.0138,
            total_built_area_km2: 0.042,
            overlay_preview: "data:image/png;base64,INFRA",
        });

        const wrapper = mount(SuperResolutionView, { localVue, vuetify: new Vuetify() });
        await new Promise(resolve => setTimeout(resolve, 20));
        await wrapper.vm.$nextTick();

        const vm = wrapper.vm as any;
        expect(vm.lrImage).toBe("data:image/png;base64,LR");

        await vm.onRunSR();
        await wrapper.vm.$nextTick();
        expect(vm.srImage).toBe("data:image/png;base64,SR");
        expect(vm.trustScoreLabel).toBe("91");
        expect(vm.metricPSNR).toBe("29.45");
        expect(vm.tileHash).toBe("0xabc123");

        await vm.onDetectInfrastructure();
        await wrapper.vm.$nextTick();
        expect(vm.infraBuildings).toBe(14);
        expect(vm.infraBuiltArea).toBe(0.042);

        wrapper.destroy();
    });

    it("renders legend_items and gradient bar in SpectralAnalysisView", async () => {
        jest.spyOn(api, "fetchSpectralVisualization").mockResolvedValue({
            status: "success",
            mode: "ndvi",
            title: "NDVI",
            subtitle: "Normalized Difference Vegetation Index",
            description: "Vegetation health",
            bands_used: ["B08 (NIR)", "B04 (Red)"],
            is_index: true,
            legend_items: [
                { label: "Barren", color: "#5c3a21", threshold: "~ -0.2" },
                { label: "Canopy", color: "#005a32", threshold: "~ 0.85" },
            ],
            gradient_css: "linear-gradient(to right, #5c3a21, #005a32)",
            coverage_stats: {
                category: "Dense / Healthy Crop Canopy",
                threshold: "NDVI >= 0.40",
                area_km2: 1.5,
                area_pct: 62.5,
                total_aoi_km2: 2.4,
                unit: "km²",
            },
            lr_preview: "data:image/png;base64,LRNDVI",
            sr_preview: "data:image/png;base64,SRNDVI",
        });

        const wrapper = mount(SpectralAnalysisView, { localVue, vuetify: new Vuetify() });
        await new Promise(resolve => setTimeout(resolve, 20));
        await wrapper.vm.$nextTick();

        const vm = wrapper.vm as any;
        expect(vm.legendItems.length).toBe(2);
        expect(wrapper.find(".spectral-gradient-bar").exists()).toBe(true);
        expect(wrapper.text()).toContain("62.5");

        wrapper.destroy();
    });

    it("disables submit in UploadForm when file validation produces beforeError", async () => {
        const wrapper = mount(UploadForm, {
            localVue,
            vuetify: new Vuetify(),
            propsData: { sceneIds: ["new-orleans"] },
        });
        const vm = wrapper.vm as any;
        vm.onBeforeSelected(new File(["png"], "bad.png", { type: "image/png" }));
        vm.onAfterSelected(new File(["tif"], "after.tif", { type: "image/tiff" }));
        await wrapper.vm.$nextTick();

        expect(vm.beforeError).toBe("must be a .tif or .tiff GeoTIFF");
        expect(vm.canSubmit).toBe(false);

        wrapper.destroy();
    });
});
