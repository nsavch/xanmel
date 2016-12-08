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
        print(event.properties['server'].config)
        message = 'Playing \00310%(gametype)s\x0f on \00304%(map)s\x0f (%(max)s free slots); join now: \2xonotic +connect %(sv_ip)s:%(sv_port)s' % {
            'gametype': event.properties['gt'],
            'map': event.properties['map'],
            'max': event.properties['server'].players.max - event.properties['server'].players.current,
            'sv_ip': event.properties['server'].config['public_ip'],
            'sv_port': event.properties['server'].config['public_port']
        }
        await self.run_action('xanmel.modules.irc.actions.ChannelMessage',
                              message=message)
