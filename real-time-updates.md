# real-time-updates

* CONTINUE: read MDN server sent events section
* CONTINUE: e2e test update
* CONTINUE: polyfill (for Edge support)
* TODO: try little animation on update (if user not self)

```
class Activity:
    def publish(self, event: 'Event') -> None:
        # ...
        for notify in self._live_subscribers:
            notify(event)

    def subscribe_live(self, notify: Callable[['Event'], None]) -> None:
        self._live_subscribers.append(notify)
        print('subscribe', self, self._live_subscribers)

(r'{}/stream$'.format(url), _ActivityStreamEndpoint, {'get_activity': get_activity})
class _ActivityStreamEndpoint(Endpoint):
    def initialize(self, get_activity: GetActivityFunc) -> None: # type: ignore
        super().initialize()
        self.get_activity = get_activity
        self._activity = None

    @asynchronous
    def get(self, *args: str) -> None:
        print('stream get', args)
        self._activity = self.get_activity(*args)
        self.set_header('Content-Type', 'text/event-stream')
        self.flush()

        def _event(event: Event) -> None:
            print('stream event', event, self._activity)
            # TODO pass user to json()
            self.write('data: {}\n\n'.format(json.dumps(event.json(restricted=True, include=True))))
            self.flush()
        self._activity.subscribe_live(_event)

micro.ActivityPage = class extends micro.Page {
    attachedCallback() {
        // ...
        this.stream = new EventSource("/api/activity/v2/stream");
        // TODO unsubscribe
        this.stream.addEventListener("open", event => {
            console.log("open", event);
        });
        this.stream.addEventListener("error", event => {
            console.log("error", event);
        });
        this.stream.addEventListener("message", event => {
            console.log("message", event);
            let e = JSON.parse(event.data);
            ui.dispatchEvent(new CustomEvent(e.type, {detail: e}));

            this._data.events.unshift(e);
            animate(this.querySelector(".micro-timeline li:first-child"));
        });
    }
};
```
