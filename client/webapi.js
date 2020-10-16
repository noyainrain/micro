/* TODO */

/** TODO */

"use strict";

self.micro = self.micro || {};
micro.webapi = {};

/**
 * Thrown for HTTP JSON REST API errors.
 *
 * .. attribute:: error
 *
 *    The error object.
 *
 * .. attribute:: status
 *
 *    The associated HTTP status code.
 */
micro.webapi.WebAPIError = class APIError extends Error {
    constructor(message, error, status) {
        // TODO is it called message?
        super(message);
        this.error = error;
        this.status = status;
    }
};

/** Thrown if network communication failed. */
micro.webapi.NetworkError = class NetworkError extends Error {};

micro.APIError = micro.webapi.WebAPIError;
micro.NetworkError = micro.webapi.NetworkError;

/** TODO. */
micro.webapi.WebAPI = class {
    constructor({url = location.origin, query = {}} = {}) {
        // on client absolute URL is not needed, relative would be relative against location
        this.url = url;
        this.query = query;
    }

    async call(method, url, {args = null, query = {}} = {}) {
        url = new URL(url, this.url);
        for (let [key, value] of Object.entries(Object.assign({}, this.query, query))) {
            url.searchParams.set(key, value);
        }
        const options = {method, credentials: "same-origin"};
        if (args) {
            // options.headers["Content-Type"] = "application/json";
            options.body = JSON.stringify(args);
        }

        let response;
        let result;
        try {
            response = await fetch(url, options);
            result = await response.json();
        } catch (e) {
            if (e instanceof TypeError) {
                throw new micro.webapi.NetworkError(`${e.message} for ${method} ${url}`);
            } else if (e instanceof SyntaxError) {
                throw new micro.webapi.NetworkError(`Bad response format for ${method} ${url}`);
            }
            throw e;
        }
        if (!response.ok) {
            throw new micro.webapi.WebAPIError(
                `Error ${response.status} for ${method} ${url}`, result, response.status
            );
        }
        return result;
    }
};
