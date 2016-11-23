class BaseAction(object):
    # TODO: include list of required/optional properties
    def __init__(self, module, **kwargs):
        self.module = module
        self.properties = kwargs

    def run(self):
        raise NotImplementedError()


class BaseModule(object):
    def __init__(self, loop, config):
        self.config = config
        self.loop = loop

    def setup_event_generators(self):
        pass

    def setup_event_handlers(self):
        pass
