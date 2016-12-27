import asyncio
import logging
import random

import bottom

from xanmel import Module, ChatUser
from .events import *

logger = logging.getLogger(__name__)


class IRCChatUser(ChatUser):
    user_type = 'irc'

    def __init__(self, *args, **kwargs):
        super(IRCChatUser, self).__init__(*args, **kwargs)
        self.botnick = self.module.config['nick']

    def unique_id(self):
        return self.properties['irc_user']

    @property
    def is_admin(self):
        return self.properties['irc_user'] in self.module.config['admin_users']

    async def private_reply(self, message, **kwargs):
        self.module.client.send('PRIVMSG', target=self.name, message=message)

    async def public_reply(self, message, **kwargs):
        self.module.client.send('PRIVMSG', target=self.module.config['channel'], message=message)


class IRCModule(Module):
    def __init__(self, xanmel, config):
        self.connected = False
        self.joined = False
        self.reconnect_interval = 0
        super(IRCModule, self).__init__(xanmel, config)
        self.client = bottom.Client(host=config['host'],
                                    port=config['port'],
                                    ssl=config['ssl'],
                                    loop=self.loop)

    async def connect(self):
        if not self.connected:
            return
        self.send('USER', user=self.config['nick'], realname=self.config['realname'])
        self.send('NICK', nick=self.config['nick'])

        done, pending = await asyncio.wait(
            [self.client.wait("RPL_ENDOFMOTD"), self.client.wait("ERR_NOMOTD")],
            loop=self.loop,
            return_when=asyncio.FIRST_COMPLETED)
        self.send('JOIN', channel=self.config['channel'])
        # Cancel whichever waiter's event didn't come in.
        for future in pending:
            future.cancel()
        if self.config.get('greeting'):
            self.send('PRIVMSG', target=self.config['channel'], message=self.config['greeting'])
        self.joined = True
        self.reconnect_interval = 0

    def send(self, command, **kwargs):
        if not self.client.protocol:
            logger.debug('Skipping command %s while not connected', command)
            return
        self.client.send(command, **kwargs)

    async def pong(self, message, **kwargs):
        self.send('PONG', message=message)

    async def disconnect(self):
        self.connected = False

    async def check_connection(self):
        while True:
            # logger.debug('Connection status - connected:%s, joined:%s', self.connected, self.joined)
            if not self.connected:
                if not self.reconnect_interval:
                    # Large sleeping interval to prevent throttling disconnections
                    await asyncio.sleep(self.reconnect_interval + random.random() * 5)
                if self.client.protocol:
                    await self.client.disconnect()
                if self.reconnect_interval < 120:
                    self.reconnect_interval += 5
                self.joined = False
                try:
                    await self.client.connect()
                    self.connected = True
                except:
                    logger.debug('Exception during IRC connect.', exc_info=True)
            elif not self.joined:
                await asyncio.sleep(60)
                if not self.joined:
                    logger.debug('Still not joined? Reconnect!')
                    self.connected = False
                    if self.client.protocol:
                        await self.client.disconnect()
            else:
                # send a keepalive message. PING would probably fit better, but parsing PONG isn't
                # supported in python-bottom
                self.send('NOTICE', target="#xanmel", message=random.randint(0, 1024*1024))
            await asyncio.sleep(5)

    def setup_event_generators(self):
        self.client.on('CLIENT_CONNECT', self.connect)
        self.client.on('CLIENT_DISCONNECT', self.disconnect)
        self.client.on('PING', self.pong)
        self.client.on('PRIVMSG', self.process_message)
        self.loop.create_task(self.check_connection())

    async def process_message(self, target, message, **kwargs):
        kwargs['chat_user'] = IRCChatUser(self,
                                          kwargs['nick'],
                                          irc_user='%s@%s' % (kwargs['user'], kwargs['host']))
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

    def teardown(self):
        self.loop.run_until_complete(self.client.disconnect())
        self.client.protocol = None
