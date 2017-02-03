import re

import time

from .events import NewPlayerActive
from .rcon_parser import CombinedParser, BaseOneLineRegexParser


class StatusItemParser(BaseOneLineRegexParser):
    regex = re.compile(rb'^(host|version|protocol|map|timing|players):\s*(.*)$')

    def process(self, data):
        self.rcon_server.status[data.group(1).decode('utf8')] = data.group(2).decode('utf8')


class StatusPlayerParser(BaseOneLineRegexParser):
    regex = re.compile(rb'^\^(?:3|7)(?P<ip>[^ ]+)\s+(?P<pl>[^ ]+)\s+(?P<ping>[^ ]+)\s+(?P<time>[^ ]+)\s+(?P<frags>-?\d+)\s+#(?P<number2>\d+)\s+(?P<nickname>.*)$')

    def process(self, data):
        g = data.group
        if g('ip') == b'botclient':
            return
        number2 = int(g('number2'))
        old_active = self.rcon_server.players.active
        self.rcon_server.players.status[number2] = {'ip': g('ip'),
                                                    'pl': g('pl'),
                                                    'ping': g('ping'),
                                                    'time': g('time'),
                                                    'frags': int(g('frags')),
                                                    'nickname': g('nickname'),
                                                    'timestamp': time.time()}
        if self.rcon_server.players.active > old_active:
            NewPlayerActive(self.rcon_server.module, server=self.rcon_server).fire()


class CvarParser(BaseOneLineRegexParser):
    regex = re.compile(rb'^"(\w+)" is "([^"]*)"')

    def process(self, data):
        self.rcon_server.cvars[data.group(1).decode('utf8')] = data.group(2).decode('utf8')


class RconCmdParser(CombinedParser):
    parsers = [StatusItemParser, CvarParser, StatusPlayerParser]
