from xanmel.modules.irc.actions import ChannelMessage
from xanmel.modules.xonotic.events import *
from xanmel.modules.xonotic.handlers import GameEndedHandler
from xanmel.modules.xonotic.players import Player
from xanmel.modules.irc.events import ChannelMessage as ChannelMessageEvent


def test_chat_message_handler_cmd(xanmel, xon_module, xon_server, mocked_coro):
    xon_server.players.join(Player(xon_server, b'meme police ', 1, 2, '127.0.0.1'))
    xon_server.players.join(Player(xon_server, b'test ', 3, 4, '127.0.0.1'))
    msg = b'^3meme police ^7: xanmel: excuse'
    h = xanmel.handlers[ChatMessage][0]
    xon_server.local_cmd_root.run = mocked_coro()
    ev = ChatMessage(xon_module, message=msg, server=xon_server)
    xanmel.loop.run_until_complete(h.handle(ev))
    assert xon_server.local_cmd_root.run.call_count == 1
    assert xon_server.local_cmd_root.run.call_args[0][0].name == 'meme police '
    assert xon_server.local_cmd_root.run.call_args[0][1] == ' excuse'


def test_chat_message_handler_forward(xanmel, xon_module, mocked_coro):
    srv = xon_module.servers[0]
    msg = b'^7test^7: hi / good luck and have fun'
    ev = ChatMessage(xon_module, message=msg, server=srv)
    h = xanmel.handlers[ChatMessage][0]
    h.run_action = mocked_coro()
    xanmel.loop.run_until_complete(h.handle(ev))
    assert h.run_action.call_count == 1
    assert h.run_action.call_args[0][0] is ChannelMessage
    assert h.run_action.call_args[1]['message'] == '\x0ftest\x0f: hi / good luck and have fun\x0f'
    assert h.run_action.call_args[1]['prefix'] == 'exe > '


def test_chat_message_command_from_non_player(xanmel, xon_module, mocked_coro):
    srv = xon_module.servers[0]
    msg = b'^3meme police ^7: xanmel: excuse'
    ev = ChatMessage(xon_module, message=msg, server=srv)
    h = xanmel.handlers[ChatMessage][0]
    h.run_action = mocked_coro()
    xanmel.loop.run_until_complete(h.handle(ev))
    assert h.run_action.call_count == 1
    assert h.run_action.call_args[0][0] is ChannelMessage
    assert h.run_action.call_args[1]['message'] == '\x0307meme police \x0f: xanmel: excuse\x0f'
    assert h.run_action.call_args[1]['prefix'] == 'exe > '


def test_game_started_handler_empty(xanmel, xon_server, xon_module, mocked_coro, mocker):
    mocker.patch.object(xon_server, 'send')
    srv = xon_module.servers[0]
    ev = GameStarted(xon_module, server=srv)
    h = xanmel.handlers[GameStarted][0]
    h.run_action = mocked_coro()
    xanmel.loop.run_until_complete(h.handle(ev))
    assert not h.run_action.called


def test_game_started_handler(xanmel, xon_module, xon_server, mocked_coro, mocker):
    mocker.patch.object(xon_server,'send')
    xon_server.players.max = 12
    xon_server.players.join(Player(xon_server, b'meme police ', 1, 2, '127.0.0.1'))
    xon_server.players.join(Player(xon_server, b'test ', 3, 4, '127.0.0.1'))
    ev = GameStarted(xon_module, server=xon_server, gt='dm', map='darkzone')
    h = xanmel.handlers[GameStarted][0]
    h.run_action = mocked_coro()
    xanmel.loop.run_until_complete(h.handle(ev))
    assert h.run_action.called
    assert h.run_action.call_args[0][0] is ChannelMessage
    msg = h.run_action.call_args[1]['message']
    assert '[2/12]' in msg
    assert 'darkzone' in msg
    assert 'deathmatch' in msg


def test_join_handler(xanmel, xon_module, xon_server, mocked_coro, mocker):
    xon_server.config['show_geolocation_for'] = 'all'
    xon_server.players.max = 12
    mocker.patch.object(xon_server, 'send')
    xon_server.players.join(Player(xon_server, b'meme police ', 1, 2, '127.0.0.1'))
    p = Player(xon_server, b'test ', 3, 4, '45.32.238.255')
    xon_server.players.join(p)
    ev = Join(xon_module, player=p, server=xon_server)
    h = xanmel.handlers[Join][0]
    h.run_action = mocked_coro()
    xanmel.loop.run_until_complete(h.handle(ev))
    assert h.run_action.called
    assert h.run_action.call_args[0][0] is ChannelMessage
    msg = h.run_action.call_args[1]['message']
    assert '[\x03042\x0f/\x030412\x0f]' in msg
    assert 'Netherlands' in msg
    assert 'test' in msg
    p = Player(xon_server, b'test123', 5, 6, '127.0.0.1')
    xon_server.players.join(p)
    ev = Join(xon_module, player=p, server=xon_server)
    xanmel.loop.run_until_complete(h.handle(ev))
    msg = h.run_action.call_args[1]['message']
    assert 'Unknown' in msg


def test_part_handler(xanmel, xon_module, xon_server, mocked_coro):
    xon_server.config['show_geolocation_for'] = 'all'
    xon_server.players.max = 12
    xon_server.players.join(Player(xon_server, b'meme police ', 1, 2, '127.0.0.1'))
    p = Player(xon_server, b'test ', 3, 4, '45.32.238.255')
    ev = Part(xon_module, player=p, server=xon_server)
    h = xanmel.handlers[Part][0]
    h.run_action = mocked_coro()
    xanmel.loop.run_until_complete(h.handle(ev))
    assert h.run_action.called
    msg = h.run_action.call_args[1]['message']
    assert '[\x03041\x0f/\x030412\x0f]' in msg
    assert 'Netherlands' in msg
    assert 'test' in msg


def test_name_change_handler(xanmel, xon_module, xon_server, mocked_coro):
    p = Player(xon_server, b'meme police ', 1, 2, '127.0.0.1')
    xon_server.players.join(p)
    xon_server.players.name_change(1, b'foobar')
    ev = NameChange(xon_module, player=p, old_nickname=b'meme police ', server=xon_server)
    h = xanmel.handlers[NameChange][0]
    h.run_action = mocked_coro()
    xanmel.loop.run_until_complete(h.handle(ev))
    assert h.run_action.called
    msg = h.run_action.call_args[1]['message']
    assert 'meme police' in msg
    assert 'is known as' in msg
    assert 'foobar'
    assert msg.index('meme police') < msg.index('foobar')


def test_irc_message_handler(xanmel, xon_module, irc_module, xon_server, mocker):
    mocker.patch.object(xon_server, 'send')
    ev = ChannelMessageEvent(irc_module, message='hello world!', nick='test')
    h = xanmel.handlers[ChannelMessageEvent][0]
    xanmel.loop.run_until_complete(h.handle(ev))
    assert xon_server.send.call_count == 3
    msg = xon_server.send.call_args_list[1][0][0]
    assert 'hello world' in msg
    xon_server.config['say_type'] = 'ircmsg'
    xanmel.loop.run_until_complete(h.handle(ev))
    assert xon_server.send.call_count == 4
    msg = xon_server.send.call_args[0][0]
    assert 'hello world' in msg
    xon_server.config['in_prefix'] = 'abraca'
    xanmel.loop.run_until_complete(h.handle(ev))
    assert xon_server.send.call_count == 4, xon_server.send.call_args_list


def test_scores_handler_empty(xanmel, xon_module, xon_server, mocked_coro):
    ev = GameEnded(xon_module, server=xon_server, players=[])
    h = xanmel.handlers[GameEnded][0]
    h.run_action = mocked_coro()
    xanmel.loop.run_until_complete(h.handle(ev))
    assert not h.run_action.called


def test_scores_handler(xanmel, xon_module, xon_server, mocked_coro, example_scores_event, example_team_scores_event):
    ev = GameEnded(xon_module, server=xon_server, **example_scores_event)
    for h in xanmel.handlers[GameEnded]:
        if isinstance(h, GameEndedHandler):
            break
    h.run_action = mocked_coro()
    xanmel.loop.run_until_complete(h.handle(ev))
    assert h.run_action.called
    h.run_action.reset_mock()
    assert not h.run_action.called
    ev = GameEnded(xon_module, server=xon_server, **example_team_scores_event)
    xanmel.loop.run_until_complete(h.handle(ev))
    assert h.run_action.called
