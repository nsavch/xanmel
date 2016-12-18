import logging
import fnmatch

from xanmel import CommandContainer, ChatCommand

from .colors import Color

logger = logging.getLogger(__name__)


class XonCommands(CommandContainer):
    help_text = 'Commands for interaction with a Xonotic server'


class Who(ChatCommand):
    prefix = 'who'
    parent = XonCommands
    help_text = 'Lists players connected to the server (one-line format)'
    allowed_user_types = ['irc']

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


class Maps(ChatCommand):
    prefix = 'maps'
    parent = XonCommands
    help_args = '[PATTERN]'
    help_text = 'Lists maps matching a glob-style PATTERN. If PATTERN not supplied output list of all maps. In ' \
                'non-private mode outputs only first 10 matches. '

    async def run(self, user, message, is_private=True):
        rcon_server = self.parent.properties['rcon_server']
        if not rcon_server.map_list:
            await user.reply(rcon_server.config['out_prefix'] + 'Map List not initialized', is_private)
            return
        pattern = message.strip().split(' ')[0].strip()
        pattern = '*%s*' % pattern
        res = []
        for i in rcon_server.map_list:
            if fnmatch.fnmatch(i, pattern):
                res.append(i)
        reply = ['[%s/%s]: %s' % (len(res), len(rcon_server.map_list), ', '.join(res[:10]))]
        if len(res) > 10:
            reply[0] += ' (%s more maps skipped)' % (len(rcon_server.map_list) - 10)
        for i in reply:
            await user.reply(rcon_server.config['out_prefix'] + i, is_private)




