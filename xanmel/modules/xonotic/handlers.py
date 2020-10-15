import asyncio
import logging
import time
import uuid

from decimal import Decimal
from peewee import fn

import xanmel.modules.irc.events as irc_events
from xanmel import Handler
from xanmel import current_time
from xanmel.modules.irc.actions import ChannelMessage, ChannelMessages
from xanmel.modules.xonotic.cointoss import CointosserState
from xanmel.modules.xonotic.models import CalledVote, MapRating, Map, AccountTransaction, PlayerAccount, CTSRecord
from .chat_user import XonoticChatUser
from .events import *
from .rcon_log import GAME_TYPES

logger = logging.getLogger(__name__)


class ServerConnectedBase(Handler):
    async def report(self, server):
        msg = '\00303Xonotic Server Connected:\x0f \00312%(hostname)s\x0f; join now: \2xonotic +connect %(sv_ip)s:%(sv_port)s' % {
            'hostname': server.host,
            'sv_ip': server.config['public_ip'],
            'sv_port': server.config['public_port']
        }
        await self.run_action(ChannelMessage, message=msg, prefix=server.config['out_prefix'])


class ServerConnectHandler(ServerConnectedBase):
    events = [ServerConnect]

    async def handle(self, event):
        await self.report(event.properties['server'])


class ServerDisconnectHandler(Handler):
    events = [ServerDisconnect]

    async def handle(self, event):
        hostname = event.properties['server'].host
        await self.run_action(ChannelMessage,
                              message='\00304Xonotic Server Disconnected:\x0f \00312%s\x0f' % hostname,
                              prefix=event.properties['server'].config['out_prefix'])


class ChatMessageHandler(Handler):
    events = [ChatMessage]

    async def handle(self, event):
        server = event.properties['server']
        msg = event.properties['message']
        nicknames = sorted([i.nickname for i in server.players.players_by_number2.values()],
                           key=lambda x: len(x), reverse=True)
        user = None
        message = None
        for nickname in nicknames:
            prefixes = [b'^7%s^7: ', b'^3%s^7: ', b'^0(^7%s^0) ^7', b'^0(^3%s^0) ^7']

            for i in prefixes:
                prefix = i % nickname
                if msg.startswith(prefix):
                    user = XonoticChatUser(self.module, Color.dp_to_none(nickname).decode('utf8'),
                                           raw_nickname=nickname,
                                           rcon_server=server)
                    message = Color.dp_to_none(msg[len(prefix):]).decode('utf8')
                    break
            if message is not None:
                break
        message_is_cmd = False
        if user:
            if message.startswith(user.botnick + ': '):
                message_is_cmd = True
                message = message[len(user.botnick) + 1:]
            elif message.startswith('/'):
                message_is_cmd = True
                message = message[1:]
        if not user or not message_is_cmd:
            if server.forward_chat_to_other_servers:
                for other_server in self.module.servers:
                    if (other_server.config['unique_id'] in server.forward_chat_to_other_servers) and (not other_server.disabled):
                        other_server.say([msg.decode('utf8')],
                                         nick=server.config.get('forward_prefix', server.config.get('out_prefix')))
            await self.run_action(ChannelMessage,
                                  message=Color.dp_to_irc(event.properties['message']).decode('utf8'),
                                  prefix=event.properties['server'].config['out_prefix'])
        else:
            await server.local_cmd_root.run(user, message, is_private=False)


class MapChangeHandler(Handler):
    events = [MapChange]

    async def handle(self, event):
        server = event.properties['server']
        await server.map_voter.store(
            event.properties['new_map'])  # what if someone votes while this is executing? Oh shi...


class RatingReportHandler(Handler):
    events = [MapChange]

    async def handle(self, event):
        server = event.properties['server']
        map_name = server.status['map']
        db = server.module.xanmel.db
        if not db.is_up:
            return
        await asyncio.sleep(10)
        map, _ = await db.mgr.get_or_create(Map, server=server.server_db_obj, name=map_name)
        result = await db.mgr.execute(
            MapRating.select(fn.Sum(MapRating.vote).alias('rating'),
                             fn.Count(MapRating.id).alias('total')).where(MapRating.map == map))
        total_votes = result[0].total
        rating = result[0].rating
        if total_votes == 0 or rating is None:
            message = '^3%(map_name)s ^7has not yet been rated - Use ^7/^2+++^7,^2++^7,^2+^7,^1-^7,^1--^7,^1--- ^7to rate the map.'
        else:
            if rating >= 0:
                message = '^3%(map_name)s ^7has ^2%(rating)s ^7points. ^5[%(total_votes)s votes]^7 - Use ^7/^2+++^7,^2++^7,^2+^7,^1-^7,^1--^7,^1--- ^7to rate the map.'
            else:
                message = '^3%(map_name)s ^7has ^1%(rating)s ^7points. ^5[%(total_votes)s votes]^7 - Use ^7/^2+++^7,^2++^7,^2+^7,^1-^7,^1--^7,^1--- ^7to rate the map.'
        msg_args = {'map_name': map_name, 'rating': rating, 'total_votes': total_votes}
        in_game_message = message % msg_args
        server.say(in_game_message)


class PlayerRatedMapHandler(Handler):
    events = [PlayerRatedMap]

    async def handle(self, event):
        msg = '\00303*\x0f %(player_name)s rated map \00304%(map_name)s\x0f: \00312%(vote)s\x0f'
        await self.run_action(ChannelMessage, message=msg % {
            'player_name': Color.dp_to_irc(event.properties['player'].nickname).decode('utf8'),
            'map_name': event.properties['map_name'],
            'vote': event.properties['vote']
        }, prefix=event.properties['server'].config['out_prefix'])


class GameStartedHandler(Handler):
    events = [GameStarted]

    async def handle(self, event):
        event.properties['server'].send('fraglimit')
        if event.properties['server'].players.current == 0:
            return
        message = 'Playing \00310%(gametype)s\x0f on \00304%(map)s\x0f [%(current)s/%(max)s]; join now: \2xonotic +connect %(sv_ip)s:%(sv_port)s' % {
            'gametype': GAME_TYPES[event.properties['gt']],
            'map': event.properties['map'],
            'current': event.properties['server'].players.current,
            'max': event.properties['server'].players.max,
            'sv_ip': event.properties['server'].config['public_ip'],
            'sv_port': event.properties['server'].config['public_port']
        }
        await self.run_action(ChannelMessage, message=message,
                              prefix=event.properties['server'].config['out_prefix'])
        await event.properties['server'].update_server_stats()


class JoinHandler(Handler):
    events = [Join]

    async def handle(self, event):
        player = event.properties['player']
        server = event.properties['server']

        await player.get_elo()
        self.module.xanmel.loop.create_task(player.update_identification())
        if not player.really_joined:
            return

        mode_stats = player.get_mode_stats()
        server_rank = player.get_server_rank()
        if server_rank:
            server_rank_fmt = ' [server rank: %s/%s] ' % server_rank
        else:
            server_rank_fmt = ' '

        formatted_mode_stats = '\00303{mode}\x0f: \00312{stats}'.format(
            mode=server.stats_mode,
            stats='\x0f, \00312'.join(['{}: {}'.format(*i) for i in mode_stats])
        )

        message = '\00309+ join\x0f: %(name)s \00312[%(rank)s]\x0f\00306%(server_rank)s\x0f\00303%(country)s\x0f \00304%(map)s\x0f [\00304%(current)s\x0f/\00304%(max)s\x0f]' % {
            'name': Color.dp_to_irc(event.properties['player'].nickname).decode('utf8'),
            'map': server.current_map,
            'current': server.players.current,
            'max': server.players.max,
            'country': player.country,
            'rank': formatted_mode_stats,
            'server_rank': server_rank_fmt
        }

        if server_rank:
            server_rank_game_fmt = ' ^3server:%s/%s^x4F0' % server_rank
        else:
            server_rank_game_fmt = ''

        if mode_stats:
            formatted_mode_stats = '^2{mode}^7: {stats}'.format(
                mode=server.stats_mode,
                stats=', '.join(['^2{}^7: ^3{}^7'.format(*i) for i in mode_stats])
            )
            in_game_message = '^2 +join:^7 %(name)s ^2%(country)s ^x4F0[%(mode_stats)s%(server_rank)s]^7' % {
                'name': event.properties['player'].nickname.decode('utf8'),
                'mode_stats': formatted_mode_stats,
                'country': player.country,
                'server_rank': server_rank_game_fmt
            }
        else:
            in_game_message = '^2+join:^7 %(name)s ^2%(country)s' % {
                'name': event.properties['player'].nickname.decode('utf8'),
                'country': player.country
            }
        if event.properties['player'].account and server.config.get('enable_betting'):
            b = event.properties['player'].account.balance
            if b > 0:
                in_game_message += ' [^3balance:^7 ^2%s^7]' % b
            else:
                in_game_message += ' [^3balance:^7 ^1%s^7]' % b
        if server.display_in_game_info:
            server.say(in_game_message)
        await self.run_action(ChannelMessage, message=message,
                              prefix=event.properties['server'].config['out_prefix'])
        if server.forward_chat_to_other_servers:
            for other_server in self.module.servers:
                if (other_server.config['unique_id'] in server.forward_chat_to_other_servers) and (not other_server.disabled):
                    other_server.say([in_game_message],
                                     nick=server.config.get('forward_prefix', server.config.get('out_prefix')))


class NewDuelHandler(Handler):
    events = [DuelPairFormed]

    async def handle(self, event):
        def __get_elo(player):
            if player.elo_basic and player.elo_basic.get('duel'):
                return player.elo_basic['duel']

        server = event.properties['server']
        if not server.config.get('enable_betting'):
            return
        elo1 = __get_elo(event.properties['player1'])
        elo2 = __get_elo(event.properties['player2'])
        if elo1 and elo2:
            odds1 = 1 + (elo2 / elo1) ** 2
            odds2 = 1 + (elo1 / elo2) ** 2
        else:
            odds1 = odds2 = 1.05
        server.betting_odds = {event.properties['player1']: odds1, event.properties['player2']: odds2}
        announcement = '%s ^2(%.2f)^7 ^1vs^7 %s ^2(%.2f)^7 Bet with "^2/bet #1 100^7" or "^2/bet #2 100^7"' % (
            event.properties['player1'].nickname.decode('utf8'),
            odds1,
            event.properties['player2'].nickname.decode('utf8'),
            odds2)
        server.say(announcement)
        session_id = uuid.uuid4()
        server.betting_session = {}
        server.betting_session_id = session_id
        server.betting_session_active = True
        await asyncio.sleep(30)
        if server.betting_session_id == session_id and server.betting_session_active:
            server.betting_session_active = False
        server.say('^2Betting session closed!^7')


class DuelFailureHandler(Handler):
    events = [DuelEndedPrematurely]

    async def handle(self, event):
        server = event.properties['server']
        if not server.config.get('enable_betting'):
            return
        server.say('^3Duel ended with no result.^7')
        server.betting_odds = None
        server.betting_session = None
        server.betting_session_active = False
        server.betting_session_id = None


class DuelSuccessHandler(Handler):
    events = [GameEnded]

    async def handle(self, event):
        if not event.properties['players']:
            return
        server = event.properties['server']
        if not server.config.get('enable_betting'):
            return
        if not server.active_duel_pair:
            return
        if not server.betting_session:
            return
        result = {}
        scores = []
        for player in event.properties['players']:
            if player['team_id']:
                if player['number1'] not in [i.number1 for i in server.active_duel_pair]:
                    logger.info('%s was not an active dueller but is present in the final scores!', player['nickname'])
                result[player['score']] = server.players.players_by_number1[player['number1']]
                scores.append(player['score'])
        if len(result) != 2:
            logger.info('A duel with %s players?', len(result))
            return
        ordering = [result[i] for i in sorted(result.keys(), reverse=True)]
        if max(scores) < server.config.get('betting_min_frag_number', 5) or scores[0] == scores[1]:
            logger.info('Not enough score or same score for both players')
            return
        announcement = '%s ^2wins^7, %s ^2loses^7!' % (ordering[0].nickname.decode('utf8'),
                                                       ordering[1].nickname.decode('utf8'))
        server.say(announcement)
        winning_odds = server.betting_odds[ordering[0]]
        for player, bet in server.betting_session.items():
            if bet[0] == ordering[0]:
                change = winning_odds * bet[1] - bet[1]
                message = '%s ^2won %.2f!^7' % (player.nickname.decode('utf8'), change)
            else:
                change = - bet[1]
                message = '%s ^1lost %.2f!^7' % (player.nickname.decode('utf8'), -change)
            change = Decimal("%.2f" % change)
            server.say(message)
            account = await server.db.mgr.get(PlayerAccount, player=player.player_db_obj)
            await server.db.mgr.create(AccountTransaction, account=account, change=change,
                                       description='Betting: %s vs %s' % (
                                           Color.dp_to_none(ordering[0].nickname).decode('utf8'),
                                           Color.dp_to_none(ordering[1].nickname).decode('utf8')
                                       ))
            account.balance += change
            await server.db.mgr.update(account)

        server.betting_odds = None
        server.betting_session = None
        server.betting_session_active = False
        server.betting_session_id = None


class NewPlayerActiveHandler(Handler):
    events = [NewPlayerActive]

    async def handle(self, event):
        server = event.properties['server']
        if server.current_gt != 'dm':
            return
        if server.config.get('dynamic_frag_limit'):
            await server.dyn_fraglimit_lock.acquire()
            try:
                server.send('fraglimit')
                await asyncio.sleep(1)
                for trigger_player_num, new_fraglimit in reversed(server.config['dynamic_frag_limit']):
                    logger.debug('Dynamic frag limit %s, current players %s',
                                 trigger_player_num, len(server.players.active))
                    if len(server.players.active) > trigger_player_num and new_fraglimit > int(
                            server.cvars.get('fraglimit', 0)):
                        server.send('fraglimit %d' % new_fraglimit)
                        await self.run_action(
                            ChannelMessage,
                            message='\00303Frag limit increased to \x0f\00304%d\x0f\00303 because there are more than \x0f\00304%d\x0f\00303 players\x0f' % (
                                new_fraglimit, trigger_player_num))
                        in_game_message = '^2Frag limit increased to ^3%d^2 because there are more than ^3%d^2 players^7' % (
                            new_fraglimit, trigger_player_num)
                        server.say(in_game_message)
                        await asyncio.sleep(1)
                        server.send('fraglimit')
                        break
            finally:
                server.dyn_fraglimit_lock.release()


class PartHandler(Handler):
    events = [Part]

    async def handle(self, event):
        message = '\00304- part\x0f: %(name)s \00303%(country)s\x0f \00304%(map)s\x0f [\00304%(current)s\x0f/\00304%(max)s\x0f]' % {
            'name': Color.dp_to_irc(event.properties['player'].nickname).decode('utf8'),
            'map': event.properties['server'].current_map,
            'current': event.properties['server'].players.current,
            'max': event.properties['server'].players.max,
            'country': event.properties['player'].country
        }
        await self.run_action(ChannelMessage, message=message,
                              prefix=event.properties['server'].config['out_prefix'])
        server = event.properties['server']
        if server.forward_chat_to_other_servers:
            in_game_message = '^1+part:^7 %(name)s' % {
                'name': event.properties['player'].nickname.decode('utf8'),
            }
            for other_server in self.module.servers:
                if (other_server.config['unique_id'] in server.forward_chat_to_other_servers) and (not other_server.disabled):
                    other_server.say([in_game_message],
                                     nick=server.config.get('forward_prefix', server.config.get('out_prefix')))


class NameChangeHandler(Handler):
    events = [NameChange]

    async def handle(self, event):
        message = '\00312*\x0f %(name)s is known as %(new_name)s' % {
            'name': Color.dp_to_irc(event.properties['old_nickname']).decode('utf8'),
            'new_name': Color.dp_to_irc(event.properties['player'].nickname).decode('utf8')
        }
        await self.run_action(ChannelMessage, message=message,
                              prefix=event.properties['server'].config['out_prefix'])
        server = event.properties['server']
        if server.forward_chat_to_other_servers:
            in_game_message = '^1*^7 %(name)s ^5is known as^7 %(new_name)s' % {
                'name': event.properties['old_nickname'].decode('utf8'),
                'new_name': event.properties['player'].nickname.decode('utf8')
            }
            for other_server in self.module.servers:
                if (other_server.config['unique_id'] in server.forward_chat_to_other_servers) and (not other_server.disabled):
                    other_server.say([in_game_message],
                                     nick=server.config.get('forward_prefix', server.config.get('out_prefix')))


class GameEndedHandler(Handler):
    events = [GameEnded]

    def __team_scores(self, teams, team_sort_column):
        res = []
        for i in teams:
            res.append(
                '%(color)s%(score)s\x0f' % {
                    'color': Color(code=i['color'], bright=True).irc().decode('utf8'),
                    'score': i[team_sort_column]
                }
            )
        return res

    def __pad(self, s, l):
        sl = len(s)
        if sl >= l:
            return s
        else:
            return ' ' * (l - sl) + s

    def __output_player_table(self, color, header, table):
        line0 = Color(code=color, bright=True).irc().decode('utf8')
        for i in header:
            line0 += ' | ' + i.upper()
        line0 += '\x0f'
        yield line0
        for row in table:
            line = ''
            for ix, col in enumerate(row[:-1]):
                line += ' | ' + self.__pad(str(col), len(header[ix]))
            line += ' | ' + row[-1]
            yield line

    def __format_time(self, seconds):
        if seconds < 60:
            return '%d sec' % seconds
        else:
            return '%d:%02d' % (seconds // 60, seconds % 60)

    async def handle(self, event):
        if not event.properties['players']:
            return
        messages = ['%(gametype)s on \00304%(map)s\017 ended (%(duration)s)' % {
            'gametype': GAME_TYPES[event.properties['gt']],
            'map': event.properties['map'],
            'duration': self.__format_time(event.properties['game_duration'])
        }]
        player_header = []
        for i in event.properties['server'].config['stats_ordering']:
            if i in event.properties['player_header']:
                player_header.append(i)
        for i in event.properties['player_header']:
            if i and i not in player_header and i not in event.properties['server'].config['stats_blacklist']:
                player_header.append(i)
        player_header.append(' elo')
        player_header.append('player')
        if event.properties['gt'] == 'dm' and len([i for i in event.properties['players'] if i['team_id']]) == 2:
            elo_type = 'duel'
        else:
            elo_type = event.properties['gt'].lower()
        if event.properties['teams']:
            messages.append(
                'Team scores: %s' % ':'.join(self.__team_scores(event.properties['teams'],
                                                                event.properties['team_sort_column'])))
            for i in event.properties['teams']:
                table = []
                for player in event.properties['players']:
                    if player['team_id'] == i['team_id']:
                        row = []
                        for col in player_header[:-2]:
                            row.append(player[col])
                        row.append(event.properties['server'].players.get_elo(player['number1'], elo_type))
                        row.append(Color.dp_to_irc(player['nickname']).decode('utf8'))
                        table.append(row)
                messages += list(self.__output_player_table(i['color'], player_header, table))
        else:
            table = []
            for player in event.properties['players']:
                if player['team_id']:
                    row = []
                    for col in player_header[:-2]:
                        row.append(player[col])
                    row.append(event.properties['server'].players.get_elo(player['number1'], elo_type))
                    row.append(Color.dp_to_irc(player['nickname']).decode('utf8'))
                    table.append(row)
            messages += list(self.__output_player_table(Color.CYAN, player_header, table))
        spectators = []
        for i in event.properties['players']:
            if i['team_id'] is None:
                spectators.append(Color.dp_to_irc(i['nickname']).decode('utf8'))
        if spectators:
            messages.append('Spectators: %s' % ' | '.join(spectators))

        await self.run_action(ChannelMessages, messages=messages,
                              prefix=event.properties['server'].config['out_prefix'],
                              interval=0.5)


class IRCMessageHandler(Handler):
    events = [irc_events.ChannelMessage]

    async def handle(self, event):
        irc_nick = Color.irc_to_none(event.properties['nick'].encode('utf8')).decode('utf8')
        message = Color.irc_to_none(event.properties['message'].encode('utf8')).decode('utf8')
        prefixes = set()
        for i in self.module.servers:
            prefixes |= set(i.config['in_prefixes'])
        prefixes = sorted(list(prefixes), key=lambda x: len(x), reverse=True)

        for prefix in prefixes:
            if message.startswith(prefix):
                unprefixed = message[len(prefix):]
                for server in self.module.servers:
                    if prefix in server.config['in_prefixes']:
                        server.say(unprefixed, nick='[IRC] {}'.format(irc_nick))


class VoteAcceptedHandler(Handler):
    events = [VoteAccepted]

    async def handle(self, event):
        server = event.properties['server']
        vote = event.properties['vote']
        if server.game_start_timestamp:
            time_from_start = int(time.time() - server.game_start_timestamp)
        else:
            time_from_start = -1
        db = server.module.xanmel.db
        if not db.is_up:
            return
        ts = current_time()
        cur_map, _ = await db.mgr.get_or_create(Map, server=server.server_db_obj, name=server.status.get('map'))
        if 'map_name' in vote:
            next_map, _ = await db.mgr.get_or_create(Map, server=server.server_db_obj, name=vote['map_name'])
        else:
            next_map = None
        if vote['player'].player_db_obj:
            player = vote['player'].player_db_obj
        else:
            player = await vote['player'].get_db_obj_anon()
        vote_data = {
            'player': player,
            'timestamp': ts.strftime('%Y-%m-%dT%H:%M:%S'),
            'server_id': server.config['unique_id'],
        }
        if vote['type'] in ('endmatch', 'gotomap') and server.status.get('map'):
            vote_data.update({
                'map': cur_map,
                'vote_type': 'endmatch',
                'time_since_round_start': time_from_start
            })
            await db.mgr.create(CalledVote, **vote_data)
        if vote['type'] in ('gotomap', 'nextmap'):
            vote_data.update({
                'map': next_map,
                'vote_type': 'gotomap',
                'time_since_round_start': 0
            })
            await db.mgr.create(CalledVote, **vote_data)
        if vote['type'] == 'restart' and server.status.get('map'):
            vote_data.update({
                'map': next_map,
                'vote_type': 'restart',
                'time_since_round_start': time_from_start
            })
            await db.mgr.create(CalledVote, **vote_data)


class CointossNotificationHandler(Handler):
    events = [DuelPairFormed]

    async def handle(self, event):
        server = event.properties['server']
        if server.cointosser and \
                int(server.cvars.get('_xanmel_wup_stage')) == 1 and \
                server.cointosser.state == CointosserState.PENDING:
            announcement = '^7{} ^1vs ^7{} ^3Current cointoss type: ^1{}^7. Type ^2"/cointoss heads"^3 or ^2"/cointoss tails"^3 to start the map selection process.^7'.format(
                event.properties['player1'].nickname.decode('utf8'),
                event.properties['player2'].nickname.decode('utf8'),
                server.cointosser.current_type)
            server.say(announcement)


class CointossChoiceCompleteHandler(Handler):
    events = [CointossChoiceComplete]

    async def handle(self, event):
        server = event.properties['server']
        await asyncio.sleep(2)
        server.say('^3Starting rounds in ^25 ^3seconds!^7')
        await asyncio.sleep(5)
        server.cointosser.start_playing()


class CointossGameComplete(Handler):
    events = [GameEnded]

    async def handle(self, event):
        server = event.properties['server']
        if server.cointosser is None or server.cointosser.state != CointosserState.PLAYING:
            return
        if not server.active_duel_pair:
            return
        result = {}
        for player in event.properties['players']:
            if player['team_id']:
                if player['number1'] not in [i.number1 for i in server.active_duel_pair]:
                    logger.info('%s was not an active dueller but is present in the final scores!', player['nickname'])
                result[server.players.players_by_number1[player['number1']]] = player['score']
        await server.cointosser.map_ended(event.properties['map'], result)


class CointossGameStarted(Handler):
    events = [GameStarted]

    async def handle(self, event):
        server = event.properties['server']
        if server.cointosser is None:
            return
        if server.cointosser.state == CointosserState.CHOICE_COMPLETE:
            server.cointosser.state = CointosserState.PLAYING
        if server.cointosser.state != CointosserState.PLAYING:
            server.cointosser.reset()


class RecordSetHandlerSaveToDB(Handler):
    events = [RecordSet]

    async def handle(self, event):
        server = event.properties['server']
        map_name = event.properties['map']
        player = event.properties['player']
        db = server.module.xanmel.db
        if not db.is_up:
            return
        map, _ = await db.mgr.get_or_create(Map, server=server.server_db_obj, name=map_name)
        await db.mgr.create(
            CTSRecord,
            server=server.server_db_obj,
            map=map,
            time=event.properties['result'],
            nickname=player.nickname.decode('utf8'),
            nickname_nocolors=Color.irc_to_none(player.nickname).decode('utf8'),
            crypto_idfp=player.crypto_idfp,
            stats_id=player.elo_basic and player.elo_basic.get('player_id'),
            ip_address=player.ip_address
        )


class RecordSetHandlerInform(Handler):
    events = [RecordSet]

    async def handle(self, event):
        server = event.properties['server']
        map_name = event.properties['map']
        player = event.properties['player']
        position = event.properties['position']
        result = event.properties['result']
        if position > 3:
            # TODO: maybe add this to config?
            return

        colors = ['FD0', 'CCC', 'A76']
        positions = ['1st', '2nd', '3rd']
        def __format_time(d: Decimal) -> str:
            mins = d // Decimal(60)
            secs = d - mins * Decimal(60)
            if mins > Decimal(0):
                return '{}:{:.2f}'.format(
                    mins,
                    secs
                )
            else:
                return '{:.2f}'.format(
                    secs
                )
        format_args = {
            'map_name': map_name,
            'name': player.nickname.decode('utf8'),
            'time': __format_time(result)
        }
        in_game_message = '^1\\o/ ^x{color}{map_name} {pos}:^7 {name} - ^x{color}{time}s^7'.format(
            color=colors[position - 1 ],
            pos=positions[position - 1],
            **format_args
        )
        server.say(in_game_message)
        await self.run_action(ChannelMessage,
                              message=Color.dp_to_irc(in_game_message.encode('utf8')).decode('utf8'),
                              prefix=event.properties['server'].config['out_prefix'])
        if server.forward_chat_to_other_servers:
            for other_server in self.module.servers:
                if (other_server.config['unique_id'] in server.forward_chat_to_other_servers) and (not other_server.disabled):
                    other_server.say([in_game_message],
                                     nick=server.config.get('forward_prefix', server.config.get('out_prefix')))
