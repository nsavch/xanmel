from xanmel import Handler

from .colors import Color


class ChatMessageHandler(Handler):
    events = ['xanmel.modules.xonotic.events.ChatMessage']

    async def handle(self, event):
        await self.run_action('xanmel.modules.irc.actions.ChannelMessage',
                              message=Color.dp_to_irc(event.properties['message']).decode('utf8'))


class GameStartedHandler(Handler):
    events = ['xanmel.modules.xonotic.events.GamesStarted']

    async def handle(self, event):
        pass
