from xanmel import Handler

from .colors import Color
from .events import *
from .rcon_log import GAME_TYPES
from xanmel.modules.irc.actions import ChannelMessage, ChannelMessages


class ChatMessageHandler(Handler):
    events = [ChatMessage]

    async def handle(self, event):
        await self.run_action(ChannelMessage,
                              message=Color.dp_to_irc(event.properties['message']).decode('utf8'))


class GameStartedHandler(Handler):
    events = [GameStarted]

    async def handle(self, event):
        message = 'Playing \00310%(gametype)s\x0f on \00304%(map)s\x0f (%(max)s free slots); join now: \2xonotic +connect %(sv_ip)s:%(sv_port)s' % {
            'gametype': event.properties['gt'],
            'map': event.properties['map'],
            'max': event.properties['server'].players.max - event.properties['server'].players.current,
            'sv_ip': event.properties['server'].config['public_ip'],
            'sv_port': event.properties['server'].config['public_port']
        }
        await self.run_action(ChannelMessage, message=message)


class JoinHandler(Handler):
    events = [Join]

    async def handle(self, event):
        message = '\00309+ join\x0f: %(name)s \00304%(map)s\x0f [\00304%(current)s\x0f/\00304%(max)s\x0f]' % {
            'name': Color.dp_to_irc(event.properties['player'].nickname).decode('utf8'),
            'map': event.properties['server'].current_map,
            'current': event.properties['current'],
            'max': event.properties['server'].players.max
        }
        await self.run_action(ChannelMessage, message=message)


class PartHandler(Handler):
    events = [Part]

    async def handle(self, event):
        message = '\00304- part\x0f: %(name)s \00304%(map)s\x0f [\00304%(current)s\x0f/\00304%(max)s\x0f]' % {
            'name': Color.dp_to_irc(event.properties['player'].nickname).decode('utf8'),
            'map': event.properties['server'].current_map,
            'current': event.properties['current'],
            'max': event.properties['server'].players.max
        }
        await self.run_action(ChannelMessage, message=message)


class NameChangeHandler(Handler):
    events = [NameChange]

    async def handle(self, event):
        message = '\00312*\x0f %(name)s is known as %(new_name)s' % {
            'name': Color.dp_to_irc(event.properties['old_nickname']).decode('utf8'),
            'new_name': Color.dp_to_irc(event.properties['player'].nickname).decode('utf8')
        }
        await self.run_action(ChannelMessage, message=message)


class GameEndedHandler(Handler):
    events = [GameEnded]

    def __team_scores(self, teams):
        res = []
        for i in teams:
            res.append(
                '%(color)s%(score)s\x0f' % {
                    'color': Color(code=i['color']).irc().decode('utf8'),
                    'score': i['score']
                }
            )
        return res

    def __visible_len(self, s):
        return len(Color.irc_to_none(s.encode('utf8')))

    def __pad(self, s, l, t='right'):
        sl = self.__visible_len(s)
        if sl >= l:
            return s
        else:
            if t == 'right':
                return s + ' ' * (l - sl)
            else:
                return ' ' * (l - sl) + s

    def __output_player_table(self, color, header, table):
        maxlen = max(len(header[0]), *[self.__visible_len(i[0]) for i in table])
        line0 = Color(code=color).irc().decode('utf8')
        line0 += self.__pad(header[0], maxlen)
        for i in header[1:]:
            line0 += ' | ' + i
        line0 += '\x0f'
        yield line0
        for row in table:
            line = self.__pad(row[0], maxlen)
            for ix, col in enumerate(row[1:]):
                line += ' | ' + self.__pad(str(col), len(header[ix+1]), 'left')
            yield line

    async def handle(self, event):
        messages = ['%(gametype)s on \00304%(map)s\017 ended' % {
            'gametype': GAME_TYPES[event.properties['gt']],
            'map': event.properties['map']
        }]
        player_header = [i for i in event.properties['player_header'] if i and i != 'score']
        player_header.append('score')
        player_header.insert(0, 'player')
        if event.properties['teams']:
            messages.append(
                'Team scores: %s' % ':'.join(self.__team_scores(event.properties['teams']))
            )
            for i in event.properties['teams']:
                table = []
                for player in event.properties['players']:
                    if player['team_id'] == i['team_id']:
                        row = [Color.dp_to_irc(player['nickname']).decode('utf8')]
                        for col in player_header[1:]:
                            row.append(player[col])
                        table.append(row)
                messages += list(self.__output_player_table(i['color'], player_header, table))
        else:
            table = []
            for player in event.properties['players']:
                if player['team_id']:
                    row = [Color.dp_to_irc(player['nickname']).decode('utf8')]
                    for col in player_header[1:]:
                        row.append(player[col])
                    table.append(row)
            messages += list(self.__output_player_table(Color.NOCOLOR, player_header, table))
        spectators = []
        for i in event.properties['players']:
            if i['team_id'] is None:
                spectators.append(Color.dp_to_irc(i['nickname']).decode('utf8'))
        if spectators:
            messages.append('Spectators: %s' % ' | '.join(spectators))

        await self.run_action(ChannelMessages, messages=messages)
