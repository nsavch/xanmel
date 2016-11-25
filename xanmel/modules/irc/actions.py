from xanmel.base_classes import Action


class ChannelMessage(Action):
    async def run(self, message, **kwargs):
        self.module.client.send('PRIVMSG', target=self.module.config['channel'], message=message)


class PrivateMessage(Action):
    async def run(self, target, message, **kwargs):
        self.module.client.send('PRIVMSG', target=target, message=message)
