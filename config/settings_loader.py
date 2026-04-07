"""
Searcharr
Sonarr & Radarr Telegram Bot
Settings Loader
By Todd Roberts
https://github.com/toddrob99/searcharr
"""
import importlib.util
import os
import shutil
import sys

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
_DATA_SETTINGS = os.path.join(_PROJECT_ROOT, "data", "settings.py")
_ROOT_SETTINGS = os.path.join(_PROJECT_ROOT, "settings.py")


def load_settings():
    """Load settings from data/settings.py with auto-migration from root."""
    # Auto-migrate: copy root -> data/ on first run
    if not os.path.exists(_DATA_SETTINGS) and os.path.exists(_ROOT_SETTINGS):
        os.makedirs(os.path.dirname(_DATA_SETTINGS), exist_ok=True)
        shutil.copy2(_ROOT_SETTINGS, _DATA_SETTINGS)

    # Determine which file to load
    if os.path.exists(_DATA_SETTINGS):
        settings_path = _DATA_SETTINGS
    elif os.path.exists(_ROOT_SETTINGS):
        settings_path = _ROOT_SETTINGS
    else:
        raise FileNotFoundError(
            "No settings.py found! Copy settings-sample.py to data/settings.py "
            "and configure it."
        )

    # Load and register in sys.modules so `import settings` works everywhere
    spec = importlib.util.spec_from_file_location("settings", settings_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    sys.modules["settings"] = mod
    return mod


def check_settings_migration():
    """Log warnings about settings location. Call AFTER logging is configured."""
    import logging

    logger = logging.getLogger("searcharr")

    if os.path.exists(_DATA_SETTINGS) and os.path.exists(_ROOT_SETTINGS):
        with open(_DATA_SETTINGS, "rb") as f1, open(_ROOT_SETTINGS, "rb") as f2:
            if f1.read() != f2.read():
                logger.warning(
                    "Settings have moved to data/settings.py. "
                    "Your ROOT settings.py has DIFFERENT content and is being IGNORED. "
                    "Please update data/settings.py and remove the root file "
                    "mapping from docker-compose.yml."
                )
            else:
                logger.info(
                    "Settings loaded from data/settings.py. "
                    "The root settings.py volume mapping is no longer needed "
                    "and can be safely removed from docker-compose.yml."
                )
    elif os.path.exists(_DATA_SETTINGS):
        logger.debug("Settings loaded from data/settings.py")
    else:
        logger.info(
            "Settings loaded from root settings.py (consider moving to data/)"
        )
