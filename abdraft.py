# A) Value
# XXX at least ATM there cannot be a file without a resource value, but not coupled

class Resource:
    url: str

class Image(Resource):
    size: Tuple[int, int]

    # XXX value has utilities to persist stuff
    def copy_files(self, store, app) -> Resource:
        url = self.url
        if url.startswith('file:'):
            url = 'file://{}'.format(randstr())
            app.r.set(url, store.get(self.url))
        return Video(url, self.content_type, self.size, self.duration,
                     self.image.persist(store, app))

class Video(Resource):
    content_type: str
    size: Tuple[int, int]
    duration: Optional[int]
    image: Image

    def delete_files(self, app):
        if self.url.startswith('file:'):
            app.r.delete(self.url)
        self.image.delete(app)


class Resolver:
    async def resolve(url, post) -> Resource:
        self.store.put(url, await fetch(url, max=5 * 1024 * 1024))
        return post(await handle_video(url, self.store))







async def handle_video(url, store) -> Optional[Resource]:
    data, content_type = store.get(url)
    info = get_video_info(data)
    poster = get_video_image(data)
    image_url = 'cache://{}.{}'.format(randstr(), image.ext)
    store.put(image_url, poster.content_type, poster.data)
    return Video(url, content_type, info.size, info.duration, Image(image_url, image.size))

def image_size(video, store):
    data, _ = store.get(video.image.url)
    if not data:
        raise ValueError()
    data, size = resize_image(data, 720)
    store.put(video.image.url, video.image.content_type, data)
    return Video(video.url, video.content_type, video.size, video.duration,
                 Image(video.image.url, size))

# /api/previews/content/(url), post_process: image_size
class PreviewsEndpoint:
    async def get(self, url):
        video = await self.app.resolver.resolve(url, post=self.post_process)
        self.write(video.json())








# /files/(name)
class FileEndpoint:
    def get(self, name):
        url = 'file://{}'.format(name)
        data = self.app.resolver.store.get(url) or self.app.r.get(url)
        if not data:
            raise 404
        self.write(data)

# XXX async edit OR extra method
class WithContent:
    async def do_edit(self, **args):
        if 'resource' in args:
            if self.resource:
                self.resource.delete_files(self.app)
            url = args['resource'] # could allow value here
            resource = await self.app.resolver.resolve(url, post=image_resize)
            self.resource = resource.copy_files(self.app.resolver.store, self.app)

# B) Object
# XXX Resources are always linked to entity, cannot be simple fields

class Resource(Object):
    url: str

class Image(Resource):
    size: Tuple[int, int]

    # XXX has utility pseudo make function
    @staticmethod
    def create(data, size, app):
        id = randstr()
        image = Image(id=id, url='file://{}'.format(id), size=size)
        app.r.oset(id, image)
        app.r.set('{}.data'.format(id), data)


class Video(Resource):
    content_type: str
    size: Tuple[int, int]
    duration: Optional[int]
    image_id: str

    def delete(self):
        self.app.r.delete(self.id)
        if self.url.startswith('file:'):
            self.app.r.delete('{}.data'.format(self.id))
        self.image.delete()

class Resources:
    async def preview(url, post) -> Resource:
        data = await fetch(url, max=5 * 1042 * 1024)
        video = post(await handle_video(url, data, self.app))
        self.app.r.sadd('previews', video.id)

    def take_preview(id):
        self.app.r.srem('previews', id)
        return self.app.oget(id)

# XXX handler is not only responsible for parsing, but also persisently creating objects
async def handle_video(url, data, content_type, app) -> Optional[Resource]:
    info = get_video_info(data)
    poster = get_video_poster(data)
    image = Image.create(poster.data, size=poster.size)
    return Video.create(url, content_type, info.size, info.duration, image)

# XXX resource is a representation and should be immutable; creating a new object feels like we
# should have used a value in the first place
def image_size(video):
    image = video.image
    if not image:
        raise ValueError()
    data, size = resize_image(image.data, 720)
    image = Image(id=image.id, url=image.url, size=size)
    app.r.oset(image.id, image)
    app.r.set('{}.data'.format(image.id), data)

# /api/resources/content/(id), post_process: image_size
class ResourcesEndpoint:
    async def post(self):
        args = self.check_args({'url': str})
        video = await self.app.resources.preview(**args, post=self.post_process)
        self.write(video.json())

# /api/resources/(id)
class ResourceEndpoint:
    def get(self, id):
        resource = self.app.resources.get(id)
        self.write(resource.json())

# /api/resources/(id).(ext)
class ResourceDataEndpoint:
    def get(self, id):
        resource = self.app.resources.get(id)
        if not resource.data:
            raise 404
        self.write(resource.data)


# XXX must create preview OR async edit OR extra method
class WithContent:
    def do_edit(self, **args):
        if 'resource' in args:
            if self.resource:
                self.resource.delete()
            id = args['element']
            self.resource = self.app.resources.take_preview(id)

# -----
    # A store
    # B property data = app.r.get('{}.data'.format(image.id))

    # XXX nah filenmame must change (two users preview same URL, get same temporary resource +
    # files), then both persist the resource, pointing to same local file :/ (which vahishes if obj
    # is deleted)

    @property
    def files(self):
        return ([self.url] if self.url.startswith('file:') else []) + self.image.files

    if self.resource:
        self.app.files.delete(*self.resource.files)
    url = args['resource'] # could allow value here
    self.resource = await self.app.resolver.resolve(url, post=image_resize)
    self.app.files.copy(self.app.resolver.store, *self.resource.files)

    # other alternative would be reference counting
    if self.resource:
        self.app.files.unref(*self.resource.files)
    url = args['resource'] # could allow value here
    self.resource = await self.app.resolver.resolve(url, post=image_resize)
    self.app.files.ref(*self.resource.files)
