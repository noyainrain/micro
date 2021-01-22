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

/** Form inputs. */

"use strict";

self.micro = self.micro || {};
micro.components = micro.components || {};
micro.components.form = {};

/**
 * Input for entering a date and optional time.
 *
 * The element behaves like a ``datetime-local`` :class:`HTMLInputElement`, while the time component
 * is optional and :attr:`value` is expressed in UTC.
 */
micro.components.form.DatetimeInputElement = class extends HTMLElement {
    constructor() {
        super();
        this.appendChild(
            document.importNode(
                document.querySelector("#micro-datetime-input-template").content, true
            )
        );
        this.classList.add("micro-input");

        this._dateInput = this.querySelector("input[type=date]");
        this._timeInput = this.querySelector("input[type=time]");
        // No input event is dispatched if an empty field receives bad input
        this._dateInput.addEventListener("input", this._update.bind(this));
        this._dateInput.addEventListener("keyup", this._update.bind(this));
        this._timeInput.addEventListener("input", this._update.bind(this));
        this._timeInput.addEventListener("keyup", this._update.bind(this));

        // Text fallback
        this._dateInput.properValue = "";
        this._dateInput.badInput = false;
        this._timeInput.properValue = "";
        this._timeInput.badInput = false;

        this._update();
    }

    /** Current value as *datetime* or *date*. */
    get value() {
        if (this._dateInput.properValue) {
            if (this._timeInput.properValue) {
                // Convert to UTC
                return new Date(`${this._dateInput.properValue}T${this._timeInput.properValue}`)
                    .toISOString();
            }
            return this._dateInput.properValue;
        }
        return "";
    }

    set value(value) {
        const date = new Date(value);
        if (value && isFinite(date)) {
            if (value.length === 10) {
                this._dateInput.value = value;
                this._timeInput.value = "";
            } else {
                // Convert to local time
                const year = date.getFullYear().toString().padStart(4, "0");
                const month = (date.getMonth() + 1).toString().padStart(2, "0");
                const day = date.getDate().toString().padStart(2, "0");
                const hour = date.getHours().toString().padStart(2, "0");
                const minute = date.getMinutes().toString().padStart(2, "0");
                this._dateInput.value = `${year}-${month}-${day}`;
                this._timeInput.value = `${hour}:${minute}`;
            }
        } else {
            this._dateInput.value = "";
            this._timeInput.value = "";
        }
        this._update();
    }

    _update() {
        // Text fallback
        if (
            this._dateInput.validity.badInput || this._dateInput.value &&
            !(this._dateInput.value.length === 10 && isFinite(new Date(this._dateInput.value)))
        ) {
            this._dateInput.properValue = "";
            this._dateInput.badInput = true;
            this._dateInput.setCustomValidity("Please enter a valid date.");
        } else {
            this._dateInput.properValue = this._dateInput.value;
            this._dateInput.badInput = false;
            this._dateInput.setCustomValidity("");
        }
        if (
            this._timeInput.validity.badInput || this._timeInput.value &&
            !(
                this._timeInput.value.length === 5 &&
                isFinite(new Date(`1970-01-01T${this._timeInput.value}Z`))
            )
        ) {
            this._timeInput.properValue = "";
            this._timeInput.badInput = true;
            this._timeInput.setCustomValidity("Please enter a valid time.");
        } else {
            this._timeInput.properValue = this._timeInput.value;
            this._timeInput.badInput = false;
            this._timeInput.setCustomValidity("");
        }

        if (
            !this._dateInput.badInput && !this._timeInput.badInput &&
            !this._dateInput.properValue && this._timeInput.properValue
        ) {
            this._dateInput.setCustomValidity("Please complete the date.");
        } else {
            // eslint-disable-next-line no-lonely-if -- text fallback
            if (!this._dateInput.badInput) {
                this._dateInput.setCustomValidity("");
            }
        }
        this.classList.toggle(
            "micro-datetime-input-empty-date",
            !this._dateInput.properValue && !this._dateInput.badInput
        );
        this.classList.toggle(
            "micro-datetime-input-empty-time",
            !this._timeInput.properValue && !this._timeInput.badInput
        );
    }

};
customElements.define("micro-datetime-input", micro.components.form.DatetimeInputElement);
