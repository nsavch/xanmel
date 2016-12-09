import asyncio

from .rcon_log import RconLogParser
from .rcon_utils import *
from .players import PlayerManager


class RconServer:
    def __init__(self, module, config):
        self.module = module
        self.loop = module.loop
        self.config = config
        self.server_address = config['rcon_ip']
        self.server_port = config['rcon_port']
        self.password = config['rcon_password']
        self.secure = config.get('rcon_secure', RCON_SECURE_TIME)
        self.command_protocol = None
        self.log_protocol = None
        self.command_lock = asyncio.Lock()
        self.command_response = b''
        self.players = {}
        self.log_parser = RconLogParser(self)
        self.players = PlayerManager()
        self.current_map = ''
        self.current_gt = ''

    async def connect_cmd(self):
        rcon_command_protocol = rcon_protocol_factory(self.password,
                                                      self.secure,
                                                      self.receive_command_response)
        _, self.command_protocol = await self.loop.create_datagram_endpoint(
            rcon_command_protocol, remote_addr=(self.server_address, self.server_port))
        await self.update_server_status()

    async def connect_log(self):
        rcon_log_protocol = rcon_protocol_factory(self.password,
                                                  self.secure,
                                                  self.receive_log_response,
                                                  self.subscribe_to_log)
        await self.loop.create_datagram_endpoint(
            rcon_log_protocol, remote_addr=(self.server_address, self.server_port)
        )

    def receive_command_response(self, data, addr):
        self.command_response += data

    def receive_log_response(self, data, addr):
        self.log_parser.feed(data)

    def subscribe_to_log(self, proto):
        proto.subscribe_to_log()

    def send(self, command):
        self.command_protocol.send(command)

    async def update_server_status(self):
        # TODO: clean up "zombie" players
        status_output = await self.execute('status 1')
        for i in status_output.split(b'\n'):
            if not i.strip():
                continue
            if i.startswith(b'players'):
                m = re.match(rb'players:\s*(\d+)\s*active\s*\((\d+)\s*max', i)
                self.players.max = int(m.group(2))

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
