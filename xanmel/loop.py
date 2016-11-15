import asyncio

from xanmel.modules.posix.events import StdinInput
from xanmel.modules.posix.handlers import EchoHandler


loop = asyncio.get_event_loop()
loop.set_debug(True)
loop.event_handlers = []
StdinInput.register_event(loop)
EchoHandler.register_handler(loop)
loop.run_forever()
