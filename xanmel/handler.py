class BaseHandler(object):
    @classmethod
    def register_handler(cls, loop):
        loop.event_handlers.append(cls())

    async def handle(self, event):
        pass
