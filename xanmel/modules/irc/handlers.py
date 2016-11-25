import logging

from xanmel.base_classes import Handler

logger = logging.getLogger(__name__)


class MentionMessageHandler(Handler):
    events = ['xanmel.modules.irc.events.MentionMessage']

    def handle(self, event):
        pass
