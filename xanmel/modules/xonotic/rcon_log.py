import logging
import re

from .colors import Color
from .events import *
from .players import Player
from .rcon_parser import BaseMultilineParser, BaseOneLineParser, CombinedParser

logger = logging.getLogger(__name__)

GAME_TYPES = {
    'as': 'assault',
    'ca': 'clan arena',
    'cq': 'conquest',
    'ctf': 'capture the flag',
    'cts': 'race cts',
    'dom': 'domination',
    'dm': 'deathmatch',
    'ft': 'freezetag',
    'inf': 'infection',
    'inv': 'invasion',
    'jb': 'jailbreak',
    'ka': 'keepaway',
    'kh': 'key hunt',
    'lms': 'last man standing',
    'nb': 'nexball',
    'ons': 'onslaught',
    'rc': 'race',
    'tdm': 'team deathmatch',
}

ipv4_address = re.compile(
            b'^(?:(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]):')
ipv6_address_or_addrz = re.compile(
            b'^(?:(?:[0-9A-Fa-f]{1,4}:){6}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))|::(?:[0-9A-Fa-f]{1,4}:){5}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))|(?:[0-9A-Fa-f]{1,4})?::(?:[0-9A-Fa-f]{1,4}:){4}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))|(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4})?::(?:[0-9A-Fa-f]{1,4}:){3}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))|(?:(?:[0-9A-Fa-f]{1,4}:){,2}[0-9A-Fa-f]{1,4})?::(?:[0-9A-Fa-f]{1,4}:){2}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))|(?:(?:[0-9A-Fa-f]{1,4}:){,3}[0-9A-Fa-f]{1,4})?::[0-9A-Fa-f]{1,4}:(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))|(?:(?:[0-9A-Fa-f]{1,4}:){,4}[0-9A-Fa-f]{1,4})?::(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))|(?:(?:[0-9A-Fa-f]{1,4}:){,5}[0-9A-Fa-f]{1,4})?::[0-9A-Fa-f]{1,4}|(?:(?:[0-9A-Fa-f]{1,4}:){,6}[0-9A-Fa-f]{1,4})?::)(?:%25(?:[A-Za-z0-9\\-._~]|%[0-9A-Fa-f]{2})+)?:')


class JoinParser(BaseOneLineParser):
    key = b':join:'

    def process(self, data):

        # TODO: find proper namings for number1 and number2
        number1, number2, rest = data.split(b':', 2)

        if rest.startswith(b'bot'):
            ip = b'bot'
            _, rest = rest.split(b':', 1)
        else:
            m = ipv4_address.match(rest)
            if m:
                ip = m.group(0)[:-1]
                rest = rest[len(ip)+1:]
            else:
                m = ipv6_address_or_addrz.match(rest)
                if m:
                    ip = m.group(0)[:-1]
                    rest = rest[len(ip)+1:]
                else:
                    ip, rest = rest.split(b':', 1)

        player = self.rcon_server.players.join(Player(
            server=self.rcon_server,
            nickname=rest,
            number1=int(number1),
            number2=int(number2),
            ip_address=ip.decode('utf8')
        ))
        if not player.is_bot:
            Join(self.rcon_server.module, server=self.rcon_server, player=player).fire()


class PartParser(BaseOneLineParser):
    key = b':part:'

    def process(self, data):
        player = self.rcon_server.players.part(int(data))
        if player and not player.is_bot:
            Part(self.rcon_server.module, server=self.rcon_server, player=player).fire()


class ScoresParser(BaseMultilineParser):
    # TODO: currently only dm scores are supported.
    key = b':scores:'
    terminator = b':end'
    team_colors = {
        5: Color.RED,
        14: Color.BLUE,
        13: Color.YELLOW,
        10: Color.MAGENTA
    }

    def __only_alpha(self, s):
        return bytes([i for i in s if chr(i).isalpha()]).decode('utf8')

    def process(self, lines):
        gt_map, game_duration = lines[0].split(b':')
        game_duration = int(game_duration)
        gt, map = gt_map.decode('utf8').split('_', 1)
        player_header = team_header = None
        players = []
        teams = []
        player_sort_column = 'score'
        team_sort_column = 'score'
        number1s = []
        for row in lines[1:]:
            if row.startswith(b':labels:player'):
                player_header = row.split(b':')[3].split(b',')
                for i in player_header:
                    if i.endswith(b'!!'):
                        player_sort_column = self.__only_alpha(i)
                player_header = [self.__only_alpha(i) for i in player_header]
            elif row.startswith(b':labels:teamscores'):
                team_header = row.split(b':')[3].split(b',')
                for i in team_header:
                    if i.endswith(b'!!'):
                        team_sort_column = self.__only_alpha(i)
                team_header = [self.__only_alpha(i) for i in team_header]
            elif row.startswith(b':player'):
                _, _, _, stats, time_alive, team_id, number1, nickname = row.split(b':', 7)
                player_data = {
                    'nickname': nickname,
                    'team_id': None if team_id == b'spectator' else int(team_id),
                    'number1': int(number1)
                }
                number1s.append(int(number1))
                stats = stats.split(b',')
                for ix, header in enumerate(player_header):
                    if header:
                        try:
                            player_data[header] = int(stats[ix])
                        except ValueError:
                            try:
                                player_data[header] = float(stats[ix])
                            except ValueError:
                                player_data[header] = stats[ix].decode('utf8')
                players.append(player_data)
            elif row.startswith(b':teamscores'):
                _, _, _, stats, team_id = row.split(b':')
                if not stats:
                    continue
                stats = stats.split(b',')
                team_data = {
                    'team_id': int(team_id),
                    'color': self.team_colors.get(int(team_id), Color.NOCOLOR),
                }
                for ix, header in enumerate(team_header):
                    if header:
                        team_data[header] = int(stats[ix])
                teams.append(team_data)
        players.sort(key=lambda x: x[player_sort_column], reverse=True)
        teams.sort(key=lambda x: x[team_sort_column], reverse=True)

        GameEnded(self.rcon_server.module,
                  server=self.rcon_server,
                  gt=gt,
                  map=map,
                  game_duration=game_duration,
                  players=players,
                  teams=teams,
                  player_header=player_header,
                  team_header=team_header,
                  player_sort_column=player_sort_column,
                  team_sort_column=team_sort_column
                  ).fire()
        zombies = []
        for k, v in self.rcon_server.players.players_by_number1.items():
            if k not in number1s:
                zombies.append(k)
        for k in zombies:
            player = self.rcon_server.players.part(k)
            if player:
                Part(self.rcon_server.module, server=self.rcon_server, player=player).fire()


class GameStartedParser(BaseOneLineParser):
    key = b':gamestart:'

    def process(self, data):
        gt_map = data.split(b':')[0].decode('utf8')
        gt, map = gt_map.split('_', 1)
        self.rcon_server.players.status = {}
        self.rcon_server.current_map = map
        self.rcon_server.current_gt = gt
        GameStarted(self.rcon_server.module, server=self.rcon_server, gt=gt, map=map).fire()
        self.rcon_server.players.clear_bots()


class NameChangeParser(BaseOneLineParser):
    key = b':name:'

    def process(self, data):
        number, name = data.split(b':', 1)
        try:
            old_nickname, player = self.rcon_server.players.name_change(int(number), name)
        except KeyError:
            pass
        else:
            NameChange(self.rcon_server.module, server=self.rcon_server, player=player,
                       old_nickname=old_nickname).fire()


class ChatMessageParser(BaseOneLineParser):
    key = b'\x01'

    def process(self, data):
        ChatMessage(self.rcon_server.module, server=self.rcon_server, message=data.strip()).fire()


class EloParser(BaseOneLineParser):
    key = b'^7Retrieving playerstats from URL: '

    def process(self, data):
        self.rcon_server.players.current_url = data


class RconLogParser(CombinedParser):
    parsers = [
        JoinParser,
        PartParser,
        ScoresParser,
        GameStartedParser,
        NameChangeParser,
        ChatMessageParser,
        EloParser
    ]
