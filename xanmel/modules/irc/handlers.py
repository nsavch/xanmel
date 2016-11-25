import logging

from xanmel.base_classes import Handler

logger = logging.getLogger(__name__)


class MentionMessageHandler(Handler):
    events = ['xanmel.modules.irc.events.MentionMessage']

    async def handle(self, event):
        await self.run_action('xanmel.modules.irc.actions.ChannelMessage',
                              message="%s: You said '%s'" % (event.properties['nick'],
                                                             event.properties['message']))
