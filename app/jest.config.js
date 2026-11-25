module.exports = {
    preset: "@vue/cli-plugin-unit-jest/presets/typescript-and-babel",
    setupFiles: ["<rootDir>/tests/unit/setup.ts"],
    testMatch: ["**/tests/unit/**/*.spec.(ts|tsx|js|jsx)"],
    transformIgnorePatterns: ["/node_modules/(?!vuetify)/"],
    moduleNameMapper: {
        "^@/(.*)$": "<rootDir>/src/$1",
    },
};
