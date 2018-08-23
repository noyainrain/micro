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

/**
 * Hello UI.
 */

"use strict";

window.hello = {};

/**
 * Hello UI.
 */
hello.UI = class extends micro.UI {
    init() {
        function makeAboutPage() {
            return document.importNode(ui.querySelector(".hello-about-page-template").content, true)
                .querySelector("micro-about-page");
        }

        this.pages = this.pages.concat([
            {url: "^/$", page: "hello-start-page"},
            {url: "^/about$", page: makeAboutPage}
        ]);
    }
};

/**
 * Start page.
 */
hello.StartPage = class extends micro.Page {
    createdCallback() {
        super.createdCallback();
        this.appendChild(
            document.importNode(ui.querySelector(".hello-start-page-template").content, true));

        this._data = new micro.bind.Watchable({
            settings: ui.settings,
            greetings: null,

            createGreeting: async() => {
                try {
                    let form = this.querySelector("form");
                    let greeting = await ui.call("POST", "/api/greetings",
                                                 {text: form.elements.text.value});
                    this._data.greetings.unshift(greeting);
                    form.reset();
                } catch (e) {
                    ui.handleCallError(e);
                }
            },

            makeGreetingHash(ctx, greeting) {
                return `greetings-${greeting.id.split(":")[1]}`;
            }
        });
        micro.bind.bind(this.children, this._data);
    }

    attachedCallback() {
        super.attachedCallback();
        this.ready.when((async() => {
            try {
                let greetings = await ui.call("GET", "/api/greetings");
                this._data.greetings = new micro.bind.Watchable(greetings);
            } catch (e) {
                ui.handleCallError(e);
            }
        })().catch(micro.util.catch));
    }
};

document.registerElement("hello-ui", {prototype: hello.UI.prototype, extends: "body"});
document.registerElement("hello-start-page", hello.StartPage);
