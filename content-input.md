# Content input

micro.util.findURLs = function(text) {
    let urls = [];
    let pattern = /(^|\s)(https?:\/\/\S+)/g;
    let match = null;
    do {
        match = pattern.exec(text);
        if (match) {
            urls.push({url: match[2], from: match[1] ? match.index + 1 : match.index, to: pattern.lastIndex});
        }
    } while (match);
    return urls;
};

// ---

const TEXT = `\
https://example.org/foo
oink http://example.com/bar oink
http://example.net/\
`;


describe("findURLs", function() {
    it("should find URLs", function() {
        let urls = micro.util.findURLs(TEXT);
        expect(urls).to.deep.equal([
            {url: "https://example.org/foo", from: 0, to: 23},
            {url: "http://example.com/bar", from: 29, to: 51},
            {url: "http://example.net/", from: 57, to: 76}
        ]);
    });
});

// ---

/**
 * TODO.
 */
micro.TextEntityInput = class extends HTMLElement {
    createdCallback() {
        console.log("CREATE TEXT ENTITY");
        this.appendChild(
            document.importNode(ui.querySelector("#micro-text-entity-input-template").content,
                                true));
        this._urls = new Set();
        this._data = new micro.bind.Watchable({
            entity: null,

            remove: () => {
                console.log("REEEEMOOOVE");
                this._data.entity = null;
            },

            input: async (event) => {
                // TODO: works, but just selecting and then deselecting an URL will detect a new URL
                // good enough, or should be better?
                //console.log(this._urls);
                if (this._data.entityElem) {
                    return;
                }

                let textarea = event.target;
                let urls = micro.util.findURLs(textarea.value);
                if (textarea == document.activeElement) {
                    urls = urls.filter(u => textarea.selectionStart < u.from || textarea.selectionStart > u.to);
                }
                //console.log(urls);
                let newURL = urls.find(u => !this._urls.has(u.url));
                this._urls = new Set(urls.map(u => u.url));
                if (newURL) {
                    newURL = newURL.url;
                    console.log(newURL);
                    this._data.previewing = true;
                    let entity = null;
                    try {
                        entity = await micro.call("GET", `/api/previews/${newURL}`);
                    } catch (e) {
                        console.log("ERROR", e.error);
                        if (!(e instanceof micro.APIError && e.error.__type__ === "WebError")) {
                            throw e;
                        }
                    }
                    this._data.previewing = false;
                    console.log("ENTITY", entity);

                    if (entity) {
                        this._data.entity = entity;
                        this._data.entity_url = newURL;
                    }
                }
                /*let newURL = urls.find(u =>
                    !this._urls.has(u.url) &&
                    !(document.activeElement && textarea.selectionStart >= u.from &&
                      textarea.selectionStart <= u.to));*/
            }
        });
        micro.bind.bind(this.children, this._data);

        let updateClass = () => {
            this.classList.toggle("micro-text-entity-input-entity", this._data.entity);
            this.classList.toggle("micro-text-entity-input-previewing", this._data.previewing);
        };
        this._data.watch("entity", updateClass);
        this._data.watch("previewing", updateClass);

        this._textarea = this.querySelector("textarea");
    }

    get value() {
        return {
            text: this._textarea.value,
            entity: this._data.entity_url
        };
    }

    set value(value) {
        this._textarea.value = value.text;
        this._data.entity_url = value.entity;
    }

    reset() {
        this.value = {text: "", entity: null};
    }
};
document.registerElement("micro-text-entity-input", micro.TextEntityInput);

<template id="micro-text-entity-input-template">
    <div data-content="renderEntity entity"></div>
    <button is="micro-button" type="button" class="action action-subtle" data-run="remove">
        <i class="fa fa-minus-circle"></i> Remove
    </button>
    <label>
        <textarea data-oninput="input" data-onclick="input" data-onkeyup="input" data-onblur="input" data-onfocus="input"></textarea>
    </label>
    <p>
        <small>
            <i class="fa fa-spinner fa-spin"></i> You can add more content (image, video, …) by
            inserting a link.
        </small>
    </p>
</template>
<style>
    micro-text-entity-input > * {
        margin: calc(1.5rem / 4) 0;
    }

    micro-text-entity-input:not(.micro-text-entity-input-entity) > button,
    micro-text-entity-input:not(.micro-text-entity-input-previewing) > p i {
        display: none;
    }
</style>

// hello.html

<micro-text-entity-input></micro-text-entity-input>

// hello.js create greeting

try {
    let input = this.querySelector("micro-text-entity-input");
    let greeting = await micro.call("POST", "/api/greetings",
        {text: input.value.text || null, entity: input.value.entity});
    input.reset();
    this._data.greetings.unshift(greeting);
} catch(e) {
    console.log(e);
}
