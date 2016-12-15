from xanmel import ChatUser


class XonoticChatUser(ChatUser):
    user_type = 'xonotic'

    def __init__(self, *args, **kwargs):
        super(XonoticChatUser, self).__init__(*args, **kwargs)
        self.server = self.properties['rcon_server']
        self.botnick = self.server.config['botnick']

    def unique_id(self):
        return self.properties['raw_nickname']

    async def private_reply(self, message, **kwargs):
        pass

    async def public_reply(self, message, **kwargs):
        if self.server.config['say_type'] == 'ircmsg':
            self.server.send('sv_cmd ircmsg [BOT] %s^7: %s' % (self.botnick, message))
        else:
            with self.server.sv_adminnick(self.botnick):
                self.server.send('say %s' % message)
