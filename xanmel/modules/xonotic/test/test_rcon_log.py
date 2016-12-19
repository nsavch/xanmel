from xanmel.modules.xonotic.events import GameEnded


def test_feed(log_parser, mocker):
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


def test_team_scores_multi(log_parser, mocker, xon_module, example_teamscores):
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
