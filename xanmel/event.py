import asyncio

from .utils import current_time


class BaseEvent(object):
    def __init__(self, module, **kwargs):
        self.module = module
        self.properties = kwargs
        self.timestamp = current_time()

    def fire(self):
        for i in self.module.loop.event_handlers:
            self.module.loop.create_task(i.handle(self))
