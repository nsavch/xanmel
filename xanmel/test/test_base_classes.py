import asyncio
import asynctest

from xanmel import Xanmel
from xanmel.modules.irc.events import MentionMessage
from xanmel.modules.irc.handlers import MentionMessageHandler
from xanmel.modules.irc.actions import ChannelMessage
from xanmel.modules.xonotic.rcon import RconServer


def test_module_loading(xanmel, mocker):
    assert len(xanmel.modules) == 3, xanmel.modules
    assert 'xanmel.modules.irc.IRCModule' in xanmel.modules.keys(), xanmel.modules
    assert 'xanmel.modules.xonotic.XonoticModule' in xanmel.modules.keys(), xanmel.modules
    assert 'xanmel.modules.fun.FunModule' in xanmel.modules.keys(), xanmel.modules
    for i in xanmel.handlers.values():
        for h in i:
            assert h.module.xanmel is xanmel
    assert xanmel.setup_event_generators.call_count == 3


def test_setup_event_generators(event_loop, mocker, mocked_coro):
    xanmel = Xanmel(event_loop, 'example_config.yaml')
    RconServer.update_server_stats = mocked_coro()
    RconServer.check_connection = mocked_coro()
    xanmel.load_modules()
    for k, v in xanmel.modules.items():
        mocker.patch.object(v, 'setup_event_generators')
        xanmel.setup_event_generators(v)
    for k, v in xanmel.modules.items():
        assert v.setup_event_generators.call_count == 1
    assert RconServer.check_connection.called


def test_teardown(xanmel, mocker):
    for k, v in xanmel.modules.items():
        mocker.patch.object(v, 'teardown')
    xanmel.teardown()
    for k, v in xanmel.modules.items():
        assert v.teardown.call_count == 1


def test_event(xanmel, mocker):
    asyncio.sleep = asynctest.CoroutineMock()
    irc_module = xanmel.modules['xanmel.modules.irc.IRCModule']
    handlers = xanmel.handlers[MentionMessage]
    for i in handlers:
        i.handle = asynctest.CoroutineMock()
    event = MentionMessage(irc_module)
    event.fire()
    pending = asyncio.Task.all_tasks()
    xanmel.loop.run_until_complete(asyncio.gather(*pending))
    for i in handlers:
        assert i.handle.call_count == 1


def test_run_action(xanmel, mocker):
    irc_module = xanmel.modules['xanmel.modules.irc.IRCModule']
    h = MentionMessageHandler(irc_module)
    a = xanmel.actions[ChannelMessage]
    a.run = asynctest.CoroutineMock()
    xanmel.loop.run_until_complete(h.run_action(ChannelMessage, message='test'))
    assert a.run.call_count == 1
    assert a.run.call_args[1] == {'message': 'test'}
