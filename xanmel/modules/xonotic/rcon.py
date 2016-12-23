import asyncio
import functools
from contextlib import contextmanager
import logging

import requests

from .rcon_log import RconLogParser
from .rcon_utils import *
from .players import PlayerManager
from .chat_commands import XonCommands

logger = logging.getLogger(__name__)


class RconServer:
    def __init__(self, module, config):
        self.module = module
        self.loop = module.loop
        self.config = config
        self.server_address = config['rcon_ip']
        self.server_port = int(config['rcon_port'])
        self.password = config['rcon_password']
        self.secure = int(config.get('rcon_secure', RCON_SECURE_TIME))
        self.admin_nick = ''
        self.command_protocol = None
        self.log_protocol = None
        self.command_lock = asyncio.Lock()
        self.command_response = b''
        self.players = {}
        self.log_parser = RconLogParser(self)
        self.players = PlayerManager()
        self.current_map = ''
        self.current_gt = ''
        self.hostname = ''
        self.timing = ''
        self.server_stats = {}
        command_container = XonCommands(rcon_server=self)
        command_container.help_text = 'Commands for interacting with %s' % config['name']
        self.module.xanmel.cmd_root.register_container(command_container, config['cmd_prefix'])
        if config.get('raw_log'):
            self.raw_log = open(config['raw_log'], 'ab')
        else:
            self.raw_log = None
        self.map_list = []

    async def connect_cmd(self):
        rcon_command_protocol = rcon_protocol_factory(self.password,
                                                      self.secure,
                                                      self.receive_command_response)
        _, self.command_protocol = await self.loop.create_datagram_endpoint(
            rcon_command_protocol, remote_addr=(self.server_address, self.server_port))
        await self.update_server_status()
        await self.update_maplist()
        await self.update_server_stats()

    async def connect_log(self):
        rcon_log_protocol = rcon_protocol_factory(self.password,
                                                  self.secure,
                                                  self.receive_log_response,
                                                  self.subscribe_to_log)
        await self.loop.create_datagram_endpoint(
            rcon_log_protocol, remote_addr=(self.server_address, self.server_port)
        )

    def receive_command_response(self, data, addr):
        if addr[0] != self.server_address or addr[1] != self.server_port:
            return
        self.command_response += data

    def receive_log_response(self, data, addr):
        if addr[0] != self.server_address or addr[1] != self.server_port:
            return
        if self.raw_log:
            self.raw_log.write(data)
        self.log_parser.feed(data)

    def subscribe_to_log(self, proto):
        proto.subscribe_to_log()

    @contextmanager
    def sv_adminnick(self, new_nick):
        self.send('sv_adminnick "%s"' % new_nick)
        yield
        self.send('sv_adminnick "%s"' % self.admin_nick)

    def send(self, command):
        self.command_protocol.send(command)

    async def update_maplist(self):
        maplist_output = await self.execute('g_maplist')
        prefix = b'"g_maplist" is '
        if maplist_output.startswith(prefix) and b'\n' in maplist_output:
            m = re.match(b'"g_maplist" is "([^"]+)"', maplist_output)
            if m:
                maplist_output = m.group(1)
            self.map_list = sorted(maplist_output.decode('utf8').split(' '))
        logger.info('Got %s on the map list', len(self.map_list))
        logger.debug(self.map_list)

    async def update_server_status(self):
        status_output = await self.execute('status 1')
        lines = status_output.split(b'\n')
        for i in lines:
            if not i.strip():
                continue
            if i.startswith(b'players'):
                m = re.match(rb'players:\s*(\d+)\s*active\s*\((\d+)\s*max', i)
                self.players.max = int(m.group(2))
            if i.startswith(b'host'):
                self.hostname = i[len(b'host') + 1:].strip().decode('utf8')
            if i.startswith(b'timing'):
                self.timing = i[len(b'timing') + 1:].strip().decode('utf8')
            if i.startswith(b'^2IP '):
                break

    async def update_server_stats(self):
        if self.config.get('server_stats_url'):
            response = await self.module.xanmel.loop.run_in_executor(
                None, functools.partial(requests.get,
                                        self.config['server_stats_url'],
                                        headers={'Accept': 'application/json'}))
            try:
                self.server_stats = response.json()
            except:
                logger.info('Could not download stats, got status %s, response %r',
                            response.status_code,
                            response.text)

    async def execute(self, command, timeout=1):
        await self.command_lock.acquire()
        self.command_response = b''
        try:
            self.command_protocol.send(command)
            await asyncio.sleep(timeout)
        finally:
            self.command_lock.release()
        return self.command_response


def rcon_protocol_factory(password, secure, received_callback=None, connection_made_callback=None):
    class RconProtocol(asyncio.DatagramProtocol):
        transport = None
        local_port = None
        local_host = None

        def connection_made(self, transport):
            self.transport = transport
            self.local_host, self.local_port = self.transport.get_extra_info('sockname')
            if connection_made_callback:
                connection_made_callback(self)

        def datagram_received(self, data, addr):
            if data.startswith(RCON_RESPONSE_HEADER):
                decoded = parse_rcon_response(data)
                if received_callback:
                    received_callback(decoded, addr)

        def subscribe_to_log(self):
            # TODO: is there a way to minimize amount of data which gets pushed to log_dest_udp?
            self.send("sv_cmd addtolist log_dest_udp %s:%s" % (self.local_host, self.local_port))
            self.send("sv_logscores_console 0")
            self.send("sv_logscores_bots 1")
            self.send("sv_eventlog 1")
            self.send("sv_eventlog_console 1")

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
