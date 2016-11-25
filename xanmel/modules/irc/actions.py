from xanmel.base_classes import Action


class ChannelMessage(Action):
    def run(self):
        self.module.client.send('PRIVMSG', target=self.module.config['channel'],
                                message=self.properties['message'])


class PrivateMessage(Action):
    def run(self):
        self.module.client.send('PRIVMSG', target=self.properties['target'],
                                message=self.properties['message'])
