from xanmel import Event


class ConnectedAndJoined(Event):
    pass


class Disconnected(Event):
    pass


class ChannelMessage(Event):
    pass


class PrivateMessage(Event):
    pass


class MentionMessage(Event):
    pass
