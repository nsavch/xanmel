import asyncio

from bottom.pack import pack_command as orig_pack_command
from bottom.unpack import unpack_command as orig_unpack_command, split_line, synonym
DELIM = b"\r\n"
DELIM_COMPAT = b"\n"


def unpack_command(msg):
    prefix, command, params = split_line(msg.strip())
    command = synonym(command)
    kwargs = {}

    if command == 'USER':
        kwargs['user'] = params[0]
    else:
        command, kwargs = orig_unpack_command(msg)
    return command, kwargs


def pack_command(command, **kwargs):
    command = str(command).upper()
    if command == 'RPL_ENDOFMOTD':
        return 'RPL_ENDOFMOTD :End of MOTD command'
    else:
        return orig_pack_command(command, **kwargs)


class IRCProtocol(asyncio.Protocol):
    transport = None
    buffer = b""
    queue = None

    def connection_made(self, transport):
        peername = transport.get_extra_info('peername')
        print('IRC Connection from {}'.format(peername))
        self.transport = transport
        self.server.connected = True
        self.server.protocol = self

    def connection_lost(self, exc):
        print('IRC Connection lost')
        self.server.connected = False

    def send_command(self, command, **kwargs):
        packed_command = pack_command(command, **kwargs).strip().encode('utf8')
        self.transport.write(packed_command + DELIM)

    def data_received(self, data):
        print('Data received', ascii(data))
        self.buffer += data
        # All but the last result of split should be pushed into the
        # client.  The last will be b"" if the buffer ends on b"\n"
        *lines, self.buffer = self.buffer.split(DELIM_COMPAT)
        for line in lines:
            message = line.decode('utf8', "ignore").strip()
            try:
                event, kwargs = unpack_command(message)
                self.server.received.append((event, kwargs))
            except ValueError:
                print("Failed to parse line >>> {!r}".format(message))


class FakeIRCServer:
    protocol = None
    server = None

    def __init__(self, loop, listen_port=6667):
        self.loop = loop
        self.connected = False
        self.listen_port = listen_port
        self.received = []
        self.queue = []
        self.connected = False

    def reset(self):
        self.queue = []

    async def start_server(self):
        IRCProtocol.server = self
        self.server = await self.loop.create_server(IRCProtocol, '127.0.0.1', self.listen_port)

    async def stop_server(self):
        self.server.close()
        self.protocol.transport.close()
        await self.server.wait_closed()

    def expect_connection(self):
        self.queue.append(('c', None))

    def expect_disconnetion(self):
        self.queue.append(('d', None))

    def send(self, **kwargs):
        self.queue.append(('o', kwargs))

    def expect(self, **kwargs):
        self.queue.append(('i', kwargs))

    def unexpect(self, data):
        self.queue.append(('x', data))

    async def execute(self):
        for t, d in self.queue:
            if t == 'c':
                timeout = 10
                while not self.connected:
                    await asyncio.sleep(1)
                    timeout -= 1
                    if timeout == 0:
                        raise RuntimeError('Bot not connected to IRC Server, not expected that!')
            elif t == 'd':
                timeout = 10
                while self.connected:
                    await asyncio.sleep(1)
                    timeout -= 1
                    if timeout == 0:
                        raise RuntimeError('Bot did not disconnect from IRC Server, not expected that!')
            elif t == 'o':
                self.protocol.send_command(d['command'], **d['kwargs'])
            elif t == 'i':
                timeout = 5
                found = False
                for cmd, kwargs in self.received:
                    if cmd == d['command'] and kwargs == d['kwargs']:
                        found = True
                if timeout == 0:
                    raise RuntimeError('Expected %s, Received %s' % (d, self.received))
                if found:
                    continue
                else:
                    await asyncio.sleep(1)
                    timeout -= 1
