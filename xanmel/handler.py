class BaseHandler(object):
    @classmethod
    def register_handler(cls, loop):
        loop.event_handlers.append(cls())

    def handle(self, event):
        pass
