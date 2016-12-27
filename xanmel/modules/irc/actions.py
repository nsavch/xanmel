from xanmel import Action


class ChannelMessage(Action):
    async def run(self, message, prefix='', **kwargs):
        if prefix:
            message = prefix + message
        self.module.send('PRIVMSG', target=self.module.config['channel'], message=message)


class ChannelMessages(Action):
    async def run(self, messages, prefix='', **kwargs):
        for message in messages:
            if prefix:
                message = prefix + message
            self.module.send('PRIVMSG', target=self.module.config['channel'], message=message)


class PrivateMessage(Action):
    async def run(self, target, message, prefix='', **kwargs):
        if prefix:
            message = prefix + message
        self.module.send('PRIVMSG', target=target, message=message)


class PrivateMessages(Action):
    async def run(self, target, messages, prefix='', **kwargs):
        for message in messages:
            if prefix:
                message = prefix + message
            self.module.send('PRIVMSG', target=target, message=message)
