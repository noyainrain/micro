/*
 * micro
 * Copyright (C) 2018 micro contributors
 *
 * This program is free software: you can redistribute it and/or modify it under the terms of the
 * GNU Lesser General Public License as published by the Free Software Foundation, either version 3
 * of the License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without
 * even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License along with this program.
 * If not, see <http://www.gnu.org/licenses/>.
 */

/* eslint-env mocha */
/* global chai, expect */
/* eslint-disable no-unused-expressions, prefer-arrow-callback */

"use strict";

window.expect = window.expect || chai.expect;

beforeEach(function() {
    document.body.appendChild(document.createElement("main"));
});

afterEach(function() {
    document.querySelector("main").remove();
});

describe("OptionsElement", function() {
    async function setupDOM({options = ["Long", "Happy", "Grumpy"], templateHTML = ""} = {}) {
        let main = document.querySelector("main");
        main.innerHTML = `
            <input />
            <micro-options>
                ${templateHTML}
            </micro-options>
        `;
        // Custom elements are upgraded in the next iteration
        await new Promise(resolve => setTimeout(resolve, 0));
        let elem = main.lastElementChild;
        elem.options = options;
        return [elem, main.firstElementChild];
    }

    function getPresentedOptions(elem) {
        return Array.from(elem.querySelector("ul").children, node => node.textContent.trim());
    }

    describe("activate()", function() {
        it("should present options", async function() {
            let [elem] = await setupDOM();
            elem.limit = 2;
            elem.activate();
            await new Promise(resolve => setTimeout(resolve, 0));
            expect(getPresentedOptions(elem)).to.deep.equal(["Long", "Happy"]);
        });

        it("should present options for dynamic options", async function() {
            let [elem] = await setupDOM({options: () => ["Long", "Happy"]});
            elem.activate();
            await new Promise(resolve => setTimeout(resolve, 0));
            expect(getPresentedOptions(elem)).to.deep.equal(["Long", "Happy"]);
        });

        it("should present options for template", async function() {
            let [elem] = await setupDOM({
                options: [{name: "Long"}, {name: "Happy"}],
                templateHTML: `
                    <template>
                        <p>
                            <span data-content="option.name"></span> Cat
                        </p>
                    </template>
                `
            });
            elem.toText = option => option.name;
            elem.activate();
            await new Promise(resolve => setTimeout(resolve, 0));
            expect(getPresentedOptions(elem)).to.deep.equal(["Long Cat", "Happy Cat"]);
        });
    });

    describe("on input", function() {
        it("should present matching options", async function() {
            let [elem, input] = await setupDOM();
            input.value = "pY";
            input.dispatchEvent(new Event("input"));
            await new Promise(resolve => setTimeout(resolve, 0));
            expect(getPresentedOptions(elem)).to.deep.equal(["Happy", "Grumpy"]);
        });
    });

    describe("on option click", function() {
        it("should set input value", async function() {
            let [elem, input] = await setupDOM();
            elem.activate();
            await new Promise(resolve => setTimeout(resolve, 0));
            elem.querySelector("li").dispatchEvent(new MouseEvent("click"));
            expect(input.value).to.equal("Long");
        });
    });
});

describe("LocationInputElement", function() {
    async function setupDOM() {
        let main = document.querySelector("main");
        main.innerHTML = "<micro-location-input></micro-location-input>";
        await new Promise(resolve => setTimeout(resolve, 0));
        return main.firstElementChild;
    }

    describe("on set value", function() {
        it("should set native input value", async function() {
            let input = await setupDOM();
            input.value = {name: "Berlin", coords: [52.504043, 13.393236]};
            expect(input.nativeInput.value).to.equal("Berlin");
        });
    });

    describe("on input", function() {
        it("should set value", async function() {
            let input = await setupDOM();
            input.nativeInput.value = "Berlin";
            input.nativeInput.dispatchEvent(new Event("input"));
            expect(input.value).to.deep.equal({name: "Berlin", coords: null});
        });
    });
});
