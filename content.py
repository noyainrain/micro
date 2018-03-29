# Content

# FAZIT => cool, but a bit too much abstraction without value
class WithContent:
    """TODO: Mixin for :class:`Editable` :class:`Object`."""

    async def check_attrs(self, **attrs):
        if 'entity' in attrs:
            return await self.app.resolve_entity(attrs['entity'])

    def do_edit(self, **attrs):
        if 'entity' in attrs:
            self.entity = attrs['entity']
        if 'text' in attrs:
            self.text = str_or_none(attrs['text'])

    def json(self):
        return {
            'entity': self.entity.json() if self.entity else None,
            'text': self.text
        }

# FAZIT => not enough functionality
class WithEntity:
    """TODO: Mixin for :class:`Editable` :class:`Object`."""

    async def check_attrs(self, **attrs):
        if 'entity' in attrs:
            return await self.app.resolve_entity(attrs['entity'])

    def do_edit(self, **attrs):
        if 'entity' in attrs:
            self.entity = attrs['entity']

    def json(self):
        return {'entity': self.entity.json() if self.entity else None}

class Comment(Object, Editable, WithContent):
    def do_edit(self, **attrs):
        entity = await WithContent.check_attrs(self, **attrs)
        # make text non-optional
        if 'text' in attrs and str_or_none(attrs['text']) is None:
            raise ValueError('text_empty')
        WithEntity.do_edit(**attrs, entity=entity)

    def json(self, restricted=False, include=False):
        return {
            **super().json(restricted, include),
            **Editable.json(self, restricted, include),
            **WithEntity.json(self)
        }

# VS

class Comment(Object, Editable):
    def do_edit(self, **attrs):
        if 'entity' in attrs:
            entity = await self.app.resolve_entity(attrs['entity'])
        if 'text' in attrs and str_or_none(attrs['text']) is None:
            raise ValueError('text_empty')

        if 'entity' in attrs:
            self.entity = entity
        if 'text' in attrs:
            self.text = attrs['text']

    def json(self, restricted=False, include=False):
        return {
            **super().json(restricted, include),
            **Editable.json(self, restricted, include),
            'entity': self.entity.json() if self.entity else None,
            'text': self.text
        }

# VS

class Comment(Object, Editable, WithEntity):
    def do_edit(self, **attrs):
        entity = await WithEntity.check_attrs(self, **attrs)
        if 'text' in attrs and str_or_none(attrs['text']) is None:
            raise ValueError('text_empty')

        WithEntity.do_edit(**attrs, entity=entity)
        if 'text' in attrs:
            self.text = attrs['text']

    def json(self, restricted=False, include=False):
        return {
            **super().json(restricted, include),
            **Editable.json(self, restricted, include),
            **WithEntity.json(self),
            'text': self.text
        }

# WIKI
#        async def _call_base(method, *args, **kwargs):
#            results = []
#            for cls in self.__bases__:
#                method = getattr(cls, method, None)
#                if method:
#                    result = method(self, *args, **kwargs)
#                    results.append(await result if iscoroutine(result) else result)
#            return results
#
#        results = await _call_base('check_edit', **attrs)
#        attrs = dict(attrs)
#        for result in results:
#            attrs.update(result)
#        self.do_edit(**attrs)
#        await _call_base('do_edit', **attrs)
