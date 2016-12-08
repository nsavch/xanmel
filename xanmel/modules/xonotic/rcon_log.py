import logging

from .events import *

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
        fields = data.split(b':')
        # TODO: find proper namings for number1 and number2
        number1, number2, ip, nick = fields
        Join(self.rcon_server.module,
             server=self.rcon_server,
             number1=int(number1),
             number2=int(number2),
             ip=ip,
             nick=nick).fire()


class PartParser(BaseParser):
    key = b':part:'

    def process(self, data):
        Part(self.rcon_server.module, server=self.rcon_server, number1=int(data)).fire()


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

    def process(self, lines):
        gt_map = lines[0].split(b':')[0]
        rows = lines[2:]
        gt, map = gt_map.split(b'_')
        scores = []
        for i in rows:
            fields = i.split(b':')
            stats = fields[3].split(b',')

            row_data = dict(
                score=int(stats[0]),
                kills=int(stats[1]),
                deaths=int(stats[2]),
                suicides=int(stats[3]),
                field4=fields[4],  # TODO: wtf is this field?
                field5=fields[5],  # TODO: wtf is this field?
                field6=fields[6],  # TODO: wtf is this field?
                nick=fields[7],
            )
            scores.append(row_data)
        scores.sort(key=lambda x: x['score'], reverse=True)

        GameEnded(self.rcon_server.module,
                  server=self.rcon_server,
                  gt=gt,
                  map=map,
                  scores=scores
                  ).fire()


class GameStartedParser(BaseParser):
    key = b':gamestart:'

    def process(self, data):
        gt_map = data.split(b':')[0].decode('utf8')
        gt, map = gt_map.split('_')
        GameStarted(self.rcon_server.module, server=self.rcon_server, gt=gt, map=map).fire()


class NameChangeParser(BaseParser):
    key = b':name:'

    def process(self, data):
        # TODO: figure out what the number here means
        number, name = data.split(b':')
        NameChange(self.rcon_server.module, server=self.rcon_server, number=number, name=name).fire()


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
