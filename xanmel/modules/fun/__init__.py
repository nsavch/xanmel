import random
import logging

from xanmel import Module, CommandContainer, ChatCommand

from .excuses import *

logger = logging.getLogger(__name__)


class FunCommands(CommandContainer):
    help_text = 'Fun commands'


class Excuse(ChatCommand):
    parent = FunCommands
    prefix = 'excuse'
    help_args = '[USERNAME]'
    help_text = 'Finds an excuse for you or USERNAME after a bad game round.'

    async def run(self, user, message, is_private=False):
        message = message.strip()
        if message:
            username = message
        else:
            username = user.name

        reply = '%s, %s %s. %s' % (
            username,
            random.choice(what_happened),
            random.choice(excuses),
            random.choice(endorses)
        )
        await user.reply(reply, is_private)


class FunModule(Module):
    def __init__(self, xanmel, config):
        super(FunModule, self).__init__(xanmel, config)
        xanmel.cmd_root.register_container(FunCommands(), '')
