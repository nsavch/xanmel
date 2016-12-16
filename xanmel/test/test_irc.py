from xanmel.modules.irc import IRCChatUser
from xanmel.modules.irc.actions import *

def test_connect(xanmel, mocker, mocked_coroutine):
    mocker.patch.object(xanmel, 'setup_event_generators')
    xanmel.load_modules()
    irc_module = xanmel.modules['xanmel.modules.irc.IRCModule']
    patched_send = mocker.patch.object(irc_module.client, 'send')
    irc_module.client.wait = mocked_coroutine
    xanmel.loop.run_until_complete(irc_module.connect())
    assert patched_send.call_count == 4


def test_process_message(xanmel, mocker):
    mocker.patch.object(xanmel, 'setup_event_generators')
    xanmel.load_modules()
    irc_module = xanmel.modules['xanmel.modules.irc.IRCModule']
    patched_fire = mocker.patch('xanmel.modules.irc.events.PrivateMessage.fire')
    xanmel.loop.run_until_complete(irc_module.process_message(
        'xanmel', 'Hello, world', nick='nick', user='~nick', host='127.0.0.1'
    ))
    assert patched_fire.called
    patched_fire = mocker.patch('xanmel.modules.irc.events.ChannelMessage.fire')
    xanmel.loop.run_until_complete(irc_module.process_message(
        '#xanmel', 'Hello, world', nick='nick', user='~nick', host='127.0.0.1'
    ))
    assert patched_fire.called
    patched_fire = mocker.patch('xanmel.modules.irc.events.MentionMessage.fire')
    xanmel.loop.run_until_complete(irc_module.process_message(
        '#xanmel', 'xanmel: Hello, world', nick='nick', user='~nick', host='127.0.0.1'
    ))
    assert patched_fire.called


def test_actions(xanmel, mocker):
    log = []
    def __side_effect(*args, **kwargs):
        log.append({'args': args, 'kwargs': kwargs})
    mocker.patch.object(xanmel, 'setup_event_generators')
    xanmel.load_modules()
    irc_module = xanmel.modules['xanmel.modules.irc.IRCModule']
    send = mocker.patch.object(irc_module.client, 'send')
    send.side_effect = __side_effect
    channel_message = xanmel.actions[ChannelMessage]
    xanmel.loop.run_until_complete(channel_message.run(message='Hello'))
    assert send.call_count == 1, send.call_count
    assert len(log) == 1
    assert log[0]['args'] == ('PRIVMSG', )
    assert log[0]['kwargs']['target'] == '#xanmel'
    assert log[0]['kwargs']['message'] == 'Hello'
