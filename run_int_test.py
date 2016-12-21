import time
import asyncio

from xanmel import Xanmel
from int_test.fake_irc import FakeIRCServer


loop = asyncio.get_event_loop()
xanmel = Xanmel(loop=loop, config_path='int_test_config.yaml')
irc_server = FakeIRCServer(loop)
time.sleep(1)
xanmel.load_modules()

loop.run_forever()
