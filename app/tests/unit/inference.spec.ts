/// <reference types="jest" />
import { createLocalVue, mount } from "@vue/test-utils";
import Vuetify from "vuetify";

import { IJob } from "@/models";
import * as api from "@/modules/api";
import JobTable from "@/ui/components/JobTable.vue";
import UploadForm from "@/ui/components/UploadForm.vue";

describe("API error handling, upload validation, and job progress", () => {
    const localVue = createLocalVue();
    let vuetify: Vuetify;

    beforeEach(() => {
        vuetify = new Vuetify();
    });

    afterEach(() => {
        jest.restoreAllMocks();
        jest.useRealTimers();
    });

    it("wraps non-OK HTTP responses in ApiRequestError and parses zone IDs", async () => {
        const mockFetch = jest.fn().mockResolvedValue({
            ok: false,
            status: 503,
            statusText: "Service Unavailable",
            text: async () => "model files are missing",
        });
        (window as any).fetch = mockFetch;

        await expect(api.fetchHealth()).rejects.toThrow("503 Service Unavailable: model files are missing");
        expect(api.sceneIdFromLayerUrl("http://127.0.0.1:8088/geo/new-orleans/structures-affected")).toBe("new-orleans");
        expect(api.isTerminalJob({ status: "succeeded" } as IJob)).toBe(true);
        expect(api.isTerminalJob({ status: "running" } as IJob)).toBe(false);
        expect(api.statusColor("failed")).toBe("error");
    });

    it("validates GeoTIFF extension and size limits in UploadForm", async () => {
        const wrapper = mount(UploadForm, {
            localVue,
            vuetify,
            propsData: {
                sceneIds: ["new-orleans", "oman"],
                maxUploadMb: 1,
            },
        });

        const vm = wrapper.vm as any;
        const badFile = new File(["png"], "tile.png", { type: "image/png" });
        vm.onBeforeSelected(badFile);
        await wrapper.vm.$nextTick();
        expect(vm.beforeError).toBe("must be a .tif or .tiff GeoTIFF");

        const oversized = new File([new Uint8Array(2 * 1024 * 1024)], "big.tif", { type: "image/tiff" });
        vm.onAfterSelected(oversized);
        await wrapper.vm.$nextTick();
        expect(vm.afterError).toBe("larger than the 1 MB limit");

        const validBefore = new File(["tiff"], "before.tif", { type: "image/tiff" });
        const validAfter = new File(["tiff"], "after.tif", { type: "image/tiff" });
        vm.onBeforeSelected(validBefore);
        vm.onAfterSelected(validAfter);
        await wrapper.vm.$nextTick();
        expect(vm.beforeError).toBeNull();
        expect(vm.afterError).toBeNull();
        expect(vm.canSubmit).toBe(true);

        wrapper.destroy();
    });

    it("submits inference job, displays live progress, polls to completion, and handles API errors", async () => {
        jest.useFakeTimers();

        const runningJob: IJob = {
            job_id: "aaaa1111-2222-4333-8444-555566667777",
            zone_id: "new-orleans",
            status: "running",
            created_at: "2026-11-25T07:10:00Z",
            started_at: "2026-11-25T07:10:01Z",
            finished_at: null,
            duration_seconds: null,
            tiles: 0,
            affected_structures: 0,
            unaffected_structures: 0,
            severe_structures: 0,
            moderate_structures: 0,
            artifacts: [],
            error: null,
            warning: null,
        };

        const finishedJob: IJob = {
            ...runningJob,
            status: "succeeded",
            finished_at: "2026-11-25T07:10:09Z",
            duration_seconds: 8.4,
            tiles: 1,
            affected_structures: 42,
            unaffected_structures: 126,
            severe_structures: 15,
            moderate_structures: 27,
            artifacts: ["structures-affected.geojson", "structures-unaffected.geojson"],
        };

        jest.spyOn(api, "submitInference").mockResolvedValue(runningJob);
        jest.spyOn(api, "fetchJob").mockResolvedValue(finishedJob);

        const wrapper = mount(UploadForm, {
            localVue,
            vuetify,
            propsData: { sceneIds: ["new-orleans"] },
        });
        const vm = wrapper.vm as any;
        vm.onBeforeSelected(new File(["b"], "before.tif"));
        vm.onAfterSelected(new File(["a"], "after.tif"));

        await vm.onSubmit();
        await wrapper.vm.$nextTick();

        expect(wrapper.find(".job-progress").exists()).toBe(true);
        expect(wrapper.text()).toContain("running");

        jest.advanceTimersByTime(2100);
        await Promise.resolve();
        await Promise.resolve();
        await wrapper.vm.$nextTick();

        expect(wrapper.text()).toContain("succeeded");
        expect(wrapper.text()).toContain("42");
        expect(wrapper.text()).toContain("126");
        expect(wrapper.text()).toContain("structures-affected.geojson");
        expect(wrapper.emitted("completed")).toBeTruthy();

        jest.spyOn(api, "submitInference").mockRejectedValue(new api.ApiRequestError("429 Too Many Requests"));
        await vm.onSubmit();
        await wrapper.vm.$nextTick();
        expect(wrapper.find(".upload-alert").text()).toContain("429 Too Many Requests");

        wrapper.destroy();
    });

    it("renders failed job error banner and empty state in JobTable", () => {
        const emptyWrapper = mount(JobTable, {
            localVue,
            vuetify,
            propsData: { jobs: [] },
        });
        expect(emptyWrapper.text()).toContain("no jobs yet");
        emptyWrapper.destroy();

        const jobs: IJob[] = [
            {
                job_id: "deadbeef-0000-4000-8000-000000000001",
                zone_id: "oman",
                status: "failed",
                created_at: "2026-11-25T07:15:00Z",
                started_at: "2026-11-25T07:15:01Z",
                finished_at: "2026-11-25T07:15:02Z",
                duration_seconds: 1.0,
                tiles: 0,
                affected_structures: 0,
                unaffected_structures: 0,
                severe_structures: 0,
                moderate_structures: 0,
                artifacts: [],
                error: "RuntimeError: missing GeoTIFF tags",
                warning: null,
            },
        ];

        const errWrapper = mount(JobTable, {
            localVue,
            vuetify,
            propsData: { jobs },
        });
        expect(errWrapper.text()).toContain("deadbeef");
        expect(errWrapper.text()).toContain("RuntimeError: missing GeoTIFF tags");
        errWrapper.destroy();
    });
});
