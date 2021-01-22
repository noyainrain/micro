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

describe("DatetimeInputElement", function() {
    let input;
    let dateInput;
    let timeInput;

    beforeEach(function() {
        const main = document.querySelector("main");
        main.innerHTML = "<micro-datetime-input></micro-datetime-input>";
        input = main.firstElementChild;
        dateInput = input.querySelector("input[type=date]");
        timeInput = input.querySelector("input[type=time]");
    });

    describe("on set value", function() {
        it("should fill inputs", function() {
            input.value = "2015-08-27T22:42:00.000Z";
            expect(dateInput.value).to.equal("2015-08-28");
            expect(timeInput.value).to.equal("00:42");
        });

        it("should fill inputs for date", function() {
            input.value = "2015-08-27";
            expect(dateInput.value).to.equal("2015-08-27");
            expect(timeInput.value).to.equal("");
        });
    });

    describe("on date input", function() {
        it("should update value", function() {
            dateInput.value = "2015-08-27";
            dateInput.dispatchEvent(new Event("input"));
            expect(input.value).to.equal("2015-08-27");
        });
    });

    describe("on time input", function() {
        it("should update value", function() {
            timeInput.value = "00:42";
            timeInput.dispatchEvent(new Event("input"));
            expect(input.value).to.be.empty;
        });

        it("should update value for set date", function() {
            input.value = "2015-08-28";
            timeInput.value = "00:42";
            timeInput.dispatchEvent(new Event("input"));
            expect(input.value).to.equal("2015-08-27T22:42:00.000Z");
        });
    });
});
