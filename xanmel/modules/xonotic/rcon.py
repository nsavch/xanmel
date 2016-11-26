# This file was copied from XRcon project https://github.com/bacher09/xrcon/
# Python-2 compatibility stuff was removed

import asyncio
from xanmel.modules.xonotic.rcon_utils import *


class RconProtocol(asyncio.DatagramProtocol):
    transport = None
    password = 'password'

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        if data.startswith(RCON_RESPONSE_HEADER):
            decoded = parse_rcon_response(data)
            for i in decoded.split(b'\n'):
                print('RCON RESPONSE RECEIVED: %s' % i)

    def send(self, command):
        self.transport.sendto(rcon_secure_time_packet(self.password, command))


class RconLogProtocol(asyncio.DatagramProtocol):
    transport = None
    local_port = None
    local_host = None
    password = 'password'

    def connection_made(self, transport):
        self.transport = transport
        self.local_host, self.local_port = self.transport.get_extra_info('sockname')
        self.send("sv_cmd addtolist log_dest_udp %s:%s" % (self.local_host, self.local_port))

    def datagram_received(self, data, addr):
        if data.startswith(RCON_RESPONSE_HEADER):
            decoded = parse_rcon_response(data)
            for i in decoded.split(b'\n'):
                print('LOG ITEM RECEIVED: %s' % i)

    def send(self, command):
        self.transport.sendto(rcon_secure_time_packet(self.password, command))


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    transport, protocol = loop.run_until_complete(
        loop.create_datagram_endpoint(RconProtocol, remote_addr=('127.0.0.1', 26005)))
    log_transport, log_protocol = loop.run_until_complete(
        loop.create_datagram_endpoint(RconLogProtocol, remote_addr=('127.0.0.1', 26005)))
    protocol.send('status')
    loop.run_forever()
    transport.close()
    loop.close()
