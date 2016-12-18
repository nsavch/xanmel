from xanmel.test.conftest import *

from xanmel.modules.xonotic.rcon_log import RconLogParser


@pytest.fixture
def log_parser(xon_module):
    return RconLogParser(xon_module.servers[0])
