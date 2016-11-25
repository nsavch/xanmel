import importlib
import os
from collections import defaultdict

import yaml


class Xanmel:
    """
    The basic metadata holder. There should be only 1 instance per running process of this class.
    """
    modules = {}
    handlers = defaultdict(list)
    events = {}

    def __init__(self, loop, config_path):
        self.loop = loop
        with open(os.path.expanduser(config_path), 'r') as config_file:
            self.config = yaml.load(config_file)

    def load_modules(self):
        for module_path, module_config in self.config.items():
            module_pkg_name, module_name = module_path.rsplit('.', 1)
            module_pkg = importlib.import_module(module_pkg_name)
            module = getattr(module_pkg, module_name)(self, module_config)
            module.setup_event_generators()
            module.setup_event_handlers()
            self.modules[module_path] = module


class Module:
    """
    Class representing Xanmel module. Modules are used to group functionality into different packages.

    Each xanmel module may provide the following facilities:

      * event types
      * event generators - functions which listen to the outside world and generate corresponding xanmel events
      * actions - function which alters the outside world
      * handler - function which is called when an event occur and may call zero or more actions

    Each module has its own config section.
    """

    def __init__(self, xanmel, config):
        self.config = config
        self.xanmel = xanmel
        self.loop = xanmel.loop

    def setup_event_generators(self):
        pass


class Action:
    # TODO: include list of required/optional properties
    def __init__(self, module, **kwargs):
        self.module = module
        self.properties = kwargs

    def run(self):
        raise NotImplementedError()


class Handler:
    listen_to_events = []

    def __init__(self, module):
        self.module = module

    async def handle(self, event):
        pass
