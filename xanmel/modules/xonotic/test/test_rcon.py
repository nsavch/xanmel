from xanmel.modules.xonotic.rcon import *


def test_ensure_bytes():
    assert ensure_bytes('hello') == b'hello'
    assert ensure_bytes(b'hello') == b'hello'
