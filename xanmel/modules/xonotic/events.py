from xanmel import Event


class ServerConnect(Event):
    pass


class ServerDisconnect(Event):
    pass


class Join(Event):
    pass


class Part(Event):
    pass


class GameStarted(Event):
    pass


class GameEnded(Event):
    pass


class NameChange(Event):
    pass


class ChatMessage(Event):
    pass
