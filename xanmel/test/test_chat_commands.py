import asyncio
import random
import string

import asynctest


def test_help(xanmel, mocker, dummy_chat_user):
    mocker.patch.object(xanmel, 'setup_event_generators')
    xanmel.load_modules()
    irc_module =xanmel.modules['xanmel.modules.irc.IRCModule']
    chat_user = dummy_chat_user(module=irc_module,
                                name=''.join(random.sample(string.ascii_letters, 10)))
    chat_user.botnick = irc_module.config['nick']
    xanmel.loop.run_until_complete(xanmel.cmd_root.run(chat_user, 'help', is_private=False))
    assert chat_user.public_reply.call_count == 1
    msg = chat_user.public_reply.call_args_list[0][0][0]
    assert msg.startswith('Available commands:')


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



