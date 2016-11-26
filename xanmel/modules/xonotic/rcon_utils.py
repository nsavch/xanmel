import hashlib
import hmac
import re

import time

QUAKE_PACKET_HEADER = b'\xFF' * 4
RCON_RESPONSE_HEADER = QUAKE_PACKET_HEADER + b'n'
CHALLENGE_PACKET = QUAKE_PACKET_HEADER + b'getchallenge'
CHALLENGE_RESPONSE_HEADER = QUAKE_PACKET_HEADER + b'challenge '
MASTER_RESPONSE_HEADER = QUAKE_PACKET_HEADER + b'getserversResponse'
PING_Q2_PACKET = QUAKE_PACKET_HEADER + b'ping'
PONG_Q2_PACKET = QUAKE_PACKET_HEADER + b'ack'
PING_Q3_PACKET = b'ping'
PONG_Q3_PACKET = QUAKE_PACKET_HEADER + b'disconnect'
QUAKE_STATUS_PACKET = QUAKE_PACKET_HEADER + b'getstatus'
STATUS_RESPONSE_HEADER = QUAKE_PACKET_HEADER + b'statusResponse\n'
ADDR_STR_RE = re.compile(r"""
    ^(?:
        (?P<host>[^:]+)               # ipv4 address or host name
        |\[(?P<host6>[a-zA-Z0-9:]+)\] # ipv6 address in square brackets
    )                                 # end of host part
    (?::(?P<port>\d+))?$              # optional port part
    """, re.VERBOSE)


def ensure_bytes(something):
    if not isinstance(something, bytes):
        return str(something).encode('ascii')
    return something


def md4(*args, **kwargs):
    return hashlib.new('MD4', *args, **kwargs)


def hmac_md4(key, msg):
    return hmac.new(key, msg, md4)


def rcon_nosecure_packet(password, command):
    return QUAKE_PACKET_HEADER + ensure_bytes('rcon {password} {command}'.format(password=password, command=command))


def rcon_secure_time_packet(password, command):
    password = ensure_bytes(password)
    cur_time = time.time()
    key = hmac_md4(password, ensure_bytes("{time:6f} {command}"
                   .format(time=cur_time, command=command))).digest()
    return b''.join([
        QUAKE_PACKET_HEADER,
        b'srcon HMAC-MD4 TIME ',
        key,
        ensure_bytes(' {time:6f} {command}'.format(time=cur_time, command=command))
    ])


def parse_challenge_response(response):
    l = len(CHALLENGE_RESPONSE_HEADER)
    return response[l:l+11]


def rcon_secure_challenge_packet(password, challenge, command):
    password = ensure_bytes(password)
    challenge = ensure_bytes(challenge)
    command = ensure_bytes(command)
    hmac_key = b' '.join([challenge, command])
    key = hmac_md4(password, hmac_key).digest()
    return b''.join([
        QUAKE_PACKET_HEADER,
        b'srcon HMAC-MD4 CHALLENGE ',
        key,
        b' ',
        challenge,
        b' ',
        command
    ])


def parse_rcon_response(packet):
    l = len(RCON_RESPONSE_HEADER)
    return packet[l:]


def parse_server_vars(server_vars):
    if not server_vars.startswith(b'\\'):
        raise ValueError('Invalid server vars')

    values = server_vars.split(b'\\')[1:]
    return dict(zip(values[::2], values[1::2]))


class Player:

    PLAYER_RE = re.compile(
        b'^(?P<frags>-?\d+) (?P<ping>-?\d+) "(?P<name>.*?)"$'
    )
    __slots__ = ('frags', 'ping', 'name')

    def __init__(self, frags, ping, name):
        self.frags = frags
        self.ping = ping
        self.name = name

    def __repr__(self):
        return '<Player({frags}, {ping}, {name})>'.format(name=repr(self.name), frags=self.frags, ping=self.ping)

    @classmethod
    def from_dict(cls, dct):
        return cls(int(dct['frags']), int(dct['ping']), dct['name'])

    @classmethod
    def parse_player(cls, player_data):
        m = cls.PLAYER_RE.match(player_data)
        if m is None:
            raise ValueError('Bad player data')

        return cls.from_dict(m.groupdict())


def parse_status_packet(status_packet, player_factory=Player.parse_player):
    data = status_packet[len(STATUS_RESPONSE_HEADER):]
    parts = data.split(b'\n')[:-1]  # split server vars and player
    # sections and remove last '\n' symbol
    if len(parts) < 1:
        raise ValueError("Bad packet")

    server_vars, players_dat = parts[0], parts[1:]
    players = list(player_factory(playerd) for playerd in players_dat)
    return parse_server_vars(server_vars), players
