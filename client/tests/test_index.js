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

before(async function() {
    let response = await fetch("/base/templates.html");
    let html = await response.text();
    let templatesNode = document.createElement("div");
    templatesNode.innerHTML = html;
    document.body.appendChild(document.createElement("main"));
    document.body.appendChild(templatesNode);
});

describe("OptionsElement", function() {
    async function setupDOM({options = ["Long", "Happy", "Grumpy"], template = false} = {}) {
        let main = document.querySelector("main");
        let templateHTML = `
            <template>
                <p><span data-content="option.name"></span> Cat</p>
            </template>
        `;
        main.innerHTML = `
            <input />
            <micro-options>
                ${template ? templateHTML : ""}
            </micro-options>
        `;
        // Custom elements are upgraded in the next iteration
        await new Promise(resolve => setTimeout(resolve, 0));
        let elem = main.querySelector("micro-options");
        elem.options = options;
        return [elem, main.querySelector("input")];
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

        it("should present options for function", async function() {
            let [elem] = await setupDOM({options: () => ["Long", "Happy"]});
            elem.activate();
            await new Promise(resolve => setTimeout(resolve, 0));
            expect(getPresentedOptions(elem)).to.deep.equal(["Long", "Happy"]);
        });

        it("should present options for template", async function() {
            let [elem] = await setupDOM(
                {options: [{name: "Long"}, {name: "Happy"}], template: true}
            );
            elem.toText = option => option.name;
            elem.activate();
            await new Promise(resolve => setTimeout(resolve, 0));
            expect(getPresentedOptions(elem)).to.deep.equal(["Long Cat", "Happy Cat"]);
        });
    });

    describe("on input", function() {
        it("should present matching options", async function() {
            let [elem, input] = await setupDOM();
            input.value = "py";
            input.dispatchEvent(new InputEvent("input"));
            await new Promise(resolve => setTimeout(resolve, 0));
            expect(getPresentedOptions(elem)).to.deep.equal(["Happy", "Grumpy"]);
        });
    });

    describe("on select", function() {
        it("should set input value", async function() {
            let [elem, input] = await setupDOM();
            elem.activate();
            await new Promise(resolve => setTimeout(resolve, 0));
            elem.querySelector("li").dispatchEvent(new MouseEvent("click"));
            expect(input.value).to.equal("Long");
        });
    });
});
