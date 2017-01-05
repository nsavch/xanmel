import logging

logger = logging.getLogger(__name__)


class BaseOneLineParser:
    key = b''
    started = False
    finished = True

    def __init__(self, rcon_server):
        self.rcon_server = rcon_server

    def parse(self, lines):
        if not lines:
            return lines
        if lines[0].startswith(self.key):
            try:
                self.process(lines[0][len(self.key):])
            except:
                logger.warning('Exception during parsing line %r', lines[0], exc_info=True)
            return lines[1:]
        else:
            return lines

    def process(self, data):
        raise NotImplementedError  # pragma: no cover


class BaseOneLineRegexParser:
    regex = None
    started = False
    finished = True

    def __init__(self, rcon_server):
        self.rcon_server = rcon_server

    def parse(self, lines):
        if not lines:
            return lines
        m = self.regex.match(lines[0])
        if m is None:
            return lines
        else:
            try:
                self.process(m)
            except:
                logger.warning('Exception during parsing line %r', lines[0], exc_info=True)
            return lines[1:]

    def process(self, data):
        raise NotImplementedError


class BaseMultilineParser:
    key = b''
    is_multiline = False
    terminator = b''

    def __init__(self, rcon_server):
        self.rcon_server = rcon_server
        self.started = False
        self.finished = False
        self.received_eol = False
        self.lines = []

    def parse(self, lines):
        if not lines:
            return lines
        if self.started:
            line = lines.pop(0)
            while not line.startswith(self.terminator):
                self.lines.append(line)
                if not lines:
                    return []
                else:
                    line = lines.pop(0)
            try:
                self.process(self.lines)
            except:
                logger.warning('Exception during parsing multiline %r', self.lines, exc_info=True)
            self.finished = True
            return lines
        else:
            if lines[0].startswith(self.key):
                self.lines.append(lines.pop(0)[len(self.key):])
                self.started = True
                return self.parse(lines)
            else:
                return lines

    def process(self, data):
        raise NotImplementedError  # pragma: no cover


class CombinedParser:
    parsers = []

    def __init__(self, rcon_server):
        self.rcon_server = rcon_server
        self.current = b''
        self.active_parser = None

    def feed(self, data):
        self.current += data
        self.parse()

    def parse(self):
        *lines, self.current = self.current.split(b'\n')
        if self.active_parser:
            lines = self.active_parser.parse(lines)
            if self.active_parser.finished:
                self.active_parser = None
        while lines:
            print(lines)
            prev_len = len(lines)
            for i in self.parsers:
                parser = i(self.rcon_server)
                lines = parser.parse(lines)
                if parser.started and (not parser.finished):
                    self.active_parser = parser
                    if lines:
                        logger.error('A multi-line parser %r did not finished but left some lines %r',
                                     parser, lines)
                    else:
                        logger.debug('Waiting for more input for parser %r', parser)
            if len(lines) == prev_len:
                lines.pop(0)
