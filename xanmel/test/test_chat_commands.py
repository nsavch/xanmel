import re
import asyncio
import random
import string

import asynctest
import time

from xanmel import CommandContainer, ChatCommand


def test_format_help():
    class TestCommand(ChatCommand):
        help_text = 'test'
        prefix = 'pref'

    c = TestCommand()
    assert c.format_help() == 'pref: test'

    class TestArgsCommand(ChatCommand):
        prefix = 'pref1'
        help_text = 'test'
        help_args = '<ARG1> [ARG2]'

    c = TestArgsCommand()
    assert c.format_help() == 'pref1 <ARG1> [ARG2]: test'


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


def test_connect_chidlren():
    class TestContainer(CommandContainer):
        pass

    class EmptyPrefixCommand(ChatCommand):
        parent = TestContainer

    class Command1(ChatCommand):
        parent = TestContainer
        prefix = 'pref'

    class Command2(ChatCommand):
        parent = TestContainer
        prefix = 'pref'

    assert len(TestContainer.children_classes), 1
    assert TestContainer.children_classes['pref'] == Command1


def test_acl(xanmel, mocker, dummy_chat_user, irc_module):
    asyncio.sleep = asynctest.CoroutineMock()
    chat_user = dummy_chat_user(module=irc_module,
                                name=''.join(random.sample(string.ascii_letters, 10)))
    chat_user.botnick = irc_module.config['nick']
    chat_user.dummy_admin = False

    class AdminContainer(CommandContainer):
        help_text = 'Top secret container'

    class AdminCommand(ChatCommand):
        parent = AdminContainer
        prefix = 'test'
        help = 'top secret command'
        admin_required = True

    xanmel.cmd_root.register_container(AdminContainer(), prefix='')
    xanmel.loop.run_until_complete(xanmel.cmd_root.run(chat_user, 'help', is_private=False))
    msg = chat_user.public_reply.call_args_list[0][0][0]
    assert 'test' not in msg
    xanmel.cmd_root.register_container(AdminContainer(), prefix='test_pref')
    xanmel.loop.run_until_complete(xanmel.cmd_root.run(chat_user, 'help', is_private=False))
    msg = chat_user.public_reply.call_args_list[-1][0][0]
    assert 'test_pref' not in msg
    xanmel.loop.run_until_complete(xanmel.cmd_root.run(chat_user, 'help test', is_private=False))
    msg = chat_user.public_reply.call_args_list[-1][0][0]
    assert msg == 'Unavailable command test'
    chat_user.private_reply.reset_mock()
    xanmel.loop.run_until_complete(xanmel.cmd_root.run(chat_user, 'fullhelp', is_private=False))
    for i in chat_user.private_reply.call_args_list:
        msg = i[0][0]
        assert 'Top secret container' not in msg
        assert 'top secret command' not in msg


def test_throttling(xanmel, mocker, dummy_chat_user, irc_module):
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


def test_unknown_root_command(xanmel, mocker, dummy_chat_user, irc_module):
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


def test_unknown_container_command(xanmel, mocker, dummy_chat_user, irc_module):
    chat_user = dummy_chat_user(module=irc_module,
                                name=''.join(random.sample(string.ascii_letters, 10)))
    chat_user.botnick = irc_module.config['nick']
    xanmel.loop.run_until_complete(xanmel.cmd_root.run(chat_user, 'xon', is_private=False))
    assert chat_user.public_reply.call_count == 1
    msg = chat_user.public_reply.call_args_list[0][0][0]
    assert msg.startswith('xon: ')
    assert 'Use "help xon" to list available subcommands' in msg
    xanmel.loop.run_until_complete(xanmel.cmd_root.run(chat_user, 'xon abraca', is_private=False))
    assert chat_user.public_reply.call_count == 2
    msg = chat_user.public_reply.call_args_list[-1][0][0]
    assert msg == 'Unknown command xon abraca. Use "xanmel: help xon" to list available commands'
    xanmel.loop.run_until_complete(xanmel.cmd_root.run(chat_user, 'xon abraca', is_private=True))
    assert chat_user.public_reply.call_count == 2
    assert chat_user.private_reply.call_count == 1
    msg = chat_user.private_reply.call_args_list[-1][0][0]
    assert msg == 'Unknown command xon abraca. Use "help xon" to list available commands'
    xanmel.loop.run_until_complete(xanmel.cmd_root.run(chat_user, 'xon who', is_private=False))
    msg = chat_user.public_reply.call_args_list[-1][0][0]
    assert msg == 'Access Denied'
    chat_user.user_type = 'irc'
    xanmel.loop.run_until_complete(xanmel.cmd_root.run(chat_user, 'xon who', is_private=False))
    msg = chat_user.public_reply.call_args_list[-1][0][0]
    assert msg == 'exe > Server is empty'

    class EmptyContainer(CommandContainer):
        pass
    xanmel.cmd_root.register_container(EmptyContainer(), prefix='empty')
    prev_call_count = chat_user.public_reply.call_count
    xanmel.loop.run_until_complete(xanmel.cmd_root.run(chat_user, 'empty', is_private=False))
    assert chat_user.public_reply.call_count == prev_call_count, chat_user.public_reply.call_args_list[-1][0][0]


def test_help(xanmel, mocker, dummy_chat_user, irc_module):
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
    xanmel.loop.run_until_complete(xanmel.cmd_root.run(chat_user, 'help xon', is_private=False))
    assert chat_user.public_reply.call_count == 3
    msg = chat_user.public_reply.call_args_list[-1][0][0]
    assert msg.startswith('Available commands')
    xanmel.loop.run_until_complete(xanmel.cmd_root.run(chat_user, 'help abraca', is_private=False))
    assert chat_user.public_reply.call_count == 4
    msg = chat_user.public_reply.call_args_list[-1][0][0]
    assert msg.startswith('Unknown command abraca')
    xanmel.loop.run_until_complete(xanmel.cmd_root.run(chat_user, 'help xon abraca', is_private=False))
    assert chat_user.public_reply.call_count == 5
    msg = chat_user.public_reply.call_args_list[-1][0][0]
    assert msg.startswith('Unknown command xon abraca')
    chat_user.uid = random.randint(0, 1024*1024)
    xanmel.loop.run_until_complete(xanmel.cmd_root.run(chat_user, 'help xon who', is_private=False))
    assert chat_user.public_reply.call_count == 6
    msg = chat_user.public_reply.call_args_list[-1][0][0]
    assert msg.startswith('Unavailable command xon who')
    xanmel.loop.run_until_complete(xanmel.cmd_root.run(chat_user, 'help xon maps', is_private=False))
    assert chat_user.public_reply.call_count == 7
    msg = chat_user.public_reply.call_args_list[-1][0][0]
    assert msg.startswith('xon maps [PATTERN]:')


def test_fullhelp(xanmel, mocker, dummy_chat_user, irc_module):
    asyncio.sleep = asynctest.CoroutineMock()
    chat_user = dummy_chat_user(module=irc_module,
                                name=''.join(random.sample(string.ascii_letters, 10)))
    chat_user.botnick = irc_module.config['nick']
    xanmel.loop.run_until_complete(xanmel.cmd_root.run(chat_user, 'fullhelp', is_private=False))
    assert chat_user.public_reply.call_count == 0
    assert chat_user.private_reply.call_count > 0


def test_version(xanmel, mocker, dummy_chat_user, irc_module):
    chat_user = dummy_chat_user(module=irc_module,
                                name=''.join(random.sample(string.ascii_letters, 10)))
    chat_user.botnick = irc_module.config['nick']
    xanmel.loop.run_until_complete(xanmel.cmd_root.run(chat_user, 'version', is_private=False))
    assert chat_user.public_reply.call_count == 1
    if not chat_user.public_reply.call_args[0][0].startswith('Unknown'):
        assert re.match('^\d+\.\d+(a|b|rc)\d+$', chat_user.public_reply.call_args[0][0])
