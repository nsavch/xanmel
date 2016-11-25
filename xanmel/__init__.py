import asyncio
import logging.config
import warnings

from xanmel.base_classes import Xanmel

warnings.simplefilter('default')
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


loop = asyncio.get_event_loop()
loop.set_debug(True)


def main():
    logger.info('Starting event loop...')
    xanmel = Xanmel(loop=loop, config_path='example_config.yaml')
    xanmel.load_modules()
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        loop.stop()
        loop.close()


if __name__ == '__main__':
    main()
