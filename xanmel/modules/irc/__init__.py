import asyncio

import bottom

from xanmel.base_classes import BaseModule


class Module(BaseModule):
    def __init__(self, loop, config):
        super(Module, self).__init__(loop, config)
        self.client = bottom.Client(host=config['host'],
                                    port=config['port'],
                                    ssl=config['ssl'],
                                    loop=loop)

    async def connect(self):
        self.client.send('USER', user=self.config['nick'], realname=self.config['realname'])
        self.client.send('NICK', nick=self.config['nick'])

        done, pending = await asyncio.wait(
            [self.client.wait("RPL_ENDOFMOTD"), self.client.wait("ERR_NOMOTD")],
            loop=self.loop,
            return_when=asyncio.FIRST_COMPLETED)
        self.client.send('JOIN', channel=self.config['channel'])
        # Cancel whichever waiter's event didn't come in.
        for future in pending:
            future.cancel()

    async def pong(self, message, **kwargs):
        self.client.send('PONG', message=message)

    def setup_event_generators(self):
        self.client.on('CLIENT_CONNECT', self.connect)
        self.client.on('PING', self.pong)
        self.loop.create_task(self.client.connect())
