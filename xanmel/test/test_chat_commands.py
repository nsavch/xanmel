import asyncio
import random
import string

import asynctest
import time

from xanmel import CommandContainer, ChatCommand


def test_register_container(xanmel):
    class TestContainer(CommandContainer):
        help_text = 'test_container'

    class TestCommand(ChatCommand):
        parent = TestContainer
        prefix = 'test'

    class TestContainer2(CommandContainer):
        help_text = 'another_test_container'

    class TestCommand2(ChatCommand):
        parent = TestContainer2
        prefix = 'test'

    xanmel.cmd_root.register_container(TestContainer(), prefix='')
    assert 'test' in xanmel.cmd_root.children
    assert isinstance(xanmel.cmd_root.children['test'], TestCommand)
    xanmel.cmd_root.register_container(TestContainer(), prefix='test_prefix')
    assert 'test_prefix' in xanmel.cmd_root.children
    assert isinstance(xanmel.cmd_root.children['test_prefix'], TestContainer)
    xanmel.cmd_root.register_container(TestContainer2(), prefix='')
    assert isinstance(xanmel.cmd_root.children['test'], TestCommand)
    xanmel.cmd_root.register_container(TestContainer2(), prefix='test_prefix')
    assert isinstance(xanmel.cmd_root.children['test_prefix'], TestContainer)


def test_throttling(xanmel, mocker, dummy_chat_user):
    mocker.patch.object(xanmel, 'setup_event_generators')
    xanmel.load_modules()
    irc_module = xanmel.modules['xanmel.modules.irc.IRCModule']
    chat_user = dummy_chat_user(module=irc_module,
                                name=''.join(random.sample(string.ascii_letters, 10)))
    chat_user.botnick = irc_module.config['nick']
    start = time.time() - 300
    time_mock = mocker.patch.object(time, 'time')
    for i in range(20):
        time_mock.return_value = start + 1
        xanmel.loop.run_until_complete(xanmel.cmd_root.run(chat_user, 'excuse', is_private=False))
    assert chat_user.public_reply.call_count == 5
    time_mock.return_value = start + 300
    xanmel.loop.run_until_complete(xanmel.cmd_root.run(chat_user, 'excuse', is_private=False))
    assert chat_user.public_reply.call_count == 6


def test_unknown_command(xanmel, mocker, dummy_chat_user):
    mocker.patch.object(xanmel, 'setup_event_generators')
    xanmel.load_modules()
    irc_module = xanmel.modules['xanmel.modules.irc.IRCModule']
    chat_user = dummy_chat_user(module=irc_module,
                                name=''.join(random.sample(string.ascii_letters, 10)))
    chat_user.botnick = irc_module.config['nick']
    xanmel.loop.run_until_complete(xanmel.cmd_root.run(chat_user, 'tnaoheunthaoetnuh', is_private=False))
    assert chat_user.public_reply.call_count == 1
    msg = chat_user.public_reply.call_args_list[0][0][0]
    assert msg.startswith('Unknown command')
    assert chat_user.botnick in msg
    xanmel.loop.run_until_complete(xanmel.cmd_root.run(chat_user, 'tnaoheunthaoetnuh', is_private=True))
    assert chat_user.private_reply.call_count == 1
    msg = chat_user.private_reply.call_args_list[0][0][0]
    assert msg.startswith('Unknown command')
    assert chat_user.botnick not in msg


def test_help(xanmel, mocker, dummy_chat_user):
    mocker.patch.object(xanmel, 'setup_event_generators')
    xanmel.load_modules()
    irc_module = xanmel.modules['xanmel.modules.irc.IRCModule']
    chat_user = dummy_chat_user(module=irc_module,
                                name=''.join(random.sample(string.ascii_letters, 10)))
    chat_user.botnick = irc_module.config['nick']
    xanmel.loop.run_until_complete(xanmel.cmd_root.run(chat_user, 'help', is_private=False))
    assert chat_user.public_reply.call_count == 1
    msg = chat_user.public_reply.call_args_list[0][0][0]
    assert msg.startswith('Available commands:')
    xanmel.loop.run_until_complete(xanmel.cmd_root.run(chat_user, 'help excuse', is_private=True))
    assert chat_user.private_reply.call_count == 1
    msg = chat_user.private_reply.call_args_list[0][0][0]
    assert msg == 'excuse [USERNAME]: Finds an excuse for you or USERNAME after a bad game round.'


def test_fullhelp(xanmel, mocker, dummy_chat_user):
    asyncio.sleep = asynctest.CoroutineMock()
    mocker.patch.object(xanmel, 'setup_event_generators')
    xanmel.load_modules()
    irc_module = xanmel.modules['xanmel.modules.irc.IRCModule']
    chat_user = dummy_chat_user(module=irc_module,
                                name=''.join(random.sample(string.ascii_letters, 10)))
    chat_user.botnick = irc_module.config['nick']
    xanmel.loop.run_until_complete(xanmel.cmd_root.run(chat_user, 'fullhelp', is_private=False))
    assert chat_user.public_reply.call_count == 0
    assert chat_user.private_reply.call_count > 0
