from xanmel import Event


class ConnectedAndJoined(Event):
    def __str__(self):
        return 'IRC Connected'


class Disconnected(Event):
    def __str__(self):
        return 'IRC Disconnected'


class ChannelMessage(Event):
    log = False

    def __str__(self):
        return 'Channel message from %s' % self.properties.get('nick', 'unknown')


class PrivateMessage(Event):
    def __str__(self):
        return 'Private message from %s: %s' % (self.properties.get('nick', 'unknown'),
                                                self.properties.get('message'))


class MentionMessage(Event):
    def __str__(self):
        return 'Mention message from %s: %s' % (self.properties.get('nick', 'unknown'),
                                                self.properties.get('message'))
