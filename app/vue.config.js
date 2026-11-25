module.exports = {
    transpileDependencies: [
        "vuetify",
    ],

    devServer: {
        // The inference API ships without CORS middleware, so the browser reaches it through
        // this proxy instead of calling http://127.0.0.1:8099 from another origin.
        proxy: {
            "/api": {
                target: "http://127.0.0.1:8099",
                pathRewrite: {
                    "^/api": "",
                },
                changeOrigin: true,
            },
        },
    },
};
