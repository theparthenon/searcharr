"""
Searcharr
Sonarr, Radarr & Readarr Telegram Bot
Language Management
By Todd Roberts
https://github.com/toddrob99/searcharr
"""
import os
import yaml

from bot.utils.log import set_up_logger
from config import settings

logger = set_up_logger("language", False, False)

# Module-level variables to store loaded language data
_lang = None
_lang_default = None


def load_language(lang_ietf=None):
    """Load language data from a YAML file.
    
    Args:
        lang_ietf (str, optional): Language code (e.g., "en-us"). Defaults to None.
        
    Returns:
        dict: The loaded language data
    """
    global _lang, _lang_default
    
    # Use setting if not specified
    if not lang_ietf:
        if not hasattr(settings, "searcharr_language"):
            logger.warning(
                "No language defined! Defaulting to en-us. Please add searcharr_language to settings.py if you want another language, where the value is a filename (without .yml) in the lang folder."
            )
            settings.searcharr_language = "en-us"
        lang_ietf = settings.searcharr_language
    
    # Base path for language files
    base_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    lang_path = os.path.join(base_dir, "lang", f"{lang_ietf}.yml")

    logger.debug(f"Attempting to load language file: {lang_path}...")
    
    try:
        with open(lang_path, mode="r", encoding="utf-8") as y:
            _lang = yaml.load(y, Loader=yaml.SafeLoader)
    except FileNotFoundError:
        logger.error(
            f"Error loading {lang_path}. Confirm searcharr_language in settings.py has a corresponding yml file in the lang subdirectory. Using default (English) language file."
        )
        default_path = os.path.join(base_dir, "lang", "en-us.yml")
        with open(default_path, "r") as y:
            _lang = yaml.load(y, Loader=yaml.SafeLoader)
    
    # Also load English as fallback if we're using a different language
    if _lang.get("language_ietf") != "en-us" and _lang_default is None:
        default_path = os.path.join(base_dir, "lang", "en-us.yml")
        with open(default_path, "r") as y:
            _lang_default = yaml.load(y, Loader=yaml.SafeLoader)
    
    return _lang


def translate(key, **kwargs):
    """Translate a key using the loaded language data.
    
    Args:
        key (str): The translation key
        **kwargs: Format arguments
        
    Returns:
        str: The translated string
    """
    global _lang, _lang_default
    
    # Ensure languages are loaded
    if _lang is None:
        load_language()
    
    # Try to get translation from primary language
    if t := _lang.get(key):
        return t.format(**kwargs)
    else:
        logger.error(f"No translation found for key [{key}]!")
        
        # Try fallback language if available
        if _lang.get("language_ietf") != "en-us" and _lang_default is not None:
            if t := _lang_default.get(key):
                logger.info(f"Using default language for key [{key}]...")
                return t.format(**kwargs)
    
    return "(translation not found)"