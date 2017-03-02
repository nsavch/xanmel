import logging

import asyncio
import geoip2.errors

from xanmel import Handler

from .chat_user import XonoticChatUser
from .colors import Color
from .events import *
from .rcon_log import GAME_TYPES
from xanmel.modules.irc.actions import ChannelMessage, ChannelMessages
import xanmel.modules.irc.events as irc_events


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
        cmd_root = self.module.xanmel.cmd_root
        server = event.properties['server']
        msg = event.properties['message']
        nicknames = sorted([i.nickname for i in server.players.players_by_number2.values()],
                           key=lambda x: len(x), reverse=True)
        user = None
        message = None
        for nickname in nicknames:
            prefix1 = b'^7' + nickname + b'^7: '
            prefix2 = b'^3' + nickname + b'^7: '
            if msg.startswith(prefix1) or msg.startswith(prefix2):
                user = XonoticChatUser(self.module, Color.dp_to_none(nickname).decode('utf8'),
                                       raw_nickname=nickname,
                                       rcon_server=server)
                message = Color.dp_to_none(msg[len(prefix1):]).decode('utf8')
                break
        if not user or not message.startswith(user.botnick + ': '):
            await self.run_action(ChannelMessage,
                                  message=Color.dp_to_irc(event.properties['message']).decode('utf8'),
                                  prefix=event.properties['server'].config['out_prefix'])
        else:
            await cmd_root.run(user, message[len(user.botnick)+1:], is_private=False)


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

        enabled_ranks = server.config.get('player_rankings', ['dm', 'duel', 'ctf'])
        if player.elo_url:
            await player.get_elo()
        if not player.really_joined:
            return
        # TODO: move that to the player class
        formatted_ranks = 'no ranks'
        if player.elo_advanced:
            existing_ranks = player.elo_advanced.get('ranks', {})
            ranks = []
            for i in enabled_ranks:
                if i in existing_ranks:
                    ranks.append((i, existing_ranks[i]))
            if len(ranks) > 0:
                formatted_ranks = ', '.join(['%s:%s/%s' % (k, v['rank'], v['max_rank']) for k, v in ranks])
        server_rank = player.get_server_rank()
        if server_rank:
            server_rank_fmt = ' [server rank: %s/%s] ' % server_rank
        else:
            server_rank_fmt = ' '

        message = '\00309+ join\x0f: %(name)s \00312[%(rank)s]\x0f\00306%(server_rank)s\x0f\00303%(country)s\x0f \00304%(map)s\x0f [\00304%(current)s\x0f/\00304%(max)s\x0f]' % {
            'name': Color.dp_to_irc(event.properties['player'].nickname).decode('utf8'),
            'map': server.current_map,
            'current': server.players.current,
            'max': server.players.max,
            'country': player.country,
            'rank': formatted_ranks,
            'server_rank': server_rank_fmt
        }
        highest_rank = player.get_highest_rank()
        if server_rank:
            server_rank_game_fmt = ' ^3server:%s/%s^x4F0' % server_rank
        else:
            server_rank_game_fmt = ''
        if highest_rank:
            in_game_message = '^2 +join:^7 %(name)s ^2%(country)s ^x4F0[Rank %(hr_type)s:%(hr_rank)s/%(hr_maxrank)s%(server_rank)s]^7' % {
                'name': event.properties['player'].nickname.decode('utf8'),
                'hr_type': highest_rank['game_type_cd'],
                'hr_rank': highest_rank['rank'],
                'hr_maxrank': highest_rank['max_rank'],
                'country': player.country,
                'server_rank': server_rank_game_fmt
            }
        else:
            in_game_message = '^2+join:^7 %(name)s ^2%(country)s' % {
                'name': event.properties['player'].nickname.decode('utf8'),
                'country': player.country
            }
        if server.config['say_type'] == 'ircmsg':
            server.send('sv_cmd ircmsg ^7%s' % in_game_message)
        else:
            with server.sv_adminnick('*'):
                server.send('say %s' % in_game_message)
        await self.run_action(ChannelMessage, message=message,
                              prefix=event.properties['server'].config['out_prefix'])


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
                                 trigger_player_num, server.players.active)
                    if server.players.active > trigger_player_num and new_fraglimit > int(server.cvars.get('fraglimit', 0)):
                        server.send('fraglimit %d' % new_fraglimit)
                        await self.run_action(
                            ChannelMessage,
                            message='\00303Frag limit increased to \x0f\00304%d\x0f\00303 because there are more than \x0f\00304%d\x0f\00303 players\x0f' % (
                                new_fraglimit, trigger_player_num))
                        in_game_message = '^2Frag limit increased to ^3%d^2 because there are more than ^3%d^2 players^7' % (
                        new_fraglimit, trigger_player_num)
                        if server.config['say_type'] == 'ircmsg':
                            server.send('sv_cmd ircmsg ^7%s' % in_game_message)
                        else:
                            with server.sv_adminnick('*'):
                                server.send('say %s' % in_game_message)
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


class NameChangeHandler(Handler):
    events = [NameChange]

    async def handle(self, event):
        message = '\00312*\x0f %(name)s is known as %(new_name)s' % {
            'name': Color.dp_to_irc(event.properties['old_nickname']).decode('utf8'),
            'new_name': Color.dp_to_irc(event.properties['player'].nickname).decode('utf8')
        }
        await self.run_action(ChannelMessage, message=message,
                              prefix=event.properties['server'].config['out_prefix'])


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
        for server in sorted(self.module.servers, key=lambda x: len(x.config['in_prefix']), reverse=True):
            if message.startswith(server.config['in_prefix']):
                if server.config['say_type'] == 'ircmsg':
                    server.send('sv_cmd ircmsg [IRC] %s^7: %s' % (irc_nick, message))
                else:
                    with server.sv_adminnick(irc_nick):
                        server.send('say %s' % message)
                if server.config['in_prefix']:
                    break


# class IRCConnected(ServerConnectedBase):
#     events = [irc_events.ConnectedAndJoined]
#
#     async def handle(self, event):
#         for server in self.module.servers:
#             if server.hostname:
#                 await self.report(server, server.hostname)
