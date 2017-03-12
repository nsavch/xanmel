from xanmel import Event
from .colors import Color


class ServerConnect(Event):
    def __str__(self):
        return 'Server connected: %s' % self.properties['server'].host


class ServerDisconnect(Event):
    def __str__(self):
        return 'Server connected: %s' % self.properties['server'].host


class Join(Event):
    def __str__(self):
        return '%s player %s joined: %s' % (self.properties['server'].config['out_prefix'],
                                             Color.dp_to_none(self.properties['player'].nickname),
                                             self.properties['player'].ip_address)


class Part(Event):
    def __str__(self):
        return '%s player %s parted: %s' % (self.properties['server'].config['out_prefix'],
                                             Color.dp_to_none(self.properties['player'].nickname),
                                             self.properties['player'].ip_address)


class GameStarted(Event):
    def __str__(self):
        return '%s %s started on %s' % (self.properties['server'].config['out_prefix'],
                                         self.properties['gt'],
                                         self.properties['map'])


class GameEnded(Event):
    def __str__(self):
        return '%s game ended' % self.properties['server'].config['out_prefix']


class NameChange(Event):
    def __str__(self):
        return '%s %s -> %s' % (self.properties['server'].config['out_prefix'],
                                 Color.dp_to_none(self.properties['old_nickname']),
                                 Color.dp_to_none(self.properties['player'].nickname))


class ChatMessage(Event):
    log = False

    def __str__(self):
        return '%s chat message' % self.properties['server'].config['out_prefix']


class NewPlayerActive(Event):
    log = False

    def __str__(self):
        return '%s new player active' % self.properties['server'].config['out_prefix']


class MapChange(Event):
    log = False

    def __str__(self):
        return 'Map change: %s -> %s' % (self.properties['old_map'], self.properties['new_map'])


class PlayerRatedMap(Event):
    def __str__(self):
        return 'Player %s rated map %s: %s' % (Color.dp_to_none(self.properties['player'].nickname),
                                               self.properties['map_name'],
                                               self.properties['vote'])
