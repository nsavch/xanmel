import asyncio

import bottom

from xanmel.base_classes import Module
from .events import *


class IRCModule(Module):
    def __init__(self, xanmel, config):
        super(IRCModule, self).__init__(xanmel, config)
        self.client = bottom.Client(host=config['host'],
                                    port=config['port'],
                                    ssl=config['ssl'],
                                    loop=self.loop)

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
        if self.config.get('greeting'):
            test = b'^xE20Tri^xF40flu^xFB0ope^xCB0raz^xAF1ine^7\xee\x83\x81\xee\x83\x82\xee\x83\x83\xee\x83\x84\xe2\x97\x86\xf0\x9f\x8c\x8f\xf0\x9f\x8c\x8e'
            from xanmel.modules.xonotic.colors import Color
            self.client.send('PRIVMSG', target=self.config['channel'],
                             message=Color.dp_to_irc(test).decode('utf8'))
            self.client.send('PRIVMSG', target=self.config['channel'], message=self.config['greeting'])

    async def pong(self, message, **kwargs):
        self.client.send('PONG', message=message)

    def setup_event_generators(self):
        self.client.on('CLIENT_CONNECT', self.connect)
        self.client.on('PING', self.pong)
        self.client.on('PRIVMSG', self.process_message)
        self.loop.create_task(self.client.connect())

    async def process_message(self, target, message, **kwargs):
        if target == self.config['nick']:
            PrivateMessage(self, message=message, **kwargs).fire()
        elif target == self.config['channel']:
            is_mention = False
            for i in self.config['mention_delimeters']:
                if message.startswith(self.config['nick'] + i):
                    is_mention = True
                    message = message[len(self.config['nick'] + i):].lstrip()
            if is_mention:
                MentionMessage(self, message=message, **kwargs).fire()
            else:
                ChannelMessage(self, message=message, **kwargs).fire()

    async def send_channel_message(self, message, **kwargs):
        self.client.send('PRIVMSG', target=self.config['channel'], message=message)

    def teardown(self):
        self.loop.run_until_complete(self.client.disconnect())
