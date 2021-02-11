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

/** Core parts of micro. */

/* eslint-disable no-underscore-dangle -- private static */

"use strict";

self.micro = self.micro || {};
micro.core = {};

// Work around missing look behind by capturing whitespace
micro.core.URL_PATTERN = "(^|[\\s!-.:-@])(https?://.+?)(?=[!-.:-@]?(\\s|$))";

/**
 * Action that is run when an element is activated.
 *
 * While the action is running, the element is suspended, i.e. it shows a progress indicator and is
 * not clickable.
 *
 * .. attribute:: element
 *
 *    Related :class:`Element`.
 *
 * .. attribute:: f
 *
 *    Function which performs the action. May be async.
 *
 * .. attribute:: args
 *
 *    Arguments passed to :attr:`f`, if any.
 *
 * .. attribute:: running
 *
 *    Indicates if the action is running.
 *
 * .. describe: .micro-suspended
 *
 *    Indicates if the element is suspended.
 */
micro.core.Action = class {
    constructor(element, f, ...args) {
        const action = micro.core.Action._actions.get(element);
        if (action) {
            action.f = f;
            action.args = args;
            // eslint-disable-next-line no-constructor-return -- idempotent
            return action;
        }
        micro.core.Action._actions.set(element, this);

        this.element = element;
        this.f = f;
        this.args = args;
        this.running = false;

        this._onClick = event => {
            if (this.element.type === "submit" && this.element.form) {
                if (this.running || this.element.form.checkValidity()) {
                    // Prevent default form submission
                    event.preventDefault();
                } else {
                    // Do not trigger action and let form validation kick in
                    return;
                }
            }

            if (!this.running) {
                this.run().catch(micro.util.catch);
            }
        };
        this.element.addEventListener("click", this._onClick);
    }

    /** Run the action. */
    async run() {
        if (this.running) {
            throw new Error("Running action");
        }

        this.running = true;
        this.element.classList.add("micro-suspended");
        const i = this.element.querySelector("i");
        let progressI = null;
        if (i) {
            progressI = document.createElement("i");
            progressI.className = "fa fa-spinner fa-spin";
            i.insertAdjacentElement("afterend", progressI);
        }
        try {
            return await this.f(...this.args);
        } finally {
            this.running = false;
            this.element.classList.remove("micro-suspended");
            if (i) {
                progressI.remove();
            }
        }
    }
};
micro.core.Action._actions = new WeakMap();

/**
 * Modal dialog to query additional information for an action.
 *
 * .. attribute:: result
 *
 *    Promise that resolves with the result of the concluded dialog. ``null`` if the dialog is
 *    closed.
 */
micro.core.Dialog = class extends HTMLElement {
    createdCallback() {
        this.result = new micro.util.PromiseWhen();
        this.classList.add("micro-dialog");
    }

    detachedCallback() {
        try {
            this.result.when(null);
        } catch (e) {
            if (e.message.includes("when")) {
                // Ignore if result is already resolved on close
            } else {
                throw e;
            }
        }
    }
};

Object.assign(micro.bind.transforms, {
    /**
     * Render *markup text* into a :class:`DocumentFragment`.
     *
     * HTTP(S) URLs are automatically converted to links.
     */
    markup(ctx, text) {
        if (!text) {
            return document.createDocumentFragment();
        }

        const patterns = {
            // Do not capture trailing whitespace because of link pattern
            item: "(^[^\\S\n]*[*+-](?=\\s|$))",
            strong: "\\*\\*(.+?)\\*\\*",
            em: "\\*(.+?)\\*",
            link: micro.core.URL_PATTERN
        };
        const pattern = new RegExp(
            `${patterns.item}|${patterns.strong}|${patterns.em}|${patterns.link}`, "ugm"
        );

        const fragment = document.createDocumentFragment();
        let match;
        do {
            const skipStart = pattern.lastIndex;
            match = pattern.exec(text);
            const skipStop = match ? match.index : text.length;
            if (skipStop > skipStart) {
                fragment.appendChild(document.createTextNode(text.slice(skipStart, skipStop)));
            }
            if (match) {
                const [, item, strong, em, linkPrefix, linkURL] = match;
                if (item) {
                    fragment.appendChild(document.createTextNode("\u00a0•"));
                } else if (strong) {
                    const elem = document.createElement("strong");
                    elem.textContent = strong;
                    fragment.appendChild(elem);
                } else if (em) {
                    const elem = document.createElement("em");
                    elem.textContent = em;
                    fragment.appendChild(elem);
                } else if (linkURL) {
                    if (linkPrefix) {
                        fragment.appendChild(document.createTextNode(linkPrefix));
                    }
                    const a = document.createElement("a");
                    a.classList.add("link");
                    a.href = linkURL;
                    a.target = "_blank";
                    a.textContent = linkURL;
                    fragment.appendChild(a);
                } else {
                    // Unreachable
                    throw new Error();
                }
            }
        } while (match);
        return fragment;
    }
});
