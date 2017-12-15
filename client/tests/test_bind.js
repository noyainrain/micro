/*
 * bind.js
 * Released into the public domain
 * https://github.com/noyainrain/micro/blob/master/client/bind.js
 */

/* eslint-env mocha */
/* global chai */
/* eslint-disable prefer-arrow-callback */

"use strict";

let {expect} = chai;

describe("Watchable", function() {
    describe("on set", function() {
        it("should notify watchers", function() {
            let object = new micro.bind.Watchable();
            let calls = [];
            object.watch("foo", (...args) => calls.push(args));
            object.foo = 42;
            expect(object.foo).to.equal(42);
            expect(calls).to.deep.equal([["foo", 42]]);
        });
    });

    describe("splice()", function() {
        it("should notify watchers", function() {
            let arr = new micro.bind.Watchable(["a", "b", "c", "d"]);
            let calls = [];
            arr.watch(Symbol.for("+"), (...args) => calls.push(["+"].concat(args)));
            arr.watch(Symbol.for("-"), (...args) => calls.push(["-"].concat(args)));
            arr.splice(1, 2, "x", "y");
            expect(arr).to.deep.equal(["a", "x", "y", "d"]);
            expect(calls).to.deep.equal([["-", "2", "c"], ["-", "1", "b"], ["+", "1", "x"],
                                         ["+", "2", "y"]]);
        });
    });

    describe("push()", function() {
        it("should notify watchers", function() {
            let arr = new micro.bind.Watchable(["a", "b"]);
            let calls = [];
            arr.watch(Symbol.for("+"), (...args) => calls.push(args));
            arr.push("c");
            expect(arr).to.deep.equal(["a", "b", "c"]);
            expect(calls).to.deep.equal([["2", "c"]]);
        });
    });
});

describe("filter()", function() {
    function makeArrays() {
        let arr = new micro.bind.Watchable(["a1", "b1", "a2", "b2"]);
        return [arr, micro.bind.filter(arr, item => item.startsWith("a"))];
    }

    describe("on arr set", function() {
        it("should update item if item still passes", function() {
            let [arr, filtered] = makeArrays();
            arr[2] = "ax";
            expect(filtered).to.deep.equal(["a1", "ax"]);
        });

        it("should include item if item passes now", function() {
            let [arr, filtered] = makeArrays();
            arr[1] = "ax";
            expect(filtered).to.deep.equal(["a1", "ax", "a2"]);
        });

        it("should exclude item if item does not pass anymore", function() {
            let [arr, filtered] = makeArrays();
            arr[0] = "bx";
            expect(filtered).to.deep.equal(["a2"]);
        });

        it("should have no effect if item still does not pass", function() {
            let [arr, filtered] = makeArrays();
            arr[1] = "bx";
            expect(filtered).to.deep.equal(["a1", "a2"]);
        });
    });

    describe("on arr splice", function() {
        it("should update filtered array", function() {
            let [arr, filtered] = makeArrays();
            arr.splice(1, 2, "ax", "bx");
            expect(filtered).to.deep.equal(["a1", "ax"]);
        });
    });
});

describe("bind()", function() {
    function setupDOMWithList() {
        let arr = new micro.bind.Watchable(["a", "b", "c"]);
        document.body.innerHTML = `
            <ul>
                <template><li></li></template>
            </ul>
        `;
        let elem = document.body.firstElementChild;
        elem.appendChild(micro.bind.list(elem, arr, "item"));
        return [arr, elem];
    }

    describe("on data set", function() {
        it("should update DOM with join", function() {
            let arr = ["a", "b", "c"];
            document.body.innerHTML = "<p><template><span></span></template></p>";
            let elem = document.body.firstElementChild;
            elem.appendChild(micro.bind.join(elem, arr, "item"));
            let nodes = Array.from(elem.childNodes,
                                   n => n.nodeType === Node.ELEMENT_NODE ? n.item : n.nodeValue);
            expect(nodes).to.deep.equal(["a", ", ", "b", ", ", "c"]);
        });
    });

    describe("on data arr set", function() {
        it("should update DOM with list", function() {
            let [arr, elem] = setupDOMWithList();
            arr[1] = "x";
            expect(Array.from(elem.children, c => c.item)).to.deep.equal(["a", "x", "c"]);
        });
    });

    describe("on data arr splice", function() {
        it("should update DOM with list", function() {
            let [arr, elem] = setupDOMWithList();
            arr.splice(1, 1, "x", "y");
            expect(Array.from(elem.children, c => c.item)).to.deep.equal(["a", "x", "y", "c"]);
        });
    });
});
