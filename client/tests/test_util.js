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
/* eslint-disable prefer-arrow-callback */

"use strict";

window.expect = window.expect || chai.expect;

describe("dispatchEvent()", function() {
    it("should dispatch event", function() {
        let calls = [];
        let span = document.createElement("span");
        span.addEventListener("poke", event => calls.push(["listener", event.type]));
        span.onpoke = event => calls.push(["on", event.type]);
        micro.util.dispatchEvent(span, new CustomEvent("poke"));
        expect(calls).to.deep.equal([["listener", "poke"], ["on", "poke"]]);
    });
});
