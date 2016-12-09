import logging

from xanmel import Handler
from .events import *
from .actions import ChannelMessage

logger = logging.getLogger(__name__)


class MentionMessageHandler(Handler):
    events = [MentionMessage]

    async def handle(self, event):
        await self.run_action(ChannelMessage,
                              message="%s: You said '%s'" % (event.properties['nick'],
                                                             event.properties['message']))
