class BaseAction(object):
    # TODO: include list of required/optional properties
    def __init__(self, **kwargs):
        self.properties = kwargs

    def run(self):
        raise NotImplementedError()
