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
:player:see-labels:21,0,0,0,0,0,0,0,0,0,17,2100,error,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,21,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0:185:-1:7:^x26FDarth Silvius^7
:player:see-labels:29,0,0,0,0,0,0,0,0,0,34,2900,435.384308,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,29,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0:309:-1:5:^xB50<E2><9D><87>^x4B0Skaven^xB50<E2><9D><87>^7
:end
:gameover
FPM ^7wins."""


@pytest.fixture
def example_teamscores():
    return b"""aoentuhantoehutnaoheu
:scores:tdm_stormkeep:85
:labels:player:score!!,kills,deaths<,suicides<,,,,,,
:player:see-labels:0,0,0,0,0,0,0,0,0,0:50:spectator:1:Trifluoperazine
:player:see-labels:-1,0,2,1,0,0,0,0,0,0:50:5:2:[BOT]Scorcher
:player:see-labels:2,2,0,0,0,0,0,0,0,0:50:14:3:[BOT]Hellfire
:player:see-labels:0,0,0,0,0,0,0,0,0,0:50:14:4:[BOT]Gator
:player:see-labels:0,0,1,0,0,0,0,0,0,0:50:5:5:[BOT]Necrotic
:labels:teamscores:score!!,
:teamscores:see-labels::1
:teamscores:see-labels::2
:teamscores:see-labels::3
:teamscores:see-labels::4
:teamscores:see-labels:-1,0:5
:teamscores:see-labels::6
:teamscores:see-labels::7
:teamscores:see-labels::8
:teamscores:see-labels::9
:teamscores:see-labels::10
:teamscores:see-labels::11
:teamscores:see-labels::12
:teamscores:see-labels::13
:teamscores:see-labels:2,0:14
:teamscores:see-labels::15
:end
:gameover
atoheuntahoetnuh
"""
