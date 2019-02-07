Investigation so far:

* <micro-options> is empty / constructor is not called, thus activate() undefined
* Seems to be timing related somehow, a 100ms wait in setupDOM fixes it

Investigation of webcomponents.js v0:

* bootstrap() call needed before any element is upgraded
* it seems like bootstrap() is called on HTMLImportReady event
  * To observe, add console.log to bootstrap() in src/CustomElements/boot.js
* which is fired directly on domready in FF, but way to late in Safari

error also seen on FF once:

```
Firefox 64.0.0 (Windows 10 0.0.0): Executed 36 of 59 SUCCESS (0 secs / 0.036 secs)
    elem.activate is not a function
    @tests/test_index.js:64:13
```
