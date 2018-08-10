/*
 * keyboard.js
 * Released into the public domain
 * https://github.com/noyainrain/micro/blob/master/client/keyboard.js
 */

/* eslint-env mocha */
/* global chai, expect */
/* eslint-disable no-unused-expressions, prefer-arrow-callback */

"use strict";

window.expect = window.expect || chai.expect;

describe("ShortcutContext", function() {
    function setupDOM(calls) {
        document.body.innerHTML = "<main><span><input></input></span></main>";
        document.querySelector("main").addEventListener(
            "keydown", event => calls.push(["keydown", event.key]));
        let span = document.querySelector("span");
        span.shortcutContext = new micro.keyboard.ShortcutContext(span);
        span.shortcutContext.add("A", (...args) => calls.push(["shortcut"].concat(args)));
        span.shortcutContext.add("B,A", (...args) => calls.push(["shortcut"].concat(args)));
        span.shortcutContext.add("Control+Enter",
                                 (...args) => calls.push(["shortcut"].concat(args)));
        return [span, document.querySelector("input")];
    }

    describe("on keydown", function() {
        it("should trigger", function() {
            let calls = [];
            let [span] = setupDOM(calls);
            span.dispatchEvent(new KeyboardEvent("keydown", {key: "a", bubbles: true}));
            expect(calls).to.deep.equal([["shortcut", "A", span.shortcutContext]]);
        });

        it("should trigger for prefix", function() {
            let calls = [];
            let [span] = setupDOM(calls);
            span.dispatchEvent(new KeyboardEvent("keydown", {key: "b", bubbles: true}));
            span.dispatchEvent(new KeyboardEvent("keydown", {key: "a", bubbles: true}));
            expect(calls).to.deep.equal([["shortcut", "B,A", span.shortcutContext]]);
        });

        it("should do nothing for other key", function() {
            let calls = [];
            let [span] = setupDOM(calls);
            span.dispatchEvent(new KeyboardEvent("keydown", {key: "c", bubbles: true}));
            expect(calls).to.deep.equal([["keydown", "c"]]);
        });

        it("should do nothing in input mode", function() {
            let calls = [];
            let [, input] = setupDOM(calls);
            input.dispatchEvent(new KeyboardEvent("keydown", {key: "a", bubbles: true}));
            expect(calls).to.deep.equal([["keydown", "a"]]);
        });

        it("should trigger for control keys in input mode", function() {
            let calls = [];
            let [span, input] = setupDOM(calls);
            input.dispatchEvent(new KeyboardEvent("keydown", {key: "Enter", ctrlKey: true, bubbles: true}));
            expect(calls).to.deep.equal([["shortcut", "Control+Enter", span.shortcutContext]]);
        });
    });
});

describe("Shortcut", function() {
    function setupDOM(calls) {
        document.body.innerHTML = "<main><button></button></main>";
        let main = document.body.firstElementChild;
        main.shortcutContext = new micro.keyboard.ShortcutContext(main);
        let button = document.querySelector("button");
        button.shortcut = new micro.keyboard.Shortcut(button, "A");
        button.addEventListener("click", () => calls.push(["click"]));
        return main;
    }

    describe("on shortcut", function() {
        it("should click element", function() {
            let calls = [];
            let main = setupDOM(calls);
            main.shortcutContext.trigger("A");
            expect(calls).to.deep.equal([["click"]]);
        });

        it("should do nothing if elem is invisible", function() {
            let calls = [];
            let main = setupDOM(calls);
            main.style.display = "none";
            main.shortcutContext.trigger("A");
            expect(calls).to.deep.equal([]);
        });
    });
});

describe("quickNavigate", function() {
    function setupDOM(focusIndex) {
        document.body.innerHTML = `
            <div class="micro-quick-nav" tabindex="0"></div>
            <div></div>
            <div class="micro-quick-nav" tabindex="0" style="display: none;"></div>
            <div class="micro-quick-nav" tabindex="0"></div>
        `;
        let elems = Array.from(document.body.children);
        elems[focusIndex].focus();
        return elems;
    }

    it("should focus next", function() {
        let elems = setupDOM(0);
        micro.keyboard.quickNavigate();
        expect(document.activeElement).to.equal(elems[3]);
    });

    it("should focus body for last element", function() {
        setupDOM(3);
        micro.keyboard.quickNavigate();
        expect(document.activeElement).to.equal(document.body);
    });

    it("should focus previous if dir is prev", function() {
        let elems = setupDOM(3);
        micro.keyboard.quickNavigate("prev");
        expect(document.activeElement).to.equal(elems[0]);
    });
});

describe("watchLifecycle", function() {
    function makeSpan(calls) {
        let span = document.createElement("span");
        micro.keyboard.watchLifecycle(span, {
            onConnect: (...args) => calls.push(["connect"].concat(args)),
            onDisconnect: (...args) => calls.push(["disconnect"].concat(args))
        });
        return span;
    }

    function timeout(delay) {
        return new Promise(resolve => setTimeout(resolve, delay));
    }

    describe("on connect", function() {
        it("should notify watchers", async function() {
            let calls = [];
            let span = makeSpan(calls);
            document.body.appendChild(span);
            await timeout();
            expect(calls).to.deep.equal([["connect", span]]);
        });

        it("should do nothing for disconnected elem", async function() {
            let calls = [];
            let span = makeSpan(calls);
            document.body.appendChild(span);
            await timeout();
            span.remove();
            await timeout();
            document.body.appendChild(span);
            await timeout();
            expect(calls).to.deep.equal([["connect", span], ["disconnect", span]]);
        });
    });
});

describe("enableActivedClass", function() {
    function setupDOM() {
        document.body.innerHTML = "<button></button><button></button>";
        micro.keyboard.enableActivatedClass();
        return Array.from(document.body.children);
    }

    describe("on click", function() {
        it("should apply activated class", function() {
            let buttons = setupDOM();
            buttons[0].focus();
            buttons[0].click();
            expect(buttons[0].classList.contains("micro-activated")).to.be.true;
        });
    });

    describe("on blur", function() {
        it("should reset activated class", function() {
            let buttons = setupDOM();
            buttons[0].focus();
            buttons[0].click();
            buttons[1].focus();
            buttons[1].click();
            expect(buttons[0].classList.contains("micro-activated")).to.be.false;
        });
    });
});
