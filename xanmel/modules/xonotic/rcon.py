import asyncio
from contextlib import contextmanager
import logging

import aiohttp
import peewee

from xanmel.modules.xonotic.colors import Color
from xanmel.modules.xonotic.events import ServerDisconnect, ServerConnect
from xanmel.modules.xonotic.rcon_cmd import RconCmdParser
from xanmel.utils import current_time
from .rcon_log import RconLogParser
from .rcon_utils import *
from .players import PlayerManager
from .chat_commands import XonCommands
from .models import MapRating, Server, Map, Player

logger = logging.getLogger(__name__)


class MapVoter:
    def __init__(self, server):
        self.server = server
        self.map_name = ''
        self.votes = {}  # number2 -> vote

    async def store(self, new_map_name):
        db = self.server.module.xanmel.db
        if not db.is_up:
            return
        ts = current_time()
        map_name = self.map_name
        self.map_name = new_map_name
        if len(self.votes) == 0:
            return
        map, _ = await db.mgr.get_or_create(Map, server=self.server.server_db_obj, name=map_name)
        logger.debug('GOING TO STORE VOTES %s:%r', ts, self.votes)
        for vote in self.votes.values():
            if vote['player'].player_db_obj is None:
                player = await vote['player'].get_db_obj_anon()
            else:
                player = vote['player'].player_db_obj
            await db.mgr.create(
                MapRating,
                map=map,
                player=player,
                vote=vote['vote'],
                message=vote['message'])
        self.votes = {}


class RconServer:
    def __init__(self, module, config):
        self.module = module
        self.db = self.module.xanmel.db
        self.loop = module.loop
        self.config = config
        self.server_address = config['rcon_ip']
        self.server_port = int(config['rcon_port'])
        self.log_listener_ip = config.get('log_listener_ip')
        self.password = config['rcon_password']
        self.secure = int(config.get('rcon_secure', RCON_SECURE_TIME))
        self.admin_nick = ''
        self.command_transport = None
        self.command_protocol = None
        self.log_transport = None
        self.log_protocol = None
        self.command_lock = asyncio.Lock()
        self.command_response = b''
        self.log_parser = RconLogParser(self)
        self.cmd_parser = RconCmdParser(self)
        self.players = PlayerManager()
        self.current_map = ''
        self.current_gt = ''
        self.connected = False
        self.timing = ''
        self.server_rating = []
        self.local_cmd_root = None
        self.command_container = XonCommands(rcon_server=self)
        self.command_container.help_text = 'Commands for interacting with %s' % config['name']
        if config.get('raw_log'):
            self.raw_log = open(config['raw_log'], 'ab')
        else:
            self.raw_log = None
        self.map_list = []
        self.host = self.config['name']
        self.status = {}
        self.cvars = {}
        self.cmd_timestamp = 0
        self.log_timestamp = 0
        self.status_poll_interval = 6
        self.dyn_fraglimit_lock = asyncio.Lock()
        self.game_start_timestamp = 0
        self.map_voter = MapVoter(self)
        self.active_vote = None
        self.server_db_obj = None

    async def check_connection(self):
        while True:
            if not self.status or time.time() - self.log_timestamp > 60:
                if self.connected:
                    ServerDisconnect(self.module, server=self).fire()
                    self.connected = False
                logger.debug('Trying to connect to %s:%s', self.server_address, self.server_port)
                await self.connect_cmd()
                await self.connect_log()
                status = await self.update_server_status()
                if status:
                    self.connected = True
                    ServerConnect(self.module, server=self).fire()
                    self.subscribe_to_log()
                    await asyncio.wait([
                        self.cleanup_log_dest_udp(),
                        self.update_maplist(),
                        self.update_server_stats(),
                        self.update_server_name()
                    ])

            else:
                await self.update_server_status()
            await asyncio.sleep(self.status_poll_interval)

    async def connect_cmd(self):
        if self.command_transport:
            self.command_transport.abort()
        rcon_command_protocol = rcon_protocol_factory(self.password,
                                                      self.secure,
                                                      self.receive_command_response,
                                                      local_ip=self.log_listener_ip)
        self.command_transport, self.command_protocol = await self.loop.create_datagram_endpoint(
            rcon_command_protocol, remote_addr=(self.server_address, self.server_port))

    async def connect_log(self):
        if self.log_transport:
            self.log_transport.abort()
        rcon_log_protocol = rcon_protocol_factory(self.password,
                                                  self.secure,
                                                  self.receive_log_response,
                                                  local_ip=self.log_listener_ip)
        self.log_transport, self.log_protocol = await self.loop.create_datagram_endpoint(
            rcon_log_protocol, remote_addr=(self.server_address, self.server_port)
        )

    def receive_command_response(self, data, addr):
        if addr[0] != self.server_address or addr[1] != self.server_port:
            return
        self.cmd_timestamp = time.time()
        self.cmd_parser.feed(data)

    def receive_log_response(self, data, addr):
        if addr[0] != self.server_address or addr[1] != self.server_port:
            return
        self.log_timestamp = time.time()
        if self.raw_log:
            self.raw_log.write(data)
        self.log_parser.feed(data)

    async def cleanup_log_dest_udp(self):
        retries = 3
        self.cvars['log_dest_udp'] = None
        self.send('log_dest_udp')
        t = time.time()
        while not self.cvars['log_dest_udp']:
            await asyncio.sleep(0.1)
            if time.time() - t > 5:
                if retries > 0:
                    self.send('log_dest_udp')
                    t = time.time()
                    retries -= 1
                else:
                    return
        old_log_dests = self.cvars['log_dest_udp'].split(' ')
        logger.debug('Old log_dest_udp list: %r', old_log_dests)
        logger.debug('Current log listener: %r:%r', self.log_protocol.local_host, self.log_protocol.local_port)
        for i in old_log_dests:
            host, port = i.rsplit(':', 1)
            if host == self.log_protocol.local_host and int(port) != self.log_protocol.local_port:
                self.send('sv_cmd removefromlist log_dest_udp %s' % i)

    def subscribe_to_log(self):
        self.send("sv_cmd addtolist log_dest_udp %s:%s" % (self.log_protocol.local_host, self.log_protocol.local_port))
        self.send("sv_logscores_console 0")
        self.send("sv_logscores_bots 1")
        self.send("sv_eventlog 1")
        self.send("sv_eventlog_console 1")

    @contextmanager
    def sv_adminnick(self, new_nick):
        self.send('sv_adminnick "%s"' % new_nick)
        yield
        self.send('sv_adminnick "%s"' % self.admin_nick)

    def send(self, command):
        self.command_protocol.send(command)

    async def update_maplist(self):
        retries = 3
        self.cvars['g_maplist'] = None
        self.send('g_maplist')
        t = time.time()
        while not self.cvars['g_maplist']:
            await asyncio.sleep(0.1)
            if time.time() - t > 5:
                if retries > 0:
                    self.send('g_maplist')
                    t = time.time()
                    retries -= 1
                else:
                    return
        self.map_list = sorted(self.cvars['g_maplist'].split(' '))
        logger.info('Got %s on the map list', len(self.map_list))
        logger.debug(self.map_list)

    async def update_server_status(self):
        retries = 3
        self.status = {}
        self.send('status 1')
        t = time.time()
        while 'players' not in self.status:
            await asyncio.sleep(0.1)
            if time.time() - t > 3:
                if retries > 0:
                    self.send('status 1')
                    retries -= 1
                else:
                    return False
        self.host = self.status['host']
        m = re.match(r'(\d+)\s*active\s*\((\d+)\s*max', self.status['players'])
        if m:
            self.players.max = int(m.group(2))
        self.command_container.help_text = 'Commands for interacting with %s' % self.status['host']
        to_remove = []
        for n2, v in self.players.status.items():
            if time.time() - v['timestamp'] > self.status_poll_interval * 3:
                to_remove.append(n2)
        for n2 in to_remove:
            del self.players.status[n2]
        # for n2, v in self.players.status.items():
        #     logger.debug('%s: %s', n2, v)
        return True

    async def update_server_stats(self):
        if self.config.get('server_stats_url'):
            self.server_rating = []
            while True:
                async with aiohttp.ClientSession() as session:
                    async with session.get(self.config['server_stats_url'] + ('/topscorers?last=%s' % len(self.server_rating)),
                                           headers={'Accept': 'application/json'}) as resp:
                        if resp.status != 200:
                            logger.info('Could not download server stats from %s, got status %s',
                                        self.config.get['server_stats_url'],
                                        resp.status)
                            return
                        try:
                            players = await resp.json()
                            if len(players.get('top_scorers', [])) == 0:
                                break
                            else:
                                self.server_rating += players['top_scorers']
                        except:
                            logger.info('Could not parse stats', exc_info=True)

    async def update_server_name(self):
        try:
            srv = await self.db.mgr.get(Server, id=self.config['unique_id'])
        except peewee.DoesNotExist:
            srv = await self.db.mgr.create(Server, id=self.config['unique_id'], config_name=self.config['name'], name=self.status['host'])
        else:
            srv.name = self.status['host']
            await self.db.mgr.update(srv)
        self.server_db_obj = srv


def rcon_protocol_factory(password, secure, received_callback=None, connection_made_callback=None,
                          local_ip=None):
    class RconProtocol(asyncio.DatagramProtocol):
        transport = None
        local_port = None
        local_host = None

        def connection_made(self, transport):
            self.transport = transport
            self.local_host, self.local_port = self.transport.get_extra_info('sockname')
            if local_ip:
                self.local_host = local_ip
            if connection_made_callback:
                connection_made_callback(self)

        def datagram_received(self, data, addr):
            if data.startswith(RCON_RESPONSE_HEADER):
                decoded = parse_rcon_response(data)
                if received_callback:
                    received_callback(decoded, addr)

        def error_received(self, exc):
            pass

        def send(self, command):
            msg = None
            if secure == RCON_SECURE_CHALLENGE:
                raise NotImplementedError()
            elif secure == RCON_SECURE_TIME:
                msg = rcon_secure_time_packet(password, command)
            elif secure == RCON_NOSECURE:
                msg = rcon_nosecure_packet(password, command)
            self.transport.sendto(msg)

    return RconProtocol
