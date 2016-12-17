import asynctest

from xanmel.modules.irc import MentionMessage, IRCChatUser
from xanmel.modules.irc import actions
from xanmel.modules.irc import events
from xanmel.modules.irc.handlers import MentionMessageHandler, PrivateMessageHandler
from xanmel.test.conftest import *


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
    mocker.patch.object(xanmel, 'setup_event_generators')
    xanmel.load_modules()
    irc_module = xanmel.modules['xanmel.modules.irc.IRCModule']
    send = mocker.patch.object(irc_module.client, 'send')
    channel_message = xanmel.actions[actions.ChannelMessage]
    xanmel.loop.run_until_complete(channel_message.run(message='Hello', prefix='pref'))
    xanmel.loop.run_until_complete(channel_message.run(message='Hi'))
    assert send.call_count == 2, send.call_count
    log = send.call_args_list
    assert len(log) == 2
    assert log[0][0] == ('PRIVMSG',)
    assert log[0][1]['target'] == '#xanmel'
    assert log[0][1]['message'] == 'prefHello'
    assert log[1][0] == ('PRIVMSG',)
    assert log[1][1]['target'] == '#xanmel'
    assert log[1][1]['message'] == 'Hi'


def test_channel_messages_action(xanmel, mocker):
    mocker.patch.object(xanmel, 'setup_event_generators')
    xanmel.load_modules()
    irc_module = xanmel.modules['xanmel.modules.irc.IRCModule']
    send = mocker.patch.object(irc_module.client, 'send')
    channel_messages = xanmel.actions[actions.ChannelMessages]
    xanmel.loop.run_until_complete(channel_messages.run(messages=['Hello', 'World'], prefix='pref'))
    xanmel.loop.run_until_complete(channel_messages.run(messages=['Hi', 'There']))
    assert send.call_count == 4, send.call_count
    log = send.call_args_list
    assert len(log) == 4
    assert log[0][0] == log[1][0] == log[2][0] == log[3][0] == ('PRIVMSG',)
    assert log[0][1]['target'] == log[1][1]['target'] == log[2][1]['target'] == log[3][1]['target'] == '#xanmel'
    assert log[0][1]['message'] == 'prefHello'
    assert log[1][1]['message'] == 'prefWorld'
    assert log[2][1]['message'] == 'Hi'
    assert log[3][1]['message'] == 'There'


def test_private_message_action(xanmel, mocker):
    mocker.patch.object(xanmel, 'setup_event_generators')
    xanmel.load_modules()
    irc_module = xanmel.modules['xanmel.modules.irc.IRCModule']
    send = mocker.patch.object(irc_module.client, 'send')
    private_message = xanmel.actions[actions.PrivateMessage]
    xanmel.loop.run_until_complete(private_message.run(target='username', message='Hello', prefix='pref'))
    xanmel.loop.run_until_complete(private_message.run(target='username', message='Hi'))
    assert send.call_count == 2, send.call_count
    log = send.call_args_list
    assert len(log) == 2
    assert log[0][0] == log[1][0] == ('PRIVMSG',)
    assert log[0][1]['target'] == log[1][1]['target'] == 'username'
    assert log[0][1]['message'] == 'prefHello'
    assert log[1][1]['message'] == 'Hi'


def test_private_messages_action(xanmel, mocker):
    mocker.patch.object(xanmel, 'setup_event_generators')
    xanmel.load_modules()
    irc_module = xanmel.modules['xanmel.modules.irc.IRCModule']
    send = mocker.patch.object(irc_module.client, 'send')
    private_messages = xanmel.actions[actions.PrivateMessages]
    xanmel.loop.run_until_complete(private_messages.run(target='username', messages=['Hello', 'World'], prefix='pref'))
    xanmel.loop.run_until_complete(private_messages.run(target='username', messages=['Hi', 'There']))
    log = send.call_args_list
    assert log[0][0] == log[1][0] == log[2][0] == log[3][0] == ('PRIVMSG',)
    assert log[0][1]['target'] == log[1][1]['target'] == log[2][1]['target'] == log[3][1]['target'] == 'username'
    assert log[0][1]['message'] == 'prefHello'
    assert log[1][1]['message'] == 'prefWorld'
    assert log[2][1]['message'] == 'Hi'
    assert log[3][1]['message'] == 'There'


def test_mention_message_handler(xanmel, mocker):
    mocker.patch.object(xanmel, 'setup_event_generators')
    xanmel.load_modules()
    xanmel.cmd_root.run = asynctest.CoroutineMock()
    irc_module = xanmel.modules['xanmel.modules.irc.IRCModule']
    msg_handler = MentionMessageHandler(irc_module)
    chat_user = IRCChatUser(irc_module, 'johndoe', irc_user='~johndoe@127.0.0.1')
    event = events.MentionMessage(irc_module, message='excuse', chat_user=chat_user)
    xanmel.loop.run_until_complete(msg_handler.handle(event))
    assert xanmel.cmd_root.run.call_count == 1
    assert xanmel.cmd_root.run.call_args_list[0][0] == (chat_user, 'excuse')
    assert xanmel.cmd_root.run.call_args_list[0][1] == {}


def test_private_message_handler(xanmel, mocker):
    mocker.patch.object(xanmel, 'setup_event_generators')
    xanmel.load_modules()
    xanmel.cmd_root.run = asynctest.CoroutineMock()
    irc_module = xanmel.modules['xanmel.modules.irc.IRCModule']
    msg_handler = PrivateMessageHandler(irc_module)
    chat_user = IRCChatUser(irc_module, 'johndoe', irc_user='~johndoe@127.0.0.1')
    event = events.PrivateMessage(irc_module, message='excuse', chat_user=chat_user)
    xanmel.loop.run_until_complete(msg_handler.handle(event))
    assert xanmel.cmd_root.run.call_count == 1
    assert xanmel.cmd_root.run.call_args_list[0][0] == (chat_user, 'excuse')
    assert xanmel.cmd_root.run.call_args_list[0][1] == {'is_private': True}


def test_chat_user(xanmel, mocker):
    mocker.patch.object(xanmel, 'setup_event_generators')
    xanmel.load_modules()
    xanmel.cmd_root.run = asynctest.CoroutineMock()
    irc_module = xanmel.modules['xanmel.modules.irc.IRCModule']
    chat_user = IRCChatUser(irc_module, 'johndoe', irc_user='~johndoe@127.0.0.1')
    assert chat_user.unique_id() == '~johndoe@127.0.0.1'
    assert chat_user.is_admin
    chat_user = IRCChatUser(irc_module, 'marryshelly', irc_user='~marryshelly@127.0.0.1')
    assert not chat_user.is_admin
    send = mocker.patch.object(irc_module.client, 'send')
    xanmel.loop.run_until_complete(chat_user.public_reply('HELLO'))
    xanmel.loop.run_until_complete(chat_user.private_reply('HELLO'))
    log = send.call_args_list
    assert log[0][0] == log[1][0] == ('PRIVMSG',)
    assert log[0][1]['target'] == '#xanmel'
    assert log[1][1]['target'] == 'marryshelly'
    assert log[0][1]['message'] == log[1][1]['message'] == 'HELLO'
