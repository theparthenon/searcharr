"""
Searcharr
Sonarr & Radarr Telegram Bot
Callback Handler Package Initialization
By Todd Roberts
https://github.com/toddrob99/searcharr
"""
from bot.callbacks.callback_handler import main_callback_handler

# Import all callback handler modules to ensure they're loaded
import bot.callbacks.base
import bot.callbacks.anime_callbacks
import bot.callbacks.sonarr_callbacks
import bot.callbacks.radarr_callbacks
import bot.callbacks.user_callbacks