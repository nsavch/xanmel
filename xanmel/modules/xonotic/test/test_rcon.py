import copy

from xanmel.modules.xonotic.rcon import *


def test_ensure_bytes():
    assert ensure_bytes('hello') == b'hello'
    assert ensure_bytes(b'hello') == b'hello'


def test_hax0r(xon_server):
    xon_server.receive_command_response(b'test', ('127.0.1.1', 14000))
    assert xon_server.command_response == b''
    xon_server.receive_command_response(b'test', ('127.0.0.1', 26005))
    assert xon_server.command_response == b'test'

    xon_server.receive_log_response(b'test', ('127.0.1.1', 14000))
    assert xon_server.log_parser.current == b''
    xon_server.receive_log_response(b'test', ('127.0.0.1', 26005))
    assert xon_server.log_parser.current == b'test'


def test_maplist(event_loop, xon_server, mocked_coro):
    xon_server.execute = mocked_coro()
    xon_server.execute.return_value = b'"g_maplist" is "solarium stormkeep warfare runningman xoylent finalrage dance ' \
                                      b'darkzone runningmanctf drain nexballarena glowplant afterslime silentsiege ' \
                                      b'vorix techassault leave_em_behind g-23 space-elevator implosion courtfun ' \
                                      b'catharsis atelier oilrig fuse" [""]\n '
    event_loop.run_until_complete(xon_server.update_maplist())
    assert xon_server.map_list == ['afterslime', 'atelier', 'catharsis', 'courtfun', 'dance', 'darkzone', 'drain', 'finalrage',
                                   'fuse', 'g-23', 'glowplant', 'implosion', 'leave_em_behind', 'nexballarena', 'oilrig',
                                   'runningman', 'runningmanctf', 'silentsiege', 'solarium', 'space-elevator', 'stormkeep',
                                   'techassault', 'vorix', 'warfare', 'xoylent']
    ml = copy.copy(xon_server.map_list)
    xon_server.execute.return_value = b'failure'
    event_loop.run_until_complete(xon_server.update_maplist())
    assert ml == xon_server.map_list


def test_server_status(event_loop, xon_server, mocked_coro):
    xon_server.execute = mocked_coro()
    xon_server.execute.return_value = b"""host:     Xonotic 0.8.1 Server
version:  Xonotic build 02:02:44 Aug 25 2015 - release (gamename Xonotic)
protocol: 3504 (DP7)
map:      silentsiege
timing:   0.0% CPU, 0.00% lost, offset avg 0.0ms, max 0.0ms, sdev 0.0ms
players:  0 active (16 max)

IP                                             %pl ping  time   frags  no   name\n"""

    event_loop.run_until_complete(xon_server.update_server_status())
    assert xon_server.players.max == 16


def test_datagram_received(event_loop, xon_server, mocked_coro):
    asyncio.sleep = mocked_coro()
    event_loop.run_until_complete(asyncio.gather(*asyncio.Task.all_tasks()))
    proto = xon_server.command_protocol
    proto.datagram_received(b'\xff\xff\xff\xffntest', ('127.0.0.1', 26005))
    assert xon_server.command_response == b'test'
