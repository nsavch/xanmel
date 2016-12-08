class Player:
    def __init__(self, nickname, number1, number2, ip_address):
        self.nickname = nickname
        self.number1 = number1
        self.number2 = number2
        self.ip_address = ip_address

    @property
    def is_bot(self):
        return self.ip_address == 'botclient'


class PlayerManager:
    def __init__(self):
        self.players_by_number1 = {}
        self.players_by_number2 = {}
        self.max = 0

    def add(self, player):
        self.players_by_number1[player.number1] = player
        self.players_by_number2[player.number2] = player

    def part(self, number2):
        player = self.players_by_number2[number2]
        try:
            del self.players_by_number1[player.number1]
            del self.players_by_number2[player.number2]
        except KeyError:
            pass
        return player

    def clear(self):
        self.players_by_number1 = {}
        self.players_by_number2 = {}

    def name_change(self, number2, new_nickname):
        player = self.players_by_number2[number2]
        player.nickname = new_nickname
        return player
