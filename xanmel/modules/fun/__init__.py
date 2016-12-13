import random
import logging

from xanmel import Module, CommandContainer, ChatCommand

from .excuses import *

logger = logging.getLogger(__name__)


class FunCommands(CommandContainer):
    pass


class Excuse(ChatCommand):
    parent = FunCommands
    prefix = 'excuse'
    help_text = 'Finds an excuse for you after a bad game round'

    async def run(self, user, message, is_private=False):
        print(user, message, is_private)
        reply = '%s, %s %s. %s' % (
            user.name,
            random.choice(what_happened),
            random.choice(excuses),
            random.choice(endorses)
        )
        await user.reply(reply, is_private)


class FunModule(Module):
    def __init__(self, xanmel, config):
        super(FunModule, self).__init__(xanmel, config)
        xanmel.cmd_root.register_container(FunCommands, '')
