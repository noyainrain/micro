/*
 * bind.js
 * Released into the public domain
 * https://github.com/noyainrain/micro/blob/master/client/bind.js
 */

/**
 * Simple data binding.
 */

"use strict";

window.micro = window.micro || {};
micro.bind = {};

/**
 * Wrapper around an object which can be watched for modification.
 *
 * .. attribute:: target
 *
 *    Wrapped :class:`Object`.
 *
 * .. method:: watch(prop, onUpdate)
 *
 *    Watch the property *prop* and call *onUpdate* when it is updated.
 *
 *    *onUpdate* is a function of the form ``onUpdate(prop, value)``, where *prop* is the property
 *    being set to *value*.
 *
 *    In addition to watching a single property, *prop* may also be one of the following special
 *    values:
 *
 *    * ``Symbol.for("*")``: Watch for updates of any property
 *    * ``Symbol.for("+")``: If *target* is an :class:`Array`, get notified when an item is inserted
 *    * ``Symbol.for("-")``: If *target* is an :class:`Array`, get notified when an item is removed
 */
micro.bind.Watchable = function(target = {}) {
    let watchers = {};

    function notify(key, prop, value) {
        (watchers[key] || []).forEach(onUpdate => onUpdate(prop, value));
    }

    let ext = {
        target,

        watch(prop, onUpdate) {
            if (!(prop in watchers)) {
                watchers[prop] = [];
            }
            watchers[prop].push(onUpdate);
        },

        splice(start, deleteCount, ...items) {
            let removed = target.splice(start, deleteCount, ...items);
            for (let [i, item] of Array.from(removed.entries()).reverse()) {
                notify(Symbol.for("-"), (start + i).toString(), item);
            }
            for (let [i, item] of items.entries()) {
                notify(Symbol.for("+"), (start + i).toString(), item);
            }
            return removed;
        },

        push(...items) {
            return ext.splice(target.length, 0, ...items);
        }
    };

    return new Proxy(target, {
        get(t, prop) {
            return ext[prop] || target[prop];
        },

        set(t, prop, value) {
            target[prop] = value;
            notify(prop, prop, value);
            notify(Symbol.for("*"), prop, value);
            return true;
        }
    });
};

/**
 * Create a new :class:`Watchable` live array from *arr* with all items that pass the given test.
 *
 * *arr* is a :class:`Watchable` array. *callback* and *thisArg* are equivalent to the arguments of
 * :func:`Array.filter`. Because the filtered array is updated live, it may be called out of order
 * and multiple times for the same index.
 */
micro.bind.filter = function(arr, callback, thisArg = null) {
    let cache = arr.map(callback, thisArg);
    let filtered = new micro.bind.Watchable(arr.filter((item, i) => cache[i]));

    function mapIndex(i) {
        // The index of the the filtered array corresponds to the count of passing items up to the
        // index of the source array
        return cache.slice(0, i).reduce((count, result) => result ? count + 1 : count, 0);
    }

    function update(i, value) {
        filtered[mapIndex(i)] = value;
    }

    function add(i, value) {
        filtered.splice(mapIndex(i), 0, value);
    }

    function remove(i) {
        filtered.splice(mapIndex(i), 1);
    }

    arr.watch(Symbol.for("*"), (prop, value) => {
        let i = parseInt(prop);
        let [prior] = cache.splice(i, 1, callback.call(thisArg, value, i, arr));
        if (prior && cache[i]) {
            update(i, value);
        } else if (!prior && cache[i]) {
            add(i, value);
        } else if (prior && !cache[i]) {
            remove(i);
        }
    });

    arr.watch(Symbol.for("+"), (prop, value) => {
        let i = parseInt(prop);
        cache.splice(i, 0, callback.call(thisArg, value, i, arr));
        if (cache[i]) {
            add(i, value);
        }
    });

    arr.watch(Symbol.for("-"), prop => {
        let i = parseInt(prop);
        let [prior] = cache.splice(i, 1);
        if (prior) {
            remove(i);
        }
    });

    return filtered;
};

/**
 * Project the :class:`Watchable` array :class:*arr* into a live DOM fragment.
 *
 * Optionally, a live transform can be applied on *arr* with the function
 * ``transform(arr, ...args)``. *args* are passed through.
 */
micro.bind.list = function(elem, arr, itemName, transform, ...args) {
    function create(item) {
        let child = document.importNode(elem.__template__.content, true).querySelector("*");
        child[itemName] = item;
        return child;
    }

    if (!elem.__template__) {
        elem.__template__ = elem.firstElementChild;
        elem.__template__.remove();
    }

    let fragment = document.createDocumentFragment();

    if (arr) {
        if (transform) {
            arr = transform(arr, ...args);
        }

        arr.watch(Symbol.for("*"), (prop, value) => {
            elem.children[prop][itemName] = value;
        });
        arr.watch(Symbol.for("+"),
                  (prop, value) => elem.insertBefore(create(value), elem.children[prop] || null));
        arr.watch(Symbol.for("-"), prop => elem.children[prop].remove());

        arr.forEach(item => fragment.appendChild(create(item)));
    }

    return fragment;
};

/**
 * Join all items of the array *arr* into a DOM fragment.
 *
 * *separator* is inserted between adjacent items. *transform* and *args* are equivalent to the
 * arguments of :func:`micro.bind.list`.
 */
micro.bind.join = function(elem, arr, itemName, separator = ", ", transform, ...args) {
    if (!elem.__template__) {
        elem.__template__ = elem.firstElementChild;
        elem.__template__.remove();
    }

    let fragment = document.createDocumentFragment();

    if (arr) {
        if (transform) {
            arr = transform(arr, ...args);
        }

        for (let [i, item] of arr.entries()) {
            if (i > 0) {
                fragment.appendChild(document.createTextNode(separator));
            }
            let child = document.importNode(elem.__template__.content, true).querySelector("*");
            child[itemName] = item;
            fragment.appendChild(child);
        }
    }

    return fragment;
};
