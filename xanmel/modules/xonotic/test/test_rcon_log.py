from xanmel.modules.xonotic.events import *
from xanmel.modules.xonotic.players import Player


def test_feed(log_parser):
    log_parser.feed(b'test')
    assert log_parser.current == b'test'
    log_parser.feed(b'foobar')
    assert log_parser.current == b'testfoobar'
    log_parser.feed(b'a\nnewline')
    assert log_parser.current == b'newline'


def test_scores_singe(log_parser, mocker, xon_module, example_scores):
    mocker.patch.object(GameEnded, '__init__', return_value=None)
    mocker.patch.object(GameEnded, 'fire')
    log_parser.feed(example_scores)
    assert GameEnded.fire.call_count == 1
    assert GameEnded.__init__.call_args[0][0] == xon_module
    kwargs = GameEnded.__init__.call_args[1]
    assert kwargs['game_duration'] == 317
    assert len(kwargs['players']) == 3
    assert kwargs['players'][0]['nickname'] == b'FPM'
    assert kwargs['players'][0]['score'] == 30


def test_team_scores_multi(log_parser, mocker, example_teamscores):
    part1 = example_teamscores[:50]
    part2 = example_teamscores[50:]
    mocker.patch.object(GameEnded, '__init__', return_value=None)
    mocker.patch.object(GameEnded, 'fire')
    log_parser.feed(part1)
    assert GameEnded.fire.call_count == 0
    log_parser.feed(part2)
    assert GameEnded.fire.call_count == 1
    kwargs = GameEnded.__init__.call_args[1]
    assert kwargs['game_duration'] == 85
    assert kwargs['gt'] == 'tdm'
    assert len(kwargs['players']) == 5
    assert len(kwargs['teams']) == 2


def test_join(log_parser, mocker):
    mocker.patch.object(Join, '__init__', return_value=None)
    mocker.patch.object(Join, 'fire', return_value=None)
    log_parser.feed(b':join:4:1:127.0.0.1:^xF90sleet^7\n')
    assert Join.fire.call_count == 1
    assert Join.__init__.call_args[1]['player'].nickname == b'^xF90sleet^7'
    assert Join.__init__.call_args[1]['player'].ip_address == '127.0.0.1'


def test_join_bot(log_parser, mocker, xon_module):
    mocker.patch.object(Join, '__init__', return_value=None)
    mocker.patch.object(Join, 'fire', return_value=None)
    log_parser.feed(b':join:2:8:bot:^1[BOT]^7Lion^1.bat^7\n')
    assert Join.fire.call_count == 0
    assert xon_module.servers[0].players.players_by_number2[8].is_bot


def test_join_ipv6(log_parser, mocker):
    mocker.patch.object(Join, '__init__', return_value=None)
    mocker.patch.object(Join, 'fire', return_value=None)
    log_parser.feed(b':join:4:2:2501:cd:3000:b820:1d08:5cf2:72c1:dec6:Vasya: Pupkin\n')
    assert Join.fire.call_count == 1
    assert Join.__init__.call_args[1]['player'].nickname == b'Vasya: Pupkin'
    assert Join.__init__.call_args[1]['player'].ip_address == '2501:cd:3000:b820:1d08:5cf2:72c1:dec6'


def test_part(log_parser, mocker):
    srv = log_parser.rcon_server
    mocker.patch.object(Part, '__init__', return_value=None)
    mocker.patch.object(Part, 'fire', return_value=None)
    p = Player(b'test', 1, 2, '127.0.0.1')
    srv.players.join(p)
    log_parser.feed(b':part:1\n')
    assert Part.fire.call_count == 1
    assert Part.__init__.call_args[1]['player'] is p


def test_part_non_existent(log_parser, mocker):
    mocker.patch.object(Part, '__init__', return_value=None)
    mocker.patch.object(Part, 'fire', return_value=None)
    log_parser.feed(b':part:1\n')
    assert Part.fire.call_count == 0


def test_part_bot(log_parser, mocker):
    srv = log_parser.rcon_server
    mocker.patch.object(Part, '__init__', return_value=None)
    mocker.patch.object(Part, 'fire', return_value=None)
    p = Player(b'test', 1, 2, 'bot')
    srv.players.join(p)
    log_parser.feed(b':part:1\n')
    assert Part.fire.call_count == 0
    assert len(srv.players.players_by_number1) == 0
