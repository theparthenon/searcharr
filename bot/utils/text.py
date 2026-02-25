"""
Searcharr
Sonarr, Radarr & Readarr Telegram Bot
Text Processing Utilities
By Todd Roberts
https://github.com/toddrob99/searcharr
"""
from bot.utils.log import set_up_logger
from config.language import translate as _translate

logger = set_up_logger("text")


def strip_entities(message):
    """Strip Telegram entities from a message.
    
    Args:
        message: The Telegram message
        
    Returns:
        str: The message text with entities removed
    """
    text = message.text
    entities = message.parse_entities()
    
    logger.debug(f"Entities in message: {entities}")
    
    for v in entities.values():
        text = text.replace(v, "")
    
    text = text.replace("  ", "").strip()
    logger.debug(f"Stripped entities from message [{message.text}]: [{text}]")
    
    return text


def translate(key, **kwargs):
    """Translate a key using the loaded language data.
    
    This is a convenience wrapper for the language module's translate function.
    
    Args:
        key (str): The translation key
        **kwargs: Format arguments
        
    Returns:
        str: The translated string
    """
    return _translate(key, **kwargs)