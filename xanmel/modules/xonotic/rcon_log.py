import logging
import re

from .colors import Color
from .events import *
from .players import Player

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


class BaseParser:
    key = b''
    is_multiline = False
    terminator = b''

    def __init__(self, rcon_server):
        self.rcon_server = rcon_server
        self.started = False
        self.finished = False
        self.data = []

    def parse(self, lines):
        if len(lines) == 0:
            return []
        if not self.is_multiline:
            line = lines[0]
            if line.startswith(self.key):
                try:
                    self.process(line[len(self.key):])
                except:
                    logger.warning('Exception during parsing line %r', line, exc_info=True)
                return lines[1:]
            else:
                return lines
        else:
            if self.started:
                line = lines.pop(0)
                while not line.startswith(self.terminator):
                    self.data.append(line)
                    if len(lines) == 0:
                        return []
                    else:
                        line = lines.pop(0)
                try:
                    self.process(self.data)
                except:
                    logger.warning('Exception during parsing multiline %r', self.data, exc_info=True)
                self.finished = True
                return lines
            else:
                line = lines[0]
                if line.startswith(self.key):
                    self.started = True
                    self.data.append(line[len(self.key):])
                    return self.parse(lines[1:])
                else:
                    return lines

    def process(self, data):
        raise NotImplementedError


class JoinParser(BaseParser):
    key = b':join:'

    def process(self, data):

        # TODO: find proper namings for number1 and number2
        number1, number2, rest = data.split(b':', 2)
        ipv4_address = re.compile(
            b'^(?:(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])')
        ipv6_address_or_addrz = re.compile(
            b'^(?:(?:[0-9A-Fa-f]{1,4}:){6}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))|::(?:[0-9A-Fa-f]{1,4}:){5}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))|(?:[0-9A-Fa-f]{1,4})?::(?:[0-9A-Fa-f]{1,4}:){4}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))|(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4})?::(?:[0-9A-Fa-f]{1,4}:){3}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))|(?:(?:[0-9A-Fa-f]{1,4}:){,2}[0-9A-Fa-f]{1,4})?::(?:[0-9A-Fa-f]{1,4}:){2}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))|(?:(?:[0-9A-Fa-f]{1,4}:){,3}[0-9A-Fa-f]{1,4})?::[0-9A-Fa-f]{1,4}:(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))|(?:(?:[0-9A-Fa-f]{1,4}:){,4}[0-9A-Fa-f]{1,4})?::(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))|(?:(?:[0-9A-Fa-f]{1,4}:){,5}[0-9A-Fa-f]{1,4})?::[0-9A-Fa-f]{1,4}|(?:(?:[0-9A-Fa-f]{1,4}:){,6}[0-9A-Fa-f]{1,4})?::)(?:%25(?:[A-Za-z0-9\\-._~]|%[0-9A-Fa-f]{2})+)?')

        if rest.startswith(b'bot'):
            ip = 'bot'
            _, rest = rest.split(b':', 1)
        else:
            m = ipv4_address.match(rest)
            if m:
                ip = m.group(0).decode('utf8')
                rest = rest[len(ip):]
            else:
                m = ipv6_address_or_addrz.match(rest)
                if m:
                    ip = m.group(0).decode('utf8')
                    rest = rest[len(ip):]
                else:
                    ip, rest = rest.split(b':', 1)
                    ip = ip.decode('utf8')

        player = self.rcon_server.players.join(Player(
            nickname=rest,
            number1=int(number1),
            number2=int(number2),
            ip_address=ip
        ))
        if player and not player.is_bot:
            Join(self.rcon_server.module, server=self.rcon_server, player=player,
                 current=self.rcon_server.players.current).fire()


class PartParser(BaseParser):
    key = b':part:'

    def process(self, data):
        try:
            player = self.rcon_server.players.part(int(data))
        except KeyError:
            pass
        else:
            if player and not player.is_bot:
                Part(self.rcon_server.module, server=self.rcon_server, player=player,
                     current=self.rcon_server.players.current).fire()


class TeamParser(BaseParser):
    # TODO: figure out what is that?
    key = b':team:'

    def process(self, data):
        pass


class ScoresParser(BaseParser):
    # TODO: currently only dm scores are supported.
    key = b':scores:'
    is_multiline = True
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
        for row in lines[1:]:
            if row.startswith(b':labels:player'):
                player_header = row.split(b':')[3].split(b',')
                player_header = [self.__only_alpha(i) for i in player_header]
            elif row.startswith(b':labels:teamscores'):
                team_header = row.split(b':')[3].split(b',')
                team_header = [self.__only_alpha(i) for i in team_header]
            elif row.startswith(b':player'):
                _, _, _, stats, time_alive, team_id, number1, nickname = row.split(b':', 7)
                player_data = {
                    'nickname': nickname,
                    'team_id': None if team_id == b'spectator' else int(team_id),
                    'number1': int(number1)
                }
                stats = stats.split(b',')
                for ix, header in enumerate(player_header):
                    if header:
                        try:
                            player_data[header] = int(stats[ix])
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
        players.sort(key=lambda x: x['score'], reverse=True)
        teams.sort(key=lambda x: x['score'], reverse=True)

        GameEnded(self.rcon_server.module,
                  server=self.rcon_server,
                  gt=gt,
                  map=map,
                  game_duration=game_duration,
                  players=players,
                  teams=teams,
                  player_header=player_header,
                  team_header=team_header
                  ).fire()


class GameStartedParser(BaseParser):
    key = b':gamestart:'

    def process(self, data):
        gt_map = data.split(b':')[0].decode('utf8')
        gt, map = gt_map.split('_', 1)
        self.rcon_server.current_map = map
        self.rcon_server.current_gt = gt
        GameStarted(self.rcon_server.module, server=self.rcon_server, gt=gt, map=map).fire()


class NameChangeParser(BaseParser):
    key = b':name:'

    def process(self, data):
        number, name = data.split(b':', 1)
        try:
            old_nickname, player = self.rcon_server.players.name_change(int(number), name)
        except IndexError:
            pass
        else:
            NameChange(self.rcon_server.module, server=self.rcon_server, player=player,
                       old_nickname=old_nickname).fire()


class ChatMessageParser(BaseParser):
    key = b'\x01'

    def process(self, data):
        ChatMessage(self.rcon_server.module, server=self.rcon_server, message=data).fire()


class RconLogParser:
    parsers = [
        JoinParser,
        PartParser,
        # TeamParser,
        ScoresParser,
        GameStartedParser,
        NameChangeParser,
        ChatMessageParser
    ]

    def __init__(self, rcon_server):
        self.rcon_server = rcon_server
        self.current = []
        self.active_parser = None

    def feed(self, data):
        self.current += data.split(b'\n')
        self.parse()

    def parse(self):
        if self.active_parser:
            self.current = self.active_parser.parse(self.current)
        else:
            previous_length = len(self.current)
            while len(self.current) > 0:
                for i in self.parsers:
                    parser = i(self.rcon_server)
                    self.current = parser.parse(self.current)
                    if parser.is_multiline and parser.started and (not parser.finished):
                        if len(self.current) != 0:
                            logger.warning('A multi-line parser %r did not finished but left some lines %r', parser,
                                           self.current)
                if previous_length == len(self.current):
                    line = self.current.pop(0)
                    if line:
                        logger.debug('Unparsed log line %r', line)
                previous_length = len(self.current)

    def parse_join(self, line):
        pass