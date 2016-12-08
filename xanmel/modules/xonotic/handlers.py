from xanmel import Handler

from .colors import Color


class ChatMessageHandler(Handler):
    events = ['xanmel.modules.xonotic.events.ChatMessage']

    async def handle(self, event):
        await self.run_action('xanmel.modules.irc.actions.ChannelMessage',
                              message=Color.dp_to_irc(event.properties['message']).decode('utf8'))


class GameStartedHandler(Handler):
    events = ['xanmel.modules.xonotic.events.GameStarted']

    async def handle(self, event):
        message = 'Playing \00310%(gametype)s\x0f on \00304%(map)s\x0f (%(max)s free slots); join now: \2xonotic +connect %(sv_ip)s:%(sv_port)s' % {
            'gametype': event.properties['gt'],
            'map': event.properties['map'],
            'max': event.properties['server'].players.max - event.properties['server'].players.current,
            'sv_ip': event.properties['server'].config['public_ip'],
            'sv_port': event.properties['server'].config['public_port']
        }
        await self.run_action('xanmel.modules.irc.actions.ChannelMessage', message=message)


class JoinHandler(Handler):
    events = ['xanmel.modules.xonotic.events.Join']

    async def handle(self, event):
        message = '\00309+ join\x0f: %(name)s \00304%(map)s\x0f [\00304%(current)s\x0f/\00304%(max)s\x0f]' % {
            'name': Color.dp_to_irc(event.properties['player'].nickname).decode('utf8'),
            'map': event.properties['server'].current_map,
            'current': event.properties['current'],
            'max': event.properties['server'].players.max
        }
        await self.run_action('xanmel.modules.irc.actions.ChannelMessage', message=message)


class PartHandler(Handler):
    events = ['xanmel.modules.xonotic.events.Part']

    async def handle(self, event):
        message = '\00304- part\x0f: %(name)s \00304%(map)s\x0f [\00304%(current)s\x0f/\00304%(max)s\x0f]' % {
            'name': Color.dp_to_irc(event.properties['player'].nickname).decode('utf8'),
            'map': event.properties['server'].current_map,
            'current': event.properties['current'],
            'max': event.properties['server'].players.max
        }
        await self.run_action('xanmel.modules.irc.actions.ChannelMessage', message=message)
