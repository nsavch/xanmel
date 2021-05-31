from aioresponses import aioresponses


# def test_update_server_stats(event_loop, xon_server, example_server_stats):
#     xon_server.update_server_stats = xon_server.update_server_stats_orig
#     with aioresponses() as m:
#         m.get('http://stats.xonotic.org/server/7975/topscorers?last=0', status=200, payload=example_server_stats)
#         m.get('http://stats.xonotic.org/server/7975/topscorers?last=20', status=200, payload={})
#         event_loop.run_until_complete(xon_server.update_server_stats())
#     assert len(xon_server.server_rating) == 20
