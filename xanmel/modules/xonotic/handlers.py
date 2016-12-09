from xanmel import Handler

from .colors import Color
from .events import *
from xanmel.modules.irc.actions import ChannelMessage


class ChatMessageHandler(Handler):
    events = [ChatMessage]

    async def handle(self, event):
        await self.run_action(ChannelMessage,
                              message=Color.dp_to_irc(event.properties['message']).decode('utf8'))


class GameStartedHandler(Handler):
    events = [GameStarted]

    async def handle(self, event):
        message = 'Playing \00310%(gametype)s\x0f on \00304%(map)s\x0f (%(max)s free slots); join now: \2xonotic +connect %(sv_ip)s:%(sv_port)s' % {
            'gametype': event.properties['gt'],
            'map': event.properties['map'],
            'max': event.properties['server'].players.max - event.properties['server'].players.current,
            'sv_ip': event.properties['server'].config['public_ip'],
            'sv_port': event.properties['server'].config['public_port']
        }
        await self.run_action(ChannelMessage, message=message)


class JoinHandler(Handler):
    events = [Join]

    async def handle(self, event):
        message = '\00309+ join\x0f: %(name)s \00304%(map)s\x0f [\00304%(current)s\x0f/\00304%(max)s\x0f]' % {
            'name': Color.dp_to_irc(event.properties['player'].nickname).decode('utf8'),
            'map': event.properties['server'].current_map,
            'current': event.properties['current'],
            'max': event.properties['server'].players.max
        }
        await self.run_action(ChannelMessage, message=message)


class PartHandler(Handler):
    events = [Part]

    async def handle(self, event):
        message = '\00304- part\x0f: %(name)s \00304%(map)s\x0f [\00304%(current)s\x0f/\00304%(max)s\x0f]' % {
            'name': Color.dp_to_irc(event.properties['player'].nickname).decode('utf8'),
            'map': event.properties['server'].current_map,
            'current': event.properties['current'],
            'max': event.properties['server'].players.max
        }
        await self.run_action(ChannelMessage, message=message)


class NameChangeHandler(Handler):
    events = [NameChange]

    async def handle(self, event):
        message = '\00312*\x0f %(name)s is known as %(new_name)s' % {
            'name': Color.dp_to_irc(event.properties['old_nickname']).decode('utf8'),
            'new_name': Color.dp_to_irc(event.properties['player'].nickname).decode('utf8')
        }
        await self.run_action(ChannelMessage, message=message)


class GameEndedHandler(Handler):
    events = [GameEnded]

    async def handle(self, event):
        pass
