/*
 * micro
 * Copyright (C) 2020 micro contributors
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

self.expect = self.expect || chai.expect;

describe("Action", function() {
    let button;

    beforeEach(function() {
        const main = document.querySelector("main");
        main.innerHTML = '<button><i class="fa fa-cat"></i> Meow</button>';
        button = main.firstElementChild;
        button.action = new micro.core.Action(button, (...args) => args, "a", "b");
    });

    describe("run()", function() {
        it("should run action", async function() {
            const p = button.action.run();
            expect(button.action.running).to.be.true;
            expect(button.classList.contains("micro-suspended")).to.be.true;
            const result = await p;
            expect(result).to.deep.equal(["a", "b"]);
            expect(button.action.running).to.be.false;
            expect(button.classList.contains("micro-suspended")).to.be.false;
        });
    });
});
