/* eslint-env node */

"use strict";

module.exports = function(config) {
    const tag = process.env.SUBJECT ? ` [${process.env.SUBJECT}]` : "";
    const timeZone = process.env.TZ.split("/")[1];

    config.set({
        frameworks: ["mocha"],
        files: [
            "node_modules/webcomponents.js/webcomponents-lite.min.js",
            "node_modules/event-source-polyfill/src/eventsource.min.js",
            "node_modules/chai/chai.js",
            "bind.js",
            "keyboard.js",
            "core.js",
            "util.js",
            "components/contentinput.js",
            "components/form.js",
            "index.js",
            "components/contextual.js",
            "components/stats.js",
            "!(node_modules)/**/test*.js",
            {pattern: "templates.html", type: "dom"},
            {pattern: "components/*.html", type: "dom"}
        ],
        sauceLabs: {
            testName: `[micro]${tag} Unit tests`
        },
        customLaunchers: {
            "sauce-chrome": {
                base: "SauceLabs",
                browserName: "chrome",
                platform: "Windows 10",
                timeZone
            },
            "sauce-edge": {
                base: "SauceLabs",
                browserName: "MicrosoftEdge",
                platform: "Windows 10",
                timeZone
            },
            "sauce-firefox": {
                base: "SauceLabs",
                browserName: "firefox",
                platform: "Windows 10",
                timeZone
            },
            "sauce-safari": {
                base: "SauceLabs",
                browserName: "safari",
                platform: "macOS 11.00",
                timeZone
            }
        },
        browsers: ["FirefoxHeadless"]
    });
};
