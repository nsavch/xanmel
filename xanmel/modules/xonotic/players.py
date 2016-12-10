from xanmel.utils import current_time


class Player:
    def __init__(self, nickname, number1, number2, ip_address):
        self.nickname = nickname
        self.number1 = number1
        self.number2 = number2
        self.ip_address = ip_address
        self.join_timestamp = None

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

    def join(self, player):
        if player.number2 in self.players_by_number2:
            old_player = self.players_by_number2[player.number2]
            old_player.number1 = player.number1
            old_player.nickname = player.nickname
            old_player.ip_address = player.ip_address
            old_player.join_timestamp = player.join_timestamp
            try:
                del self.players_by_number1[old_player.number1]
            except IndexError:
                pass
            self.players_by_number1[old_player.number1] = old_player
            return
        else:
            self.players_by_number1[player.number1] = player
            self.players_by_number2[player.number2] = player
            player.join_timestamp = current_time()
            return player

    def part(self, number1):
        player = self.players_by_number1[number1]
        try:
            del self.players_by_number1[player.number1]
            del self.players_by_number2[player.number2]
        except KeyError:
            pass
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
        return repr(list(self.players_by_number1.items()))
