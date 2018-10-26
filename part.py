
# ---

Github: attach file
Facebook: nothing, just a selection of additional content to add
Twitter: nothing, just add gif, add photo
Telelgram: attachment symbol

            <i class="fa fa-spinner fa-spin"></i> You can add more content (image, video, …) by
            inserting a link.

Attach additional content like images, videos, ... by inserting a link.

additional content -> addendum / enclosure / attachment

# Email: multipart
# Github -> markdown

# Twitter: Media/Entity
#   1. POST /media/upload(blob) -> Media
#   2. POST /statuses(media_id) -> Tweet{media_id}
# Facebook: Object
#   A.  POST /photos(blob/url) -> Photo + Post{attached_media}
#   B1. POST /photos(blob/url,published=false) -> Photo
#   B2. POST /feed(attached_media) -> Post{attached_media}
# Slack: Attachment / File
#   A. files.upload(blob) -> File
#   B. files.upload(blob,channel) -> File + Event{file_shared}
#   C. postMessage(attachments) -> Message{attachments}
#   AB = blob, C = struct
#
# VS
#
# Telegram: Media
#   sendVideo/Audio/...(blob/url) -> Message{video/audio/...{file_id}} + File

# General: Resource, Entity, Object, Thing
#          Part
#          Content
# Data, Blob < not really, is like we know nothing about the format
# multipart mixed attachment

# A multimedia item has:
#   content = [Image(...), Text(...), Video(...), Link(...), ...]
#   simpler version for now:
#   text = 'foo'
#   entity = Image(...)
# Content
#   text = 'foo'
#   nontext = Image(...)

# Content
#   text
#   element

# --- refresh

* OQ when / if?
* not, just stay forever as entered
* on edit item?
* can a resource change its type (i.e. content type changes)
* if user has entered description, thumbnail we have to remember that so its lost
  like user_description, user_image_url
* what do other services do?

# --- user input / how to create ---

create:
* a) only url
* b) url, description, image_url
always auto computed:
*           user | auto (reliable)                                              | ?
* Resource: url  | content_type                                                 | description, image_url
* Image:         | image_url (thumb)                                            |
* Video:         | duration, size                                               |
* Audio:         | duration                                                     |
* Tweet:         | description, image_url, text, user_name, user_id, avatar_url |
* WebPage:       |                                                              | icon
* Document:      | image_url (first page)                                       |

if user can edit nothing:
Item.edit(*, resource: str)
# ^ needs to be async then -- maybe not so a good idea, for example setters cannot be async and edit
# is like convenient setters :)
if user can edit things
# A)
Item.set_resource(url: str, description: str = None, image_url: str = None)
# B) Resource as full-fledged Editable Object
Item.resource.edit(...)

# --- Thumbnail storage ---

# A)
# Store file/thumbnail (for fields see below) in redis (as JSON object or via direct data
# structures), exposed via /files/abcdef.png or /thumbnails/abcdef.png
# Resource just has thumbnail_url, thumbnail_size

# B) File/Thumbnail visible via API
class File(Object):
    content_type: str
    ref: int # reference count, will be deleted if 0
    @property
    def data(self) -> bytes:
        pass
# or maybe better name:
class Thumbnail(Object):
    content_type: str
    size: Tuple[int, int]
    @property
    def data(self) -> bytes:
        pass
# ^ exposed via /thumbnails/abcdef.png
class Resource:
    def __init__(self, *, thumbnail_id: str = None) -> None:
        pass
    @property
    def thumbnail(self) -> Thumbnail:
        self.app.r.oget(self.thumbnail_id)
    def json(self):
        return {'thumbnail', self.thumbnail.json()}

# C)
# Because thumbnails are only used for Resource, would rather make Resource an Object with
# @thumbnail_data property (exposed via /api/cats/abcdef/resource/thumbnail.png)

class Resolver:
    def resolve(self, url: str) -> Content:
        data = fetch(url)
        f = extract_image(data)
        self.app.files.add(f.url, f)
        return Video(url, image=f.url)

    def adopt(self, content: Content) -> None:
        del self.cache[content.url]

    def clean(self) -> None:
        for content in self.cache.values():
            content.delete()
        self.cache.values.clear()

class Content:
    def delete(self, app) -> None:
        raise NotImplementedError
        # video example
        if self.url.starts_with('file:'):
            app.files.remove(self.url)
        app.files.remove(self.image_url)

    def copy(self) -> Content:
        pass

class Resource:
    def destroy(self, *, app=None) -> None:
        app = app or current_app()
        if self.url.starts_with('file:'):
            app.files.remove(self.url)

def do_edit(**attrs: object) -> None:
    if 'element' in attrs:
        element = attrs.get('element')
        if not isinstance(element, str):
            raise TypeError()
        self.element = self.app.resolver.resolve(element)

# ---

class ImageRef:
    url: str
    content_type: str
    size: Tuple[int, int]

class Content:
    def json(self) -> Dict[str, object]:
        return {'__type__': type(self).__name__}

class Link(Content):
    url: str
    description: str # auto (opt)
    image: Optional[ImageRef] # auto

class Image(Content):
    url: str
    thumbnail: ImageRef # auto

class Video(Content):
    url: str
    content_type: str # auto
    size: Tuple[int, int] # auto
    duration: Optional[int] # auto
    image: Optional[ImageRef] # auto

    def __init__(
            self, url: str, *, content_type: str = 'video/mp4', size: Tuple[int, int] = (300, 150),
            duration: int = None, image: ImageRef = None) -> None:
        pass

class Audio(Content):
    url: str
    content_type: str # auto
    duration: Optional[int] # auto
    image: Optional[ImageRef] # auto

class Tweet(Content):
    url: str
    id: str # auto
    text: str # auto
    user_id: str # auto
    user_name: str # auto
    avatar_url: ImageRef # auto

class Quote(Content):
    text: str
    author: str

#class Resource:
#    url: str # min
#
#class WithImageRepr:
#    image: Optional[ImageRef]

    ## See if HTML5 can read it from stream, otherwise as property: => EXIF (jpeg and since 2017 png)
    #alt: str
    #CONTENT_TYPES = ['image/jpeg', 'image/png', 'image/svg+xml', 'image/gif'] # (check browser support)
    ## See if HTML5 can read it from stream, otherwise as property: => audioTracks and textTracks, event addressable via foo.mpg#track=oink :)
    #audio_description
    #captions
    #CONTENT_TYPES = ['video/mp4', 'text/html'] # (check browser support)
    ## See if HTML5 can read it from stream, otherwise as property: => ID3 Tag USLT
    #transcript: str
    #CONTENT_TYPES = ['audio/mp3', 'audio/mp4', 'audio/wav'] # (check browser support)

    #def __init__(self, url: str, content_type: str, description: str, *, thumbnail_url: str = None,
    #             thumbnail_size: Tuple[int, int] = None) -> None:
    #    self.url = url
    #    self.content_type = content_type
    #    self.summary = summary
    #    self.image_url = image_url
    #    self.image_size = image_size
    #def __init__(self, url: str, content_type: str, description: str,
    #             thumbnail_size: Tuple[int, int]) -> None:
    #    super(url, content_type, description, thumbnail_url=url, thumbnail_size=thumbnail_size)
#def json(self) -> Dict[str, object]:
#    return {
#        **super.json(),
#        'url': self.url,
#        'content_type': self.content_type,
#        'description': description,
#        'thumbnail_url': self.thumbnail_url,
#        'thumbnail_size': self.thumbnail_size
#    }

#class Resource:
#    def __init__(self, url: str, content_type: str, description: str, *, thumbnail_url: str = None,
#                 thumbnail_size: Tuple[int, int] = None) -> None:
#        self.url = url
#        self.content_type = content_type
#        self.description = description
#        self.thumbnail_url = thumbnail_url
#        self.thumbnail_size = thumbnail_size
#
#    def json(self) -> Dict[str, object]:
#        return {
#            '__type__': type(self).__name__,
#            'url': self.url,
#            'content_type': self.content_type,
#            'description': description,
#            'thumbnail_url': self.thumbnail_url,
#            'thumbnail_size': self.thumbnail_size
#        }
#
#class Image(Resource):
#    CONTENT_TYPES = ['image/jpeg', 'image/png', 'image/svg+xml', 'image/gif'] # (check browser support)
#
#    def __init__(self, url: str, content_type: str, description: str,
#                 thumbnail_size: Tuple[int, int]) -> None:
#        super(url, content_type, description, thumbnail_url=url, thumbnail_size=thumbnail_size)
#
#class Video(Resource):
#    CONTENT_TYPES = ['video/mp4', 'text/html'] # (check browser support)
#
#    duration: int
#    size: Tuple[int, int]
#
#class Audio(Resource):
#    CONTENT_TYPES = ['audio/mp3', 'audio/mp4', 'audio/wav'] # (check browser support)
#
#    duration: int

#class Document(Resource):
# do not need anything per se, will just be rendered as std resource

# ---
# do not archive just for now
class Tweet(Content):
    CONTENT_TYPES = ['text/html']

    text: str
    user_id: str
    user_name: str
    avatar_url: str

# ---
# for now leave this, resource is fair enough, only icon additional
class Webpage(Content):
    def __init__(self, url: str, content_type: str, description: str, *, image_url = None,
                 icon_url = None) -> None:
        if content_type not in ('text/html', 'application/xhtml+xml'):
            raise ValueError()
        super(url, content_type, description, image_url)
        self.icon_url = icon_url

    def json(self) -> Dict[str, object]:
        return {**super().json(), 'icon_url': self.icon_url}
