from xanmel import Module
from xanmel.modules.xonotic.chat_commands import XonCommands
from xanmel.modules.xonotic.rcon import RconServer


class XonoticModule(Module):
    db_indices = {
        'maps': {},
        'games': {}
    }

    def __init__(self, xanmel, config):
        super(XonoticModule, self).__init__(xanmel, config)
        self.servers = []
        for server in config['servers']:
            self.servers.append(RconServer(self, server))

    def after_load(self):
        raw_root = self.xanmel.cmd_root.copy()
        for i in self.servers:
            self.xanmel.cmd_root.register_container(i.command_container, i.config['cmd_prefix'])
            i.local_cmd_root = raw_root.copy()
            i.local_cmd_root.register_container(XonCommands(rcon_server=i), '')

    def setup_event_generators(self):
        for i in self.servers:
            self.loop.create_task(i.check_connection())
