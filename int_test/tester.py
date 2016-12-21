import asyncio

from xanmel import Xanmel
from .fake_irc import FakeIRCServer


class IntTester:
    def __init__(self):
        self.loop = asyncio.get_event_loop()
        self.xanmel = Xanmel(self.loop, 'int_test_config.yaml')
        self.irc = FakeIRCServer(self.loop)
        self.xanmel.load_modules()

    def run(self):
        test_methods = []
        for i in dir(self):
            if i.startswith('test_'):
                test_methods.append(i[5:])
        for i in sorted(test_methods):
            self.loop.run_until_complete(getattr(self, 'test_' + i))

    def test_0001_irc_connect(self):
        pass
