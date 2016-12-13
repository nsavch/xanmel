import logging

from xanmel import CommandContainer, ChatCommand

from .colors import Color

logger = logging.getLogger(__name__)


class XonCommands(CommandContainer):
    help_text = 'Commands for interaction with a Xonotic server'


class Who(ChatCommand):
    prefix = 'who'
    parent = XonCommands
    help_text = 'Lists players connected to the server (one-line format)'

    async def run(self, user, message, is_private=True):
        rcon_server = self.parent.properties['rcon_server']
        logger.debug(rcon_server.players.players_by_number1)
        logger.debug(rcon_server.players.players_by_number2)
        if rcon_server.players.current == 0:
            reply = 'Server is empty'
        else:
            player_names = []
            for player in rcon_server.players.players_by_number2.values():
                if not player.is_bot:
                    player_names.append(Color.dp_to_irc(player.nickname).decode('utf8'))
            reply = ' | '.join(player_names)
            bots = rcon_server.players.bots
            if len(bots) > 0:
                reply += ' | %s bots' % len(bots)

        await user.reply(rcon_server.config['out_prefix'] + reply, is_private)
