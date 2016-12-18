from xanmel.test.conftest import *

from xanmel.modules.xonotic.rcon_log import RconLogParser


@pytest.fixture
def log_parser(xon_module):
    return RconLogParser(xon_module.servers[0])


@pytest.fixture
def example_scores():
    return b"""^7^xB50<E2><9D><87>^x4B0Skaven^xB50<E2><9D><87>^7^1 has been sublimated by ^7FPM^1's Vaporizer
:scores:dm_darkzone:317
:labels:player:score!!,,,,,,,,,,deaths<,dmg,dmgtaken<,,,,,,,,elo,,,,,,,,,,,,,,,,,kills,,,,,,,,,,,,,,suicides<,,,
:player:see-labels:30,0,0,0,0,0,0,0,0,0,32,3000,3200,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,30,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0:312:-1:4:FPM
:player:see-labels:21,0,0,0,0,0,0,0,0,0,17,2100,1700,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,21,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0:185:-1:7:^x26FDarth Silvius^7
:player:see-labels:29,0,0,0,0,0,0,0,0,0,34,2900,3400,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,29,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0:309:-1:5:^xB50<E2><9D><87>^x4B0Skaven^xB50<E2><9D><87>^7
:end
:gameover
FPM ^7wins."""
