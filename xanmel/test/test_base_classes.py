import asyncio

from xanmel.base_classes import Xanmel


def test_module_loading():
    xanmel = Xanmel(loop=asyncio.get_event_loop(), config_path='example_config.yaml')
    xanmel.load_modules()
    assert len(xanmel.modules) == 2, xanmel.modules
