#!/usr/bin/env python3
"""
Searcharr
Sonarr, Radarr & Readarr Telegram Bot
By Todd Roberts
https://github.com/toddrob99/searcharr
"""
import argparse

from bot.searcharr_bot import SearcharrBot
from config import settings
from bot.utils.log import set_up_logger

__version__ = "3.3.0"

def parse_args():
    parser = argparse.ArgumentParser(
        prog="Searcharr", description="Start the Searcharr Bot."
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        dest="verbose",
        help="Enable debug logging.",
    )
    parser.add_argument(
        "--console-logging",
        "-c",
        action="store_true",
        dest="console_logging",
        help="Enable console logging.",
    )
    parser.add_argument(
        "--dev",
        "-d",
        action="store_true",
        dest="dev_mode",
        help="Enable developer mode, which will result in more exceptions being raised instead of handled.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    logger = set_up_logger("searcharr", args.verbose, args.console_logging)
    
    logger.info(f"Searcharr v{__version__} - Starting...")
    
    # Initialize and run the bot
    bot = SearcharrBot(
        token=settings.tgram_token,
        dev_mode=args.dev_mode,
        verbose=args.verbose
    )
    
    bot.run()