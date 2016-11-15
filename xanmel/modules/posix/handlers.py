from xanmel.handler import BaseHandler
from .actions import PrintStdout
from .events import StdinInput


class EchoHandler(BaseHandler):
    async def handle(self, event):
        if isinstance(event, StdinInput):
            await PrintStdout(message='STDIN INPUT RECEIVED: ' + event.properties['input']).run()
