import string

from xanmel.modules.xonotic.chat_user import XonoticChatUser
from xanmel.modules.xonotic.players import Player
from xanmel.test.conftest import *


def test_who(xanmel, xon_module, dummy_chat_user):
    rcon_server = xon_module.servers[0]
    rcon_server.players.join(Player(b'test', 1, 2, '127.0.0.1'))
    rcon_server.players.join(Player(b'test2', 2, 3, '127.0.0.1'))
    chat_user = dummy_chat_user(module=irc_module,
                                name=''.join(random.sample(string.ascii_letters, 10)))
    chat_user.user_type = 'irc'
    xanmel.loop.run_until_complete(xanmel.cmd_root.run(chat_user, 'xon who', is_private=False))
    assert chat_user.public_reply.call_args[0][0] == 'exe > test\x0f | test2\x0f'
    rcon_server.players.join(Player(b'[BOT] Eureka', 3, 4, 'bot'))
    xanmel.loop.run_until_complete(xanmel.cmd_root.run(chat_user, 'xon who', is_private=False))
    assert chat_user.public_reply.call_args[0][0] == 'exe > test\x0f | test2\x0f | 1 bots'


def test_maps(xanmel, xon_module, dummy_chat_user):
    rcon_server = xon_module.servers[0]
    chat_user = dummy_chat_user(module=irc_module,
                                name=''.join(random.sample(string.ascii_letters, 10)))
    xanmel.loop.run_until_complete(xanmel.cmd_root.run(chat_user, 'xon maps', is_private=False))
    assert chat_user.public_reply.call_args[0][0] == 'exe > Map List not initialized'
    rcon_server.map_list = ['afterslime', 'atelier', 'catharsis', 'courtfun', 'dance', 'darkzone', 'drain', 'finalrage', 'fuse', 'g-23', 'glowplant', 'implosion', 'leave_em_behind', 'nexballarena', 'oilrig', 'runningman', 'runningmanctf', 'silentsiege', 'solarium', 'space-elevator', 'stormkeep', 'techassault', 'vorix', 'warfare', 'xoylent']
    xanmel.loop.run_until_complete(xanmel.cmd_root.run(chat_user, 'xon maps', is_private=False))
    assert chat_user.public_reply.call_args[0][0] == 'exe > [25/25]: afterslime, atelier, catharsis, courtfun, dance, darkzone, drain, finalrage, fuse, g-23 (15 more maps skipped)'
    xanmel.loop.run_until_complete(xanmel.cmd_root.run(chat_user, 'xon maps darkzo', is_private=False))
    assert chat_user.public_reply.call_args[0][0] == 'exe > [1/25]: darkzone'


def test_chat_user(xanmel, xon_module, mocked_coro):
    srv = xon_module.servers[0]
    srv.send = mocked_coro
    cu = XonoticChatUser(xon_module, 'test', rcon_server=srv, raw_nickname=b'test^7')
    assert cu.unique_id() == b'test^7'
    xanmel.loop.run_until_complete(cu.private_reply('test'))
    assert srv.send.call_count == 0
    xanmel.loop.run_until_complete(cu.public_reply('test'))
    assert srv.send.call_count == 3
    assert [i[0][0] for i in srv.send.call_args_list] == ['sv_adminnick "xanmel"', 'say test', 'sv_adminnick ""']
    srv.config['say_type'] = 'ircmsg'
    srv.send.reset_mock()
    xanmel.loop.run_until_complete(cu.public_reply('test'))
    assert srv.send.call_count == 1
    assert [i[0][0] for i in srv.send.call_args_list] == ['sv_cmd ircmsg [BOT] xanmel^7: test']
