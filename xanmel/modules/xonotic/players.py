import geoip2.errors

from xanmel.modules.xonotic.colors import Color
from xanmel.utils import current_time


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

    def name_change(self, number1, new_nickname):
        player = self.players_by_number1[number1]
        old_nickname = player.nickname
        player.nickname = new_nickname
        return old_nickname, player

    def __str__(self):
        return ', '.join(['%s: %s' % (n1, Color.dp_to_none(p.nickname).decode('utf8'))
                          for n1, p in self.players_by_number1.items()])
