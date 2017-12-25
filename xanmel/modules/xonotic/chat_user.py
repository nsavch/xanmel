from xanmel import ChatUser


class XonoticChatUser(ChatUser):
    user_type = 'xonotic'

    def __init__(self, *args, **kwargs):
        super(XonoticChatUser, self).__init__(*args, **kwargs)
        self.server = self.properties['rcon_server']
        self.botnick = self.server.config['botnick']
        self.number2 = None
        for number2, player in self.server.players.players_by_number2.items():
            if player.nickname == self.properties['raw_nickname']:
                if self.number2 is None:
                    self.number2 = number2
                else:
                    # Duplicate nickname, can't find who sent the msg
                    self.number2 = None
                    break

    def unique_id(self):
        return self.properties['raw_nickname']

    async def private_reply(self, message, **kwargs):
        if self.number2:
            with self.server.sv_adminnick(self.botnick):
                if isinstance(message, list):
                    for i in message:
                        self.server.send('tell #%s %s' % (self.number2, i))
                else:
                    self.server.send('tell #%s %s' % (self.number2, message))

    async def public_reply(self, message, **kwargs):
        if not isinstance(message, list):
            message = [message]
        for i in message:
            self.server.say(i, nick=self.botnick)