import asyncio

from bottom.unpack import unpack_command
DELIM = b"\r\n"
DELIM_COMPAT = b"\n"


class IRCProtocol(asyncio.Protocol):
    transport = None
    buffer = b""

    def connection_made(self, transport):
        peername = transport.get_extra_info('peername')
        print('Connection from {}'.format(peername))
        self.transport = transport

    def data_received(self, data):
        self.buffer += data
        # All but the last result of split should be pushed into the
        # client.  The last will be b"" if the buffer ends on b"\n"
        *lines, self.buffer = self.buffer.split(DELIM_COMPAT)
        for line in lines:
            message = line.decode('utf8', "ignore").strip()
            try:
                event, kwargs = unpack_command(message)
                print(event, kwargs)
            except ValueError:
                print("Failed to parse line >>> {}".format(message))


class FakeIRCServer:
    transport = None

    def __init__(self, loop, listen_port=6667):
        self.loop = loop
        self.listen_port = listen_port
        loop.create_task(self.start_server())

    async def start_server(self):
        self.transport = await self.loop.create_server(IRCProtocol, '127.0.0.1', self.listen_port)
        self.transport.server = self

    def send(self):
        pass

    async def expect(self, data):
        pass

    async def unexpect(self, data):
        pass
