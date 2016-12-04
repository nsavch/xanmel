import re
import logging

from .events import *


logger = logging.getLogger(__name__)


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
            if line.startswith(b':' + self.key + b':'):
                self.process(line[2 + len(self.key):])
                return lines[1:]
            else:
                return lines
        else:
            if self.started:
                line = lines.pop(0)
                while not line.startswith(b':' + self.terminator):
                    self.data.append(line)
                    if len(lines) == 0:
                        return []
                    else:
                        line = lines.pop(0)
                self.process(self.data)
                self.finished = True
                return lines
            else:
                line = lines[0]
                if line.startswith(b':' + self.key + b':'):
                    self.started = True
                    self.data.append(line[2 + len(self.key):])
                    return self.parse(lines[1:])
                else:
                    return lines

    def process(self, data):
        raise NotImplementedError


class JoinParser(BaseParser):
    key = b'join'

    def process(self, data):
        fields = data.split(b':')
        if len(fields) != 4:
            logger.debug('Invalid join entry: %r', data)
            return
        _, id, ip, nick = fields
        Join(self.rcon_server.module, player_id=id, player_ip=ip, player_nick=nick).fire()


class PartParser(BaseParser):
    key = b'part'


class TeamParser(BaseParser):
    # TODO: figure out what is that?
    key = b'team'


class ScoresParser(BaseParser):
    key = b'scores'
    is_multiline = True
    terminator = 'end'


class RconLogParser:
    parsers = [
        JoinParser,
        PartParser,
        # TeamParser,
        # ScoresParser
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
                            logger.warning('A multi-line parser %r did not finished but left some lines %r', parser, self.current)
                if previous_length == len(self.current):
                    self.current.pop(0)
                previous_length = len(self.current)

    def parse_join(self, line):
        pass
