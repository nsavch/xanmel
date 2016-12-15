import pytest


def test_module_loading(xanmel, mocker):
    mf = mocker.patch.object(xanmel, 'setup_event_generators')
    xanmel.load_modules()
    assert len(xanmel.modules) == 3, xanmel.modules
    assert 'xanmel.modules.irc.IRCModule' in xanmel.modules.keys(), xanmel.modules
    assert 'xanmel.modules.xonotic.XonoticModule' in xanmel.modules.keys(), xanmel.modules
    assert 'xanmel.modules.fun.FunModule' in xanmel.modules.keys(), xanmel.modules
    assert mf.call_count == 3
