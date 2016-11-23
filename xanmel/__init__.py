import asyncio
import logging.config
import warnings

from xanmel.loader import load_modules


warnings.simplefilter('default')
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


loop = asyncio.get_event_loop()
loop.set_debug(True)


def main():
    load_modules('example_config.yaml', loop)
    logger.info('Starting event loop...')
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        loop.stop()
        loop.close()


if __name__ == '__main__':
    main()
