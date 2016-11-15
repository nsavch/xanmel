import asyncio
import logging.config
import warnings

from xanmel.modules.posix.events import StdinInput
from xanmel.modules.posix.handlers import EchoHandler

warnings.simplefilter('default')
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


loop = asyncio.get_event_loop()
loop.set_debug(True)
loop.event_handlers = []


def main():
    logger.info('Starting event loop...')
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        loop.stop()
        loop.close()


if __name__ == '__main__':
    main()
