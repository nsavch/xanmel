from xanmel import Module
from xanmel.modules.xonotic.rcon import RconServer


class XonoticModule(Module):
    def __init__(self, xanmel, config):
        super(XonoticModule, self).__init__(xanmel, config)
        self.servers = []
        for server in config['servers']:
            self.servers.append(RconServer(self, server))
        for i in self.servers:
            self.loop.create_task(i.connect_cmd())
            self.loop.create_task(i.connect_log())
