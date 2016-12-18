import string
import asynctest
from xanmel.test.conftest import *


def test_fun(xanmel, mocker, dummy_chat_user):
    fun_module = xanmel.modules['xanmel.modules.fun.FunModule']
    chat_user = dummy_chat_user(module=fun_module, name=''.join(random.sample(string.ascii_letters, 10)))
    xanmel.loop.run_until_complete(xanmel.cmd_root.run(chat_user, 'excuse', is_private=False))
    assert chat_user.public_reply.call_count == 1
    assert chat_user.private_reply.call_count == 0
    assert chat_user.public_reply.call_args_list[0][0][0].startswith(chat_user.name + ', ')
    xanmel.loop.run_until_complete(xanmel.cmd_root.run(chat_user, 'excuse', is_private=True))
    xanmel.loop.run_until_complete(xanmel.cmd_root.run(chat_user, 'excuse Goose_on_Fire', is_private=False))
    assert chat_user.public_reply.call_count == 2
    assert chat_user.private_reply.call_count == 1
