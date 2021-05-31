import asyncio

from xanmel import Action


class ChannelMessage(Action):
    async def run(self, message, prefix='', **kwargs):
        async with self.module.msg_lock:
            if prefix:
                message = prefix + message
            self.module.send('PRIVMSG', target=self.module.config['channel'], message=message)


class ChannelMessages(Action):
    async def run(self, messages, prefix='', interval=0, **kwargs):
        async with self.module.msg_lock:
            for message in messages:
                if prefix:
                    message = prefix + message
                await asyncio.sleep(interval)
                self.module.send('PRIVMSG', target=self.module.config['channel'], message=message)


class PrivateMessage(Action):
    async def run(self, target, message, prefix='', **kwargs):
        if prefix:
            message = prefix + message
        self.module.send('PRIVMSG', target=target, message=message)


class PrivateMessages(Action):
    async def run(self, target, messages, prefix='', **kwargs):
        interval = kwargs.pop('interval', 0)
        for message in messages:
            if prefix:
                message = prefix + message
            await asyncio.sleep(interval)
            self.module.send('PRIVMSG', target=target, message=message)
