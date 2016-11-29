import asyncio
import pytest
import yaml

from xanmel.base_classes import Xanmel


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture
def transport():
    class Transport:
        def __init__(self):
            self.written = []
            self.closed = False

        def write(self, data):
            self.written.append(data)

        def close(self):
            self.closed = True
    return Transport()


@pytest.fixture
def xanmel(event_loop, mocker):
    xanmel = Xanmel(event_loop, 'example_config.yaml')
    yield xanmel


@pytest.fixture
def config():
    with open('example_config.yaml') as f:
        return yaml.load(f)


@pytest.fixture
def mocked_coroutine():
    async def dummy(*args, **kwargs):
        pass
    return dummy
