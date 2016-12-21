import logging
import geoip2.errors
import math

from xanmel.modules.xonotic.colors import Color
from xanmel.utils import current_time


logger = logging.getLogger(__name__)

class Player:
    def __init__(self, server, nickname, number1, number2, ip_address):
        self.server = server
        self.nickname = nickname
        self.number1 = number1
        self.number2 = number2
        self.ip_address = ip_address
        self.join_timestamp = None
        self.geo_response = None
        if not self.is_bot:
            try:
                self.geo_response = self.server.module.xanmel.geoip.city(self.ip_address)
            except (ValueError, geoip2.errors.AddressNotFoundError):
                pass

    @property
    def country(self):
        if self.geo_response:
            return self.geo_response.country.name
        else:
            return 'Unknown'

    @property
    def is_bot(self):
        return 'bot' in self.ip_address

    def __str__(self):
        return repr(self.nickname)


class PlayerManager:
    def __init__(self):
        self.players_by_number1 = {}
        self.players_by_number2 = {}
        self.elo_data = {}
        self.ip_port_to_client_id = {}
        self.number2_to_client_id = {}
        self.max = 0

    @property
    def current(self):
        c = 0
        for i in self.players_by_number2.values():
            if not i.is_bot:
                c += 1
        return c

    @property
    def bots(self):
        res = []
        for i in self.players_by_number2.values():
            if i.is_bot:
                res.append(i)
        return res

    def clear_bots(self):
        to_clear = []
        for k, v in self.players_by_number1.items():
            if v.is_bot:
                to_clear.append((k, v.number2))
        for n1, n2 in to_clear:
            try:
                del self.players_by_number1[n1]
                del self.players_by_number2[n2]
            except KeyError:
                pass

    def join(self, player):
        if player.number2 in self.players_by_number2:
            old_player = self.players_by_number2[player.number2]
            if old_player.number1 in self.players_by_number1 and self.players_by_number1[old_player.number1].number2 == player.number2:
                del self.players_by_number1[old_player.number1]
            self.players_by_number1[player.number1] = player
            self.players_by_number2[player.number2] = player
            return
        else:
            self.players_by_number1[player.number1] = player
            self.players_by_number2[player.number2] = player
            player.join_timestamp = current_time()
            return player

    def part(self, number1):
        if number1 in self.players_by_number1:
            player = self.players_by_number1[number1]
            del self.players_by_number1[player.number1]
            if player.number2 in self.players_by_number2:
                del self.players_by_number2[player.number2]
            return player

    def clear(self):
        self.players_by_number1 = {}
        self.players_by_number2 = {}

    def clear_elo(self):
        self.elo_data = {}

    def name_change(self, number1, new_nickname):
        player = self.players_by_number1[number1]
        old_nickname = player.nickname
        player.nickname = new_nickname
        return old_nickname, player

    def add_client_id(self, ip, port, client_id):
        if b'@' in client_id:
            client_id = client_id.split(b'@', 1)[0]
        client_id = client_id.decode('utf8')
        self.ip_port_to_client_id[(ip, port)] = client_id

    def update_status(self, ip, port, number2):
        if (ip, port) in self.ip_port_to_client_id:
            self.number2_to_client_id[number2] = self.ip_port_to_client_id[(ip, port)]

    def add_elo(self, elo_txt):
        current_mode = None
        elo_data = {}
        primary_id = None
        for line in elo_txt.split('\n'):
            if not line.strip():
                continue
            pref, data = line.split(' ', 1)
            if current_mode is None and pref not in ('S', 'n', 'i', 'G', 'P'):
                continue
            elif current_mode and pref == 'e':
                elo_data[current_mode] = float(data.strip('elo '))
            if pref == 'S':
                elo_data['url'] = data
            elif pref == 'n':
                elo_data['nickname'] = data
            elif pref == 'i':
                elo_data['player_id'] = data
            elif pref == 'G':
                current_mode = data.lower()
            elif pref == 'P':
                primary_id = data
        if primary_id:
            self.elo_data[primary_id] = elo_data

    def get_elo(self, number1, elo_type):
        try:
            player = self.players_by_number1[number1]
            client_id = self.number2_to_client_id[player.number2]
            elo = self.elo_data[client_id][elo_type]
            res = math.floor(elo)
        except KeyError:
            res = None
        if res is None:
            return '--'
        return res

    def __str__(self):
        return ', '.join(['%s: %s' % (n1, Color.dp_to_none(p.nickname).decode('utf8'))
                          for n1, p in self.players_by_number1.items()])
