import string

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
