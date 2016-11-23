import importlib
import yaml


def load_modules(config_path, loop):
    with open(config_path, 'r') as config_file:
        config = yaml.load(config_file)
    for module_path, module_config in config.items():
        module_lib = importlib.import_module(module_path)
        module = module_lib.Module(loop, module_config)
        module.setup_event_generators()
        module.setup_event_handlers()
