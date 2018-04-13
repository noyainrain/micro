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

/* eslint-env serviceworker */

/** Service worker. */

"use strict";

self.micro = self.micro || {};
micro.service = {};

micro.service.STANDALONE = location.pathname.endsWith("@noyainrain/micro/service.js");
if (micro.service.STANDALONE) {
    importScripts(new URL("util.js", location.href).href);
}

micro.util.watchErrors();

/**
 * Main service worker of a micro app.
 *
 * .. attribute:: settings
 *
 *    Subclass API: App settings.
 *
 * .. attribute:: notificationRenderers
 *
 *    Subclass API: Table of notification render functions by event type.
 *
 *    A render function has the form *render(event)* and produces an :class:`Object`
 *    *{title, body, url}* from the given :ref:`Event` *event*. May return a :class:`Promise`.
 *
 *    The key defines the event *type* (e.g. `editable-edit`) a renderer can handle, optionally
 *    augmented with event's *object* type (e.g. `editable-edit+Settings`). When rendering a
 *    notification, the most specific matching render function is used.
 */
micro.service.Service = class {
    constructor() {
        this.settings = null;
        this.notificationRenderers = {
            "user-enable-device-notifications": () => ({
                title: this.settings.title,
                body: "Notifications enabled",
                url: "/"
            })
        };

        addEventListener("install", () => skipWaiting());
        addEventListener("activate", () => clients.claim());

        addEventListener("push", event => {
            event.waitUntil((async() => {
                if (!this.settings) {
                    this.settings = await micro.call("GET", "/api/settings");
                }

                let ev = event.data.json();
                let render;
                if (ev.object) {
                    render = this.notificationRenderers[`${ev.type}+${ev.object.__type__}`];
                }
                if (!render) {
                    render = this.notificationRenderers[ev.type];
                }
                if (!render) {
                    throw new Error("notification-renderers");
                }

                let notification = render(ev);
                if (notification instanceof Promise) {
                    notification = await notification;
                }
                registration.showNotification(notification.title, {
                    body: notification.body || undefined,
                    icon: this.settings.icon_large || undefined,
                    data: {url: notification.url}
                });
            })());
        });

        addEventListener("notificationclick", event => {
            event.waitUntil((async() => {
                let windows = await clients.matchAll({type: "window"});
                for (let client of windows) {
                    if (new URL(client.url).pathname === event.notification.data.url) {
                        client.focus();
                        return;
                    }
                }
                clients.openWindow(event.notification.data.url);
            })());
        });
    }

    /**
     * Subclass API: Update :attr:`notificationRenderers` with the given *renderers*.
     */
    setNotificationRenderers(renderers) {
        Object.assign(this.notificationRenderers, renderers);
    }
};

if (micro.service.STANDALONE) {
    self.service = new micro.service.Service();
}
