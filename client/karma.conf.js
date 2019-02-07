/* eslint-env node */

"use strict";

module.exports = function(config) {
    let tag = process.env.SUBJECT ? ` [${process.env.SUBJECT}]` : "";
    config.set({
        //logLevel: config.LOG_DEBUG,
        frameworks: ["mocha"],
        files: [
            "node_modules/whatwg-fetch/fetch.js",
            "node_modules/webcomponents.js/webcomponents-lite.min.js",
            "node_modules/chai/chai.js",
            "bind.js",
            "keyboard.js",
            "util.js",
            "index.js",
            "!(node_modules)/**/test*.js",
            "templates.html"
        ],
        sauceLabs: {
            testName: `[micro]${tag} Unit tests`
        },
        customLaunchers: {
            "sauce-chrome": {
                base: "SauceLabs",
                browserName: "chrome",
                platform: "Windows 10"
            },
            "sauce-edge": {
                base: "SauceLabs",
                browserName: "MicrosoftEdge",
                platform: "Windows 10"
            },
            "sauce-firefox": {
                base: "SauceLabs",
                browserName: "firefox",
                platform: "Windows 10"
            },
            "sauce-safari": {
                base: "SauceLabs",
                browserName: "safari",
                platform: "macOS 10.13"
            }
        },
        browsers: ["FirefoxHeadless"]
    });
};
