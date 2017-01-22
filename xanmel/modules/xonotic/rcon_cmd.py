import re

from .rcon_parser import CombinedParser, BaseOneLineRegexParser


class StatusItemParser(BaseOneLineRegexParser):
    regex = re.compile(rb'^(host|version|protocol|map|timing|players):\s*(.*)$')

    def process(self, data):
        self.rcon_server.status[data.group(1).decode('utf8')] = data.group(2).decode('utf8')


class CvarParser(BaseOneLineRegexParser):
    regex = re.compile(rb'^"(\w+)" is "([^"]*)"')

    def process(self, data):
        self.rcon_server.cvars[data.group(1).decode('utf8')] = data.group(2).decode('utf8')


class RconCmdParser(CombinedParser):
    parsers = [StatusItemParser, CvarParser]
