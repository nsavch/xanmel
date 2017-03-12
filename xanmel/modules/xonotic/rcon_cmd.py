import re
import logging

import time

from .events import NewPlayerActive, MapChange
from .rcon_parser import CombinedParser, BaseOneLineRegexParser


logger = logging.getLogger(__name__)


class StatusItemParser(BaseOneLineRegexParser):
    regex = re.compile(rb'^(host|version|protocol|map|timing|players):\s*(.*)$')

    def process(self, data):
        key = data.group(1).decode('utf8')
        value = data.group(2).decode('utf8')
        self.rcon_server.status[key] = value
        if key == 'map' and self.rcon_server.map_voter.map_name != value:
            MapChange(self.rcon_server.module, server=self.rcon_server,
                      old_map=self.rcon_server.map_voter.map_name, new_map=value).fire()


class StatusPlayerParser(BaseOneLineRegexParser):
    regex = re.compile(rb'^\^(?:3|7)(?P<ip>[^ ]+)\s+(?P<pl>[^ ]+)\s+(?P<ping>[^ ]+)\s+(?P<time>[^ ]+)\s+(?P<frags>-?\d+)\s+#(?P<number2>\d+)\s+(?P<nickname>.*)$')

    def process(self, data):
        if not (self.rcon_server.game_start_timestamp and time.time() - self.rcon_server.game_start_timestamp > 15):
            return
        g = data.group
        if g('ip') == b'botclient':
            return
        if g('ping') == b'0':
            return
        number2 = int(g('number2'))
        old_active = self.rcon_server.players.active
        if number2 not in self.rcon_server.players.status:
            frags = -666
        else:
            frags = int(g('frags'))
        self.rcon_server.players.status[number2] = {'ip': g('ip'),
                                                    'pl': g('pl'),
                                                    'ping': g('ping'),
                                                    'time': g('time'),
                                                    'frags': frags,
                                                    'nickname': g('nickname'),
                                                    'timestamp': time.time()}
        if self.rcon_server.players.active > old_active:
            NewPlayerActive(self.rcon_server.module, server=self.rcon_server).fire()


class CvarParser(BaseOneLineRegexParser):
    regex = re.compile(rb'^"(\w+)" is "([^"]*)"')

    def process(self, data):
        self.rcon_server.cvars[data.group(1).decode('utf8')] = data.group(2).decode('utf8')
        logger.debug('Set cvar %s to %r', data.group(1).decode('utf8'), data.group(2).decode('utf8'))


class RconCmdParser(CombinedParser):
    parsers = [StatusItemParser, CvarParser, StatusPlayerParser]
