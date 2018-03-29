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
                    let input = this.querySelector("micro-text-entity-input");
                    let greeting = await micro.call("POST", "/api/greetings",
                        {text: input.value.text || null, entity: input.value.entity});
                    input.reset();
                    this._data.greetings.unshift(greeting);
                } catch(e) {
                    console.log(e);
                }
            }
        });
        micro.bind.bind(this.children, this._data);
    }

    async attachedCallback() {
        let greetings = await micro.call("GET", "/api/greetings");
        this._data.greetings = new micro.bind.Watchable(greetings);
    }
};

document.registerElement("hello-ui", {prototype: hello.UI.prototype, extends: "body"});
document.registerElement("hello-start-page", hello.StartPage);
