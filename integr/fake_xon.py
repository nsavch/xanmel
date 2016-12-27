import asyncio
import logging

logger = logging.getLogger(__name__)

QUAKE_PACKET_HEADER = b'\xFF' * 4


class RconProtocol(asyncio.DatagramProtocol):
    password = b'password'
    transport = None

    def connection_made(self, transport):
        logger.debug('Xon Connection made from %s', transport)
        self.transport = transport

    def datagram_received(self, data, addr):
        print(data)
        for line in data.split(b'\n'):
            assert line.startswith(QUAKE_PACKET_HEADER), line
            line = line[len(QUAKE_PACKET_HEADER):].strip()
            srcon_pref = b'srcon HMAC-MD4 TIME '
            assert line.startswith(b'rcon') or line.startswith(srcon_pref), line
            if line.startswith(b'rcon'):
                _, password, cmd = line.split(b' ', 2)
                assert password.strip() == self.password, line
                self.server.queue.append(cmd)
            else:
                line = line[len(srcon_pref):].strip()
                key, time, cmd = line.split(b' ', 2)
                self.server.queue.append(cmd)


class FakeXonServer:
    def __init__(self, loop, listen_port=26005):
        self.transport = None
        self.protocol = None
        self.loop = loop
        self.listen_port = listen_port
        self.received = []
        self.queue = []

    def reset(self):
        self.queue = []

    async def start_server(self):
        RconProtocol.server = self
        self.transport, self.protocol = await self.loop.create_datagram_endpoint(
            RconProtocol, local_addr=('127.0.0.1', self.listen_port))




