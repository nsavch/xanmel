import asyncio

import bottom

from xanmel import Module, ChatUser
from .events import *


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
            self.client.send('PRIVMSG', target=self.config['channel'], message=self.config['greeting'])

    async def pong(self, message, **kwargs):
        self.client.send('PONG', message=message)

    def setup_event_generators(self):
        self.client.on('CLIENT_CONNECT', self.connect)
        self.client.on('PING', self.pong)
        self.client.on('PRIVMSG', self.process_message)
        self.loop.create_task(self.client.connect())

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

    async def send_channel_message(self, message, **kwargs):
        self.client.send('PRIVMSG', target=self.config['channel'], message=message)

    def teardown(self):
        self.loop.run_until_complete(self.client.disconnect())
