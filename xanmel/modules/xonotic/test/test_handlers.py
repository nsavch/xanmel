from xanmel.modules.xonotic.events import *
from xanmel.modules.xonotic.players import Player


def test_chat_message_handler(xanmel, xon_module, mocked_coro):
    srv = xon_module.servers[0]
    srv.players.join(Player(b'meme police ', 1, 2, '127.0.0.1'))
    srv.players.join(Player(b'test ', 3, 4, '127.0.0.1'))
    msg = b'^3meme police ^7: xanmel: excuse'
    h = xanmel.handlers[ChatMessage][0]
    xanmel.cmd_root.run = mocked_coro
    ev = ChatMessage(xon_module, message=msg, server=srv)
    xanmel.loop.run_until_complete(h.handle(ev))
    assert xanmel.cmd_root.run.call_count == 1
    assert xanmel.cmd_root.run.call_args[0][0].name == 'meme police '
    assert xanmel.cmd_root.run.call_args[0][1] == ' excuse'
