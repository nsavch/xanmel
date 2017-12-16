import logging
import fnmatch

import random

from xanmel import CommandContainer, ChatCommand
from xanmel.modules.xonotic.cointoss import CointosserState, CointosserException, CointosserAction

from .colors import Color
from .events import PlayerRatedMap

logger = logging.getLogger(__name__)


class XonCommands(CommandContainer):
    help_text = 'Commands for interaction with Xonotic server'
    include_confirmations = True


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
                return
        if not message.strip() and self.vote == -3:
            await user.private_reply('You can not vote --- without specifying a reason why you hate the map. Use '
                                     '"/--- [YOUR COMPLAINT]" instead')
            return
        player = rcon_server.players.players_by_number2[user.number2]
        rcon_server.map_voter.votes[user.number2] = {
            'vote': self.vote,
            'message': message,
            'player': player
        }
        PlayerRatedMap(rcon_server.module, server=rcon_server, player=player,
                       map_name=rcon_server.map_voter.map_name, vote=self.vote).fire()
        await user.private_reply('Your vote for the map %s was accepted: %s%s' % (
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


class Bet(ChatCommand):
    prefix = 'bet'
    parent = XonCommands
    help_args = '<PLAYER_ID> <AMOUNT>'
    help_text = 'Bet AMOUNT on PLAYER_ID'
    allowed_user_types = ['xonotic']

    async def run(self, user, message, is_private=True, root=None):
        rcon_server = self.parent.properties['rcon_server']
        if not rcon_server.config.get('enable_betting'):
            await user.reply(rcon_server.config['out_prefix'] + 'Betting is disabled on this server',
                             is_private=is_private)
            return
        args = message.strip().split(' ')
        if len(args) != 2:
            await user.private_reply(rcon_server.config['out_prefix'] + 'Usage: /bet <PLAYER_ID> <AMOUNT>')
            return
        args[0] = args[0].lstrip('#')
        if args[0] not in ('1', '2'):
            await user.private_reply('Player number must be either 1 or 2')
            return
        args[0] = int(args[0])
        try:
            args[1] = int(args[1])
        except ValueError:
            await user.private_reply('Betting amount should be an integer')
            return
        if args[1] <= 0:
            await user.private_reply('Amount should be positive')
            return
        if not rcon_server.betting_session_active:
            await user.private_reply(rcon_server.config[
                                         'out_prefix'] + 'Betting session is not active (either too early or too late). Sorry.')
            return
        if not user.number2:
            await user.private_reply('Sorry, your nickname cannot be identified. Try to  reconnect to the server.')
            return
        player = rcon_server.players.players_by_number2[user.number2]
        betting_target = rcon_server.active_duel_pair[args[0] - 1]
        if player in rcon_server.active_duel_pair and player != betting_target:
            await user.private_reply("You can't bet on your opponent. Bet on yourself and try as hard as you can.")
            return
        rcon_server.betting_session[player] = (betting_target, args[1])
        await user.private_reply('^2Your bet on^7 %s ^2is accepted^7: ^1%s^7' % (
            betting_target.nickname.decode('utf8'),
            args[1]
        ))


class Cointoss(ChatCommand):
    prefix = 'cointoss'
    parent = XonCommands
    help_args = '[OPERATION]'
    help_text = 'start a cointoss process.'
    allowed_user_types = ['xonotic']

    async def run(self, user, message, is_private=True, root=None):
        rcon_server = self.parent.properties['rcon_server']
        if not rcon_server.cointosser:
            await user.reply('Cointoss not enabled on this server')
            return
        message = message.lower().strip()
        if int(rcon_server.cvars['xanmel_wup_stage']) != 1:
            await user.reply('Cointoss can only be performed during warmup stage. vcall restart or endmatch.',
                             is_private=False)
            return
        if not rcon_server.active_duel_pair:
            await user.reply('Exactly two players must join the game before cointoss can be performed.',
                             is_private=False)
            return
        if rcon_server.cointosser.state != CointosserState.PENDING:
            await user.reply(
                'A cointoss is already activated. Finish the games or /cointoss stop before starting a new one',
                is_private=False)
            return
        if message in ('heads', 'tails'):
            result = random.choice(('heads', 'tails'))
            await user.public_reply('{}!'.format(result.upper()))
            rcon_server.cointosser.reset()
            this_player = other_player = None
            for i in rcon_server.active_duel_pair:
                if i.nickname == user.unique_id():
                    this_player = i
                else:
                    other_player = i
            assert this_player and other_player, (this_player, other_player)
            if message == result:
                await user.public_reply('{} wins the cointoss!'.format(this_player.nickname.decode('utf8')))
                rcon_server.cointosser.activate((this_player, other_player))
            else:
                await user.public_reply('{} wins the cointoss!'.format(other_player.nickname.decode('utf8')))
                rcon_server.cointosser.activate((other_player, this_player))
        await user.public_reply(rcon_server.cointosser.format_status())


class PickDropBase(ChatCommand):
    help_args = '<MAP_NAME>'
    allowed_user_types = ['xonotic']
    action = None

    async def run(self, user, message, is_private=True, root=None):
        rcon_server = self.parent.properties['rcon_server']
        if not rcon_server.cointosser:
            await user.reply('Cointoss not enabled on this server')
            return
        if rcon_server.cointosser.state != CointosserState.ACTIVE:
            await user.reply(
                'Cointoss is not activated. /cointoss heads|tails to start it.',
                is_private=False)
            return
        map_name = message.lower().strip()
        this_player = None
        for i in rcon_server.active_duel_pair:
            if i.nickname == user.unique_id():
                this_player = i
        assert this_player, rcon_server.active_duel_pair
        try:
            rcon_server.cointosser.validate_action(this_player, self.action, map_name)
        except CointosserException as e:
            await user.public_reply(str(e))
            return

        async def __yes_cb():
            rcon_server.cointosser.do_action(this_player, self.action, map_name)
            await user.public_reply(rcon_server.cointosser.format_status())

        async def __no_cb():
            await user.public_reply('Action canceled!')
            await user.public_reply(rcon_server.cointosser.format_status())
        await self.parent.confirmations.ask(user, 'Are you sure to {} a map {}?'.format(
            self.action.value.lower(),
            rcon_server.cointosser.clean_map_name(map_name),
        ), __yes_cb, __no_cb)


class Pick(PickDropBase):
    parent = XonCommands
    prefix = 'pick'
    help_text = 'Pick a map to play on.'
    action = CointosserAction.P


class Drop(PickDropBase):
    parent = XonCommands
    prefix = 'drop'
    help_text = 'Drop a map to exclude it from the map pool.'
    action = CointosserAction.D
