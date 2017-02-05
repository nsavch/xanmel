from xanmel.test.conftest import *

from xanmel.modules.xonotic.rcon_log import RconLogParser


@pytest.fixture
def log_parser(xon_module):
    return RconLogParser(xon_module.servers[0])


@pytest.fixture
def xon_server(xon_module, mocked_coro):
    srv = xon_module.servers[0]
    srv.update_server_stats_orig = srv.update_server_stats
    srv.update_server_stats = mocked_coro()
    return srv


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


@pytest.fixture
def example_scores_event():
    return {'players': [
        {'score': 30, 'deaths': 31, 'dmgtaken': 3100, 'dmg': 3380, 'team_id': -1, 'nickname': b'SummSumm', 'kills': 34,
         'number1': 1, 'elo': 0, 'suicides': 4},
        {'score': 0, 'deaths': 42, 'dmgtaken': 4200, 'dmg': 900, 'team_id': -1, 'nickname': b'ItzDub98', 'kills': 9,
         'number1': 4, 'elo': 0, 'suicides': 9}, {'score': 0, 'deaths': 6, 'dmgtaken': 600, 'dmg': 100, 'team_id': -1,
                                                  'nickname': b'^xF00\xee\x83\x88\xee\x83\x85\xee\x83\x81\xee\x83\x92\xee\x83\x94^x0EEof^xEF1\xee\x83\x87\xee\x83\x8f\xee\x83\x8c\xee\x83\x84^xFFF\xee\x82\xb5\xee\x82\xb2\xee\x82\xb3^7',
                                                  'kills': 1, 'number1': 6, 'elo': 0, 'suicides': 1}],
        'team_sort_column': 'score', 'map': 'revdm1', 'game_duration': 581, 'teams': [],
        'player_sort_column': 'score', 'gt': 'dm', 'team_header': None,
        'player_header': ['score', '', '', '', '', '', '', '', '', '', 'deaths', 'dmg', 'dmgtaken', '', '', '', '',
                          '', '', '', 'elo', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '',
                          'kills', '', '', '', '', '', '', '', '', '', '', '', '', '', 'suicides', '', '', '']}


@pytest.fixture
def example_team_scores_event():
    return {'players': [{'score': 5, 'deaths': 8, 'dmgtaken': 850, 'dmg': 1206, 'revivals': 0, 'team_id': 5,
                         'nickname': b'pip', 'kills': 13, 'number1': 6, 'elo': -2, 'suicides': 1},
                        {'score': 5, 'deaths': 6, 'dmgtaken': 600, 'dmg': 895, 'revivals': 2, 'team_id': 5,
                         'nickname': b'/^xF90\xe9\x82\xaa^xCCC/ C\xcc\xba\xcc\x9d\xcc\x9e\xcd\x96\xcc\xab\xcc\xbb\xcd\x85\xcd\x99\xcc\xb9\xcc\xb0\xcc\x9d\xcc\x9d\xcc\xb1\xcd\x8eo\xcd\x85\xcc\x9e\xcc\xad\xcc\xb0\xcd\x95\xcc\xa5\xcc\xaf\xcc\xb9\xcc\xba\xcd\x8e\xcc\xbb\xcc\xad\xcd\x8e\xcc\xb2\xcc\x9c\xcc\x9f\xcc\x9fr\xcc\xba\xcc\xa4\xcc\x9f\xcc\x9f\xcc\x96\xcd\x85\xcc\xa0\xcc\xbb\xcd\x88\xcc\x99\xcc\x9c\xcd\x87\xcc\x9f\xcc\x99o\xcc\xa0^xF90n^xFFFa^7',
                         'kills': 9, 'number1': 8,
                         'elo': 152.973511, 'suicides': 0},
                        {'score': 0, 'deaths': 10, 'dmgtaken': 1000, 'dmg': 1050, 'revivals': 0, 'team_id': 14,
                         'nickname': b'SummSumm', 'kills': 10, 'number1': 5, 'elo': 100, 'suicides': 0},
                        {'score': 0, 'deaths': 0, 'dmgtaken': 0, 'dmg': 0, 'revivals': 0, 'team_id': None,
                         'nickname': b'^1Tel^2etu^3bbi^6es^7', 'kills': 0,
                         'number1': 4, 'elo': 100, 'suicides': 0},
                        {'score': -8, 'deaths': 12, 'dmgtaken': 1101, 'dmg': 300, 'revivals':
                            0, 'team_id': 14, 'nickname': b'ItzDub98', 'kills': 3, 'number1': 7, 'elo': -2,
                         'suicides': 0}], 'team_sort_column': 'score', 'map': 'cucumber_v2', 'game_duration': 44,
            'teams': [{'score': 10, 'color': 1, 'team_id': 5}, {'score': 5, 'color': 4, 'team_id': 14}],
            'player_sort_column': 'score', 'gt': 'ft', 'team_header': ['score', ''],
            'player_header': ['score', '', '', '', '', '', '', '', '', '', 'deaths', 'dmg', 'dmgtaken', '', '', '', '',
                              '',
                              '', '', 'elo', '', '', 'revivals', '', '', '', '', '', '', '', '', '', '', '', '', '',
                              'kills', '', '', '', '',
                              '', '', '', '', '', '', '', '', '', 'suicides', '', '', '']}


@pytest.fixture
def example_server_stats():
    return {'server_id': '7994',
            'top_scorers': [{'nick': 'dr. Equivalent',
                             'player_id': 62153,
                             'rank': 1,
                             'score': 808},
                            {'nick': '^xe42M^xe52o^xd62r^xd72o^xd82s^xd82o^xd92p^xca2h^xcb2o^xcc2s^xc00.exe^7',
                             'player_id': 75981,
                             'rank': 2,
                             'score': 722},
                            {'nick': '^1|^2|^4| ^7k^xAAAo^x777u^x777g^x444i^1.exe ^x079\ud83c\udf0d^7',
                             'player_id': 35182,
                             'rank': 3,
                             'score': 169},
                            {'nick': '^x03AJarco^7', 'player_id': 88178, 'rank': 4, 'score': 143},
                            {'nick': 'марская пихота', 'player_id': 90722, 'rank': 5, 'score': 138},
                            {'nick': '^xf90sleet^7', 'player_id': 91277, 'rank': 6, 'score': 95},
                            {'nick': '^x037Lover^x666Solid ^7',
                             'player_id': 42170,
                             'rank': 7,
                             'score': 82},
                            {'nick': '^x033[^x066n^x0a9M^x0dc] ^x0BBS^x07BC^x05BR^x03BU^x20AF^x50AF^x80AY^7',
                             'player_id': 78802,
                             'rank': 8,
                             'score': 60},
                            {'nick': 'Master Trollrotz', 'player_id': 89332, 'rank': 9, 'score': 35},
                            {'nick': '^x26FDarth Silvius^7',
                             'player_id': 11700,
                             'rank': 10,
                             'score': 30},
                            {'nick': 'Goose_On_Fire^xFFF^7',
                             'player_id': 86350,
                             'rank': 11,
                             'score': 28},
                            {'nick': 'zbionic', 'player_id': 82693, 'rank': 12, 'score': 26},
                            {'nick': 'Anonymous Player #88215',
                             'player_id': 88215,
                             'rank': 13,
                             'score': 20},
                            {'nick': 'Anonymous Player #90035',
                             'player_id': 90035,
                             'rank': 14,
                             'score': 18},
                            {'nick': 'dem\ud83d\udc7dn', 'player_id': 65399, 'rank': 15, 'score': 9},
                            {'nick': 'ericbsd', 'player_id': 91171, 'rank': 16, 'score': 7},
                            {'nick': 'Anonymous Player #91907',
                             'player_id': 91907,
                             'rank': 17,
                             'score': 7},
                            {'nick': '\ue0c3\ue0c9\ue0c3\ue0c3\ue0c1\ue0c2\ue0cf\ue0cf\ue0cd\ue0c2\ue0cf\ue0cf\ue0cd',
                             'player_id': 90380,
                             'rank': 18,
                             'score': 6},
                            {'nick': 'Anonymous Player #81361',
                             'player_id': 81361,
                             'rank': 19,
                             'score': 5},
                            {'nick': '\ue0c7\ue0c9\ue0cc\ue0cc\ue0c8\ue0c1\ue0cd\ue0d3',
                             'player_id': 33321,
                             'rank': 20,
                             'score': 4}]}
