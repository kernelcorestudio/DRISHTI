/*
 * DISASTER RESPONSE APP
 * Copyright (c) 2021 SilentByte <https://silentbyte.com/>
 */

import Vue from "vue";
import VueRouter, { RouteConfig } from "vue-router";

import AnalyticsView from "@/ui/views/AnalyticsView.vue";
import DashboardView from "@/ui/views/DashboardView.vue";
import InferenceView from "@/ui/views/InferenceView.vue";
import MapView from "@/ui/views/MapView.vue";
import ModelsView from "@/ui/views/ModelsView.vue";
import ReportView from "@/ui/views/ReportView.vue";
import SpectralAnalysisView from "@/ui/views/SpectralAnalysisView.vue";
import SuperResolutionView from "@/ui/views/SuperResolutionView.vue";
import SystemView from "@/ui/views/SystemView.vue";
import ZonesView from "@/ui/views/ZonesView.vue";

Vue.use(VueRouter);

// One route per feature; the shell in App.vue renders the sidebar from this same list.
const routes: Array<RouteConfig> = [
    {
        path: "/",
        name: "Dashboard",
        component: DashboardView,
        meta: { title: "Dashboard", subtitle: "Live pipeline state, queue and damage totals" },
    },
    {
        path: "/map/:options(@[\\-0-9\\.\\,]+z)?",
        name: "Map",
        component: MapView,
        meta: { title: "Map", subtitle: "Before/after imagery, heatmap and affected structures" },
    },
    {
        path: "/report",
        name: "Report",
        component: ReportView,
        meta: { title: "Report", subtitle: "Damage breakdown per scene, with a live map view scope" },
    },
    {
        path: "/analytics",
        name: "Analytics",
        component: AnalyticsView,
        meta: { title: "Analytics", subtitle: "Damage distribution, model accuracy and throughput" },
    },
    {
        path: "/zones",
        name: "Zones",
        component: ZonesView,
        meta: { title: "Zones", subtitle: "Indexed scenes, layer sizes and GeoJSON feature counts" },
    },
    {
        path: "/inference",
        name: "Inference",
        component: InferenceView,
        meta: { title: "Inference", subtitle: "Upload a GeoTIFF pair and follow the job to completion" },
    },
    {
        path: "/super-resolution",
        name: "SuperResolution",
        component: SuperResolutionView,
        meta: { title: "Super-Resolution", subtitle: "Sentinel-2 10m to 2.5m enhancement with hallucination-aware trust" },
    },
    {
        path: "/spectral",
        name: "SpectralAnalysis",
        component: SpectralAnalysisView,
        meta: { title: "Spectral Indices", subtitle: "Multi-spectral NDVI, NDWI, NDBI, and NBR hazard assessment" },
    },
    {
        path: "/models",
        name: "Models",
        component: ModelsView,
        meta: { title: "Models", subtitle: "Stage-1 footprints, Stage-2 damage and local evaluation" },
    },
    {
        path: "/system",
        name: "System",
        component: SystemView,
        meta: { title: "System", subtitle: "Services, data directories, models and tile inventory" },
    },
    {
        path: "*",
        redirect: "/",
    },
];

const router = new VueRouter({
    mode: "history",
    base: process.env.BASE_URL,
    routes,
});

export default router;
