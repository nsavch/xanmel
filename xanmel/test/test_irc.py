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


def test_channel_message_action(xanmel, mocker):
    log = []

    def __side_effect(*args, **kwargs):
        log.append({'args': args, 'kwargs': kwargs})

    mocker.patch.object(xanmel, 'setup_event_generators')
    xanmel.load_modules()
    irc_module = xanmel.modules['xanmel.modules.irc.IRCModule']
    send = mocker.patch.object(irc_module.client, 'send')
    send.side_effect = __side_effect
    channel_message = xanmel.actions[ChannelMessage]
    xanmel.loop.run_until_complete(channel_message.run(message='Hello', prefix='pref'))
    xanmel.loop.run_until_complete(channel_message.run(message='Hi'))
    assert send.call_count == 2, send.call_count
    assert len(log) == 2
    assert log[0]['args'] == ('PRIVMSG',)
    assert log[0]['kwargs']['target'] == '#xanmel'
    assert log[0]['kwargs']['message'] == 'prefHello'
    assert log[1]['args'] == ('PRIVMSG',)
    assert log[1]['kwargs']['target'] == '#xanmel'
    assert log[1]['kwargs']['message'] == 'Hi'


def test_channel_messages_action(xanmel, mocker):
    log = []

    def __side_effect(*args, **kwargs):
        log.append({'args': args, 'kwargs': kwargs})

    mocker.patch.object(xanmel, 'setup_event_generators')
    xanmel.load_modules()
    irc_module = xanmel.modules['xanmel.modules.irc.IRCModule']
    send = mocker.patch.object(irc_module.client, 'send')
    send.side_effect = __side_effect
    channel_messages = xanmel.actions[ChannelMessages]
    xanmel.loop.run_until_complete(channel_messages.run(messages=['Hello', 'World'], prefix='pref'))
    xanmel.loop.run_until_complete(channel_messages.run(messages=['Hi', 'There']))
    assert send.call_count == 4, send.call_count
    assert len(log) == 4
    assert log[0]['args'] == log[1]['args'] == log[2]['args'] == log[3]['args'] == ('PRIVMSG',)
    assert log[0]['kwargs']['target'] == log[1]['kwargs']['target'] == log[2]['kwargs']['target'] == log[3]['kwargs']['target'] == '#xanmel'
    assert log[0]['kwargs']['message'] == 'prefHello'
    assert log[1]['kwargs']['message'] == 'prefWorld'
    assert log[2]['kwargs']['message'] == 'Hi'
    assert log[3]['kwargs']['message'] == 'There'


def test_private_message_action(xanmel, mocker):
    log = []

    def __side_effect(*args, **kwargs):
        log.append({'args': args, 'kwargs': kwargs})

    mocker.patch.object(xanmel, 'setup_event_generators')
    xanmel.load_modules()
    irc_module = xanmel.modules['xanmel.modules.irc.IRCModule']
    send = mocker.patch.object(irc_module.client, 'send')
    send.side_effect = __side_effect
    private_message = xanmel.actions[PrivateMessage]
    xanmel.loop.run_until_complete(private_message.run(target='username', message='Hello', prefix='pref'))
    xanmel.loop.run_until_complete(private_message.run(target='username', message='Hi'))
    assert send.call_count == 2, send.call_count
    assert len(log) == 2
    assert log[0]['args'] == log[1]['args'] == ('PRIVMSG',)
    assert log[0]['kwargs']['target'] == log[1]['kwargs']['target'] == 'username'
    assert log[0]['kwargs']['message'] == 'prefHello'
    assert log[1]['kwargs']['message'] == 'Hi'


def test_private_messages_action(xanmel, mocker):
    log = []

    def __side_effect(*args, **kwargs):
        log.append({'args': args, 'kwargs': kwargs})

    mocker.patch.object(xanmel, 'setup_event_generators')
    xanmel.load_modules()
    irc_module = xanmel.modules['xanmel.modules.irc.IRCModule']
    send = mocker.patch.object(irc_module.client, 'send')
    send.side_effect = __side_effect
    private_messages = xanmel.actions[PrivateMessages]
    xanmel.loop.run_until_complete(private_messages.run(target='username', messages=['Hello', 'World'], prefix='pref'))
    xanmel.loop.run_until_complete(private_messages.run(target='username', messages=['Hi', 'There']))
    assert log[0]['args'] == log[1]['args'] == log[2]['args'] == log[3]['args'] == ('PRIVMSG',)
    assert log[0]['kwargs']['target'] == log[1]['kwargs']['target'] == log[2]['kwargs']['target'] == log[3]['kwargs']['target'] == 'username'
    assert log[0]['kwargs']['message'] == 'prefHello'
    assert log[1]['kwargs']['message'] == 'prefWorld'
    assert log[2]['kwargs']['message'] == 'Hi'
    assert log[3]['kwargs']['message'] == 'There'
