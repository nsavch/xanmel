import asyncio
from xanmel.modules.xonotic.rcon_utils import *


class RconServer:
    def __init__(self, loop, server_address, server_port, password, secure=RCON_SECURE_TIME):
        self.loop = loop
        self.server_address = server_address
        self.server_port = server_port
        self.password = password
        self.secure = secure
        self.command_protocol = None
        self.log_protocol = None
        self.command_lock = asyncio.Lock()
        self.command_response = b''

    async def connect(self):
        _, self.command_protocol = await self.loop.create_datagram_endpoint(
            RconProtocol, remote_addr=(self.server_address, self.server_port))
        self.command_protocol.received_callback = self.receive_command_response

        _, self.log_protocol = await self.loop.create_datagram_endpoint(
            RconProtocol, remote_addr=(self.server_address, self.server_port)
        )
        self.log_protocol.received_callback = self.receive_log_response
        self.log_protocol.subscribe_to_log()

    def receive_command_response(self, data, addr):
        self.command_response += data

    def receive_log_response(self, data, addr):
        for i in data.split(b'\n'):
            print('LOG: ', i)

    async def execute(self, command, timeout=1):
        await self.command_lock.acquire()
        self.command_response = b''
        try:
            self.command_protocol.send(command)
            await asyncio.sleep(timeout)
        finally:
            self.command_lock.release()
        return self.command_response


class RconProtocol(asyncio.DatagramProtocol):
    transport = None
    password = 'password'
    local_port = None
    local_host = None
    received_callback = None

    def connection_made(self, transport):
        self.transport = transport
        self.local_host, self.local_port = self.transport.get_extra_info('sockname')

    def datagram_received(self, data, addr):
        if data.startswith(RCON_RESPONSE_HEADER):
            decoded = parse_rcon_response(data)
            if self.received_callback:
                self.received_callback(decoded, addr)

    def subscribe_to_log(self):
        self.send("sv_cmd addtolist log_dest_udp %s:%s" % (self.local_host, self.local_port))

    def send(self, command):
        msg = None
        if self.transport.secure == RCON_SECURE_CHALLENGE:
            raise NotImplementedError()
        elif self.transport.secure == RCON_SECURE_TIME:
            msg = rcon_secure_time_packet(self.password, command)
        elif self.transport.secure == RCON_NOSECURE:
            msg = rcon_nosecure_packet(self.password, command)
        self.transport.sendto(msg)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    rcon_server = RconServer(loop, '127.0.0.1', 26005, 'password')
