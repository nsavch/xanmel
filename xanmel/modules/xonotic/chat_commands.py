from xanmel import CommandContainer, ChatCommand

from .colors import Color


class XonCommands(CommandContainer):
    pass


class Who(ChatCommand):
    prefix = 'who'
    parent = XonCommands

    async def run(self, user, message, is_private=True):
        rcon_server = self.parent.properties['rcon_server']
        if rcon_server.players.current == 0:
            reply = 'Server is empty'
        else:
            player_names = []
            for player in rcon_server.players.players_by_number1.values():
                player_names.append(Color.dp_to_irc(player.nickname).decode('utf8'))
            reply = ' | '.join(player_names)

        await user.reply(rcon_server.config['out_prefix'] + reply, is_private)
