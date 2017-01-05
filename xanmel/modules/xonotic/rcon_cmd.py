from .rcon_parser import CombinedParser, BaseOneLineRegexParser


class StatusItemParser(BaseOneLineRegexParser):
    pass


class CvarParser(BaseOneLineRegexParser):
    pass


class CmdParser(CombinedParser):
    parsers = [StatusItemParser, CvarParser]
