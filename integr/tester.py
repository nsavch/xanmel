import asyncio

from xanmel import Xanmel
from .fake_irc import FakeIRCServer


class IntTester:
    def __init__(self):
        self.loop = asyncio.get_event_loop()
        self.irc = FakeIRCServer(self.loop)
        self.loop.run_until_complete(self.irc.start_server())
        self.xanmel = Xanmel(self.loop, 'integr_config.yaml')
        self.xanmel.load_modules()

    def run(self):
        test_methods = []
        for i in dir(self):
            if i.startswith('test_'):
                test_methods.append(i[5:])
        for i in sorted(test_methods):
            self.loop.run_until_complete(getattr(self, 'test_' + i)())
            self.irc.reset()
        print('*' * 80)
        print('Bingo! %s tests run successfully!' % len(test_methods))
        print('*' * 80)

    async def test_0010_irc_connect(self):
        self.irc.expect_connection()
        self.irc.expect(command='USER', kwargs={'user': 'xanmel'})
        self.irc.expect(command='NICK', kwargs={'new_nick': 'xanmel', 'host': ''})
        self.irc.send(command='RPL_ENDOFMOTD', kwargs={})
        self.irc.expect(command='JOIN', kwargs={'channel': '#xanmel'})
        self.irc.expect(command='PRIVMSG', kwargs={'target': '#xanmel', 'message': 'HELLO WORLD!'})
        await self.irc.execute()

    async def test_0020_handle_irc_missing_during_startup(self):
        pass

    async def test_0030_handle_irc_connection_loss(self):
        await self.irc.stop_server()
        self.irc.expect_disconnetion()
        await self.irc.execute()
        self.irc.reset()

        await self.irc.start_server()
        self.irc.expect_connection()
        self.irc.expect(command='USER', kwargs={'user': 'xanmel'})
        self.irc.expect(command='NICK', kwargs={'new_nick': 'xanmel', 'host': ''})
        self.irc.send(command='RPL_ENDOFMOTD', kwargs={})
        self.irc.expect(command='JOIN', kwargs={'channel': '#xanmel'})
        self.irc.expect(command='PRIVMSG', kwargs={'target': '#xanmel', 'message': 'HELLO WORLD!'})
        await asyncio.sleep(30)
        await self.irc.execute()
