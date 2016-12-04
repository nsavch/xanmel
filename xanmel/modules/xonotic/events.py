from xanmel.base_classes import Event


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
