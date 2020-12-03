import dotenv
from telegram_channel_duplicator.client import Client
from loguru import logger
import colorama
import os
import sys


if __name__ == '__main__':
    dotenv.load_dotenv()

    logger.remove()
    logger.add(
        sys.stderr,
        format="<cyan>{time}</cyan> | <lvl>{level}</lvl> - <lvl>{message}</lvl>",
        colorize=True,
        level='DEBUG',
    )

    logger.add(
        os.path.join('logs', 'debug.log'),
        format="{time} {level} {message}",
        level='DEBUG',
        rotation='3mb',
        compression='zip'
    )
    logger.info(colorama.Fore.LIGHTYELLOW_EX+'Created by https://github.com/deFiss')

    Client()
