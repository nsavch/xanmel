from xanmel.modules.xonotic.players import PlayerManager, Player


def test_repr(xon_server):
    pm = PlayerManager()
    p = Player(xon_server, b'test', 1, 2, '127.0.0.1')
    assert str(p) == "b'test'"
    pm.join(p)
    assert str(pm) == '1: test'


def test_clear_bots(xon_server):
    pm = PlayerManager()
    pm.join(Player(xon_server, b'test', 1, 2, '127.0.0.1'))
    pm.join(Player(xon_server, b'bot1', 2, 3, 'bot'))
    pm.join(Player(xon_server, b'bot2', 3, 4, 'bot'))
    assert len(pm.players_by_number2) == 3
    assert len(pm.players_by_number1) == 3
    pm.clear_bots()
    assert len(pm.players_by_number2) == 1
    assert len(pm.players_by_number1) == 1
    assert pm.players_by_number1[1].nickname == b'test'


def test_clear(xon_server):
    pm = PlayerManager()
    pm.join(Player(xon_server, b'test', 1, 2, '127.0.0.1'))
    pm.join(Player(xon_server, b'bot1', 2, 3, 'bot'))
    pm.join(Player(xon_server, b'bot2', 3, 4, 'bot'))
    pm.clear()
    assert len(pm.players_by_number2) == 0
    assert len(pm.players_by_number1) == 0


def test_part(xon_server):
    pm = PlayerManager()
    pm.join(Player(xon_server, b'test', 1, 2, '127.0.0.1'))
    pm.part(1)
    assert len(pm.players_by_number2) == 0
    assert len(pm.players_by_number1) == 0
    pm.part(10)
    assert len(pm.players_by_number2) == 0
    assert len(pm.players_by_number1) == 0


def test_name_change(xon_server):
    pm = PlayerManager()
    pm.join(Player(xon_server, b'test', 1, 2, '127.0.0.1'))
    pm.name_change(1, b'barbaz')
    assert pm.players_by_number1[1].nickname == b'barbaz'
    assert pm.players_by_number2[2].nickname == b'barbaz'


def test_join_override(xon_server):
    pm = PlayerManager()
    pm.join(Player(xon_server, b'test', 1, 2, '127.0.0.1'))
    pm.join(Player(xon_server, b'test', 3, 2, '127.0.0.1'))
    assert pm.players_by_number1[3].nickname == b'test'
    assert 1 not in pm.players_by_number1


def test_get_elo(xon_server):
    pm = PlayerManager()
    pm.join(Player(xon_server, b'test', 1, 2, '127.0.0.1'))

