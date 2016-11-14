import asyncio

from xanmel.modules.posix.events import StdinInput
from xanmel.modules.posix.handlers import EchoHandler


async def test():
    while True:
        print('Hello')
        await asyncio.sleep(1)


loop = asyncio.get_event_loop()
loop.set_debug(True)
loop.event_handlers = []
StdinInput.register_event(loop)
EchoHandler.register_handler(loop)
loop.create_task(test())
loop.run_forever()
