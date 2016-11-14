from .utils import current_time


class BaseEvent(object):
    def __init__(self, loop, **kwargs):
        self.loop = loop
        self.properties = kwargs
        self.timestamp = current_time()

    @classmethod
    def register_event(cls, loop):
        raise NotImplementedError()

    def fire(self):
        for i in self.loop.event_handlers:
            i.handle(self)
