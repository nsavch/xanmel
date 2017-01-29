from xanmel import Module
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

    def setup_event_generators(self):
        for i in self.servers:
            self.loop.create_task(i.check_connection())
