/*
 * micro
 * Copyright (C) 2021 micro contributors
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

"use strict";

self.micro = self.micro || {};
micro.core = {};

// Work around missing look behind by capturing whitespace
micro.core.URL_PATTERN = "(^|[\\s!-.:-@])(https?://.+?)(?=[!-.:-@]?(\\s|$))";

/**
 * Page.
 *
 * .. attribute:: ready
 *
 *    Promise that resolves once the page is ready.
 *
 *    Subclass API: :meth:`micro.util.PromiseWhen.when` may be used to signal when the page will be
 *    ready. By default, the page is considered all set after it has been attached to the DOM.
 */
micro.core.Page = class extends HTMLElement {
    createdCallback() {
        this.ready = new micro.util.PromiseWhen();
        this._caption = null;
    }

    attachedCallback() {
        setTimeout(
            () => {
                try {
                    this.ready.when(Promise.resolve());
                } catch (e) {
                    // The subclass may call when
                    if (e.message === "already-called-when") {
                        return;
                    }
                    throw e;
                }
            },
            0
        );
    }

    /**
     * Page title. May be ``null``.
     */
    get caption() {
        return this._caption;
    }

    set caption(value) {
        this._caption = value;
        if (this === ui.page) {
            // eslint-disable-next-line no-underscore-dangle
            ui._updateTitle();
        }
    }
};

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

/**
 * Decorator for a user request.
 *
 * If the request cannot be fulfilled because of a common web API error (:ref:`NotFoundError`,
 * :ref:`PermissionError`, :ref:`RateLimitError`, :class:`micro.NetworkError`), the user is notified
 * and :attr:`micro.core.request.ABORTED` is returned. A user request function is async.
 *
 * The decorated function may be async.
 */
micro.core.request = function(f) {
    return async (...args) => {
        try {
            return await f(...args);
        } catch (e) {
            ui.handleCallError(e);
            return micro.core.request.ABORTED;
        }
    };
};

/** Returned if a user request was aborted. */
micro.core.request.ABORTED = Symbol("aborted");

/**
 * Decorator for a user action.
 *
 * If the action cannot be performed because the current user is anonymous, they are notified and
 * :data:`micro.core.request.ABORTED` is returned. A user action function is a
 * :func:`micro.core.request`.
 */
micro.core.action = function(f) {
    return micro.core.request((...args) => {
        if (ui.embedded) {
            const notification = document.importNode(
                document.querySelector("#micro-embedded-notification").content, true
            );
            micro.bind.bind(notification, {settings: ui.settings});
            ui.notify(notification);
            return micro.core.request.ABORTED;
        }
        if (!ui.features.storage) {
            ui.notify(
                `Oops, cookies are disabled! Please enable cookies for ${ui.settings.title} and try again.`
            );
            return micro.core.request.ABORTED;
        }
        return f(...args);
    });
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
