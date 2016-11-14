from xanmel.handler import BaseHandler
from .actions import PrintStdout
from .events import StdinInput


class EchoHandler(BaseHandler):
    def handle(self, event):
        if isinstance(event, StdinInput):
            PrintStdout(message=event.properties['input']).run()
