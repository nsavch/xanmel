import sys

from xanmel.event import BaseEvent


class StdinInput(BaseEvent):
    @classmethod
    def register_event(cls, loop):
        async def __process():
            while True:
                line = await loop.run_in_executor(None, sys.stdin.readline)
                if line.endswith('\n'):
                    line = line[:-1]
                event = cls(loop, input=line)
                event.fire()
        loop.create_task(__process())
