import logging

from xanmel import Handler
from .events import *
from .actions import ChannelMessage

logger = logging.getLogger(__name__)


class MentionMessageHandler(Handler):
    events = [MentionMessage]

    async def handle(self, event):
        await self.module.xanmel.cmd_root.run(event.properties['chat_user'],
                                              event.properties['message'])


class PrivateMessageHandler(Handler):
    events = [PrivateMessage]

    async def handle(self, event):
        await self.module.xanmel.cmd_root.run(event.properties['chat_user'],
                                              event.properties['message'],
                                              is_private=True)
