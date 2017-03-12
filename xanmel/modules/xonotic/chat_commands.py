import logging
import fnmatch

from xanmel import CommandContainer, ChatCommand

from .colors import Color

logger = logging.getLogger(__name__)


class XonCommands(CommandContainer):
    help_text = 'Commands for interaction with Xonotic server'


class VoteBaseMixin:
    allowed_user_types = ['xonotic']

    async def run(self, user, message, is_private=True, root=None):
        if not user.number2:
            await user.private_reply('Sorry, your nickname cannot be identified. Try to use another nickname, '
                                     'or reconnect to the server.')
            return
        rcon_server = self.parent.properties['rcon_server']
        if not rcon_server.map_voter.map_name:
            await user.private_reply('Map voter is not initialized, please try later')
            return
        if user.number2 in rcon_server.map_voter.votes:
            old_vote = rcon_server.map_voter.votes[user.number2]
            if old_vote['vote'] == self.vote and old_vote['message'] == message:
                await user.private_reply('You have already voted this round. Enough. You can change your vote though.')
        rcon_server.map_voter.votes[user.number2] = {
            'vote': self.vote,
            'message': message,
            'player': rcon_server.players.players_by_number2[user.number2]
        }
        await user.private_reply('Your vote for map %s is accepted: %s%s' % (
            rcon_server.map_voter.map_name,
            self.prefix,
            message
        ))


class VotePlus(VoteBaseMixin, ChatCommand):
    prefix = '+'
    vote = 1
    parent = XonCommands


class VotePlusPlus(VoteBaseMixin, ChatCommand):
    prefix = '++'
    vote = 2
    parent = XonCommands


class VotePlusPlusPlus(VoteBaseMixin, ChatCommand):
    prefix = '+++'
    vote = 3
    parent = XonCommands


class VoteMinus(VoteBaseMixin, ChatCommand):
    prefix = '-'
    vote = -1
    parent = XonCommands


class VoteMinusMinus(VoteBaseMixin, ChatCommand):
    prefix = '--'
    vote = -2
    parent = XonCommands


class VoteMinusMinusMinus(VoteBaseMixin, ChatCommand):
    prefix = '---'
    vote = -3
    parent = XonCommands


class Who(ChatCommand):
    prefix = 'who'
    parent = XonCommands
    help_text = 'Lists players connected to the server (one-line format)'
    allowed_user_types = ['irc']

    async def run(self, user, message, is_private=True, root=None):
        rcon_server = self.parent.properties['rcon_server']
        logger.debug(rcon_server.players.players_by_number1)
        logger.debug(rcon_server.players.players_by_number2)
        if rcon_server.players.current == 0:
            reply = 'Server is empty'
        else:
            player_names = []
            for player in rcon_server.players.players_by_number1.values():
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

    async def run(self, user, message, is_private=True, root=None):
        rcon_server = self.parent.properties['rcon_server']
        if not rcon_server.map_list:
            await user.reply(rcon_server.config['out_prefix'] + 'Map List not initialized', is_private)
            return
        pattern = message.strip().split(' ')[0].strip()
        pattern = '*%s*' % pattern.lower()
        res = []
        for i in rcon_server.map_list:
            if fnmatch.fnmatch(i.lower(), pattern):
                res.append(i)
        if not res:
            reply = 'No maps match.'
        else:
            reply = '[%s/%s]: %s' % (len(res), len(rcon_server.map_list), ', '.join(res[:10]))
            if len(res) > 10:
                reply += ' (%s more maps skipped)' % (len(res) - 10)
        await user.reply(rcon_server.config['out_prefix'] + reply, is_private)
