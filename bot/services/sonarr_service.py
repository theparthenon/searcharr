"""
Searcharr
Sonarr, Radarr & Readarr Telegram Bot
Sonarr Service Configuration
By Todd Roberts
https://github.com/toddrob99/searcharr
"""
from bot.utils.log import set_up_logger
from config import settings

logger = set_up_logger("sonarr_service", False, False)


def configure_sonarr(client):
    """Configure the Sonarr client.
    
    Args:
        client: The Sonarr client
        
    Returns:
        object: The configured Sonarr client
    """
    # Configure quality profiles
    client = _configure_quality_profiles(client)
    
    # Configure root folders
    client = _configure_root_folders(client)
    
    # Configure tags
    _configure_tags(client)
    
    # Check service-specific settings
    _check_service_settings()
    
    return client


def _configure_quality_profiles(client):
    """Configure quality profiles for Sonarr.
    
    Args:
        client: The Sonarr client
        
    Returns:
        object: The Sonarr client with configured quality profiles
    """
    quality_profiles = []
    setting_name = "sonarr_quality_profile_id"
    
    profile_setting = getattr(settings, setting_name, [])
    if not isinstance(profile_setting, list):
        setattr(settings, setting_name, [profile_setting])
        profile_setting = [profile_setting]
        
    for i in profile_setting:
        logger.debug(f"Looking up/validating Sonarr quality profile id for [{i}]...")
        foundProfile = client.lookup_quality_profile(i)
        
        if not foundProfile:
            logger.error(f"Sonarr quality profile id/name [{i}] is invalid!")
        else:
            logger.debug(f"Found Sonarr quality profile for [{i}]: [{foundProfile}]")
            quality_profiles.append(foundProfile)
            
    if not quality_profiles:
        logger.warning(
            f"No valid Sonarr quality profile(s) provided! "
            f"Using all of the quality profiles found in Sonarr: {client._quality_profiles}"
        )
    else:
        logger.debug(
            f"Using the following Sonarr quality profile(s): "
            f"{[(x['id'], x['name']) for x in quality_profiles]}"
        )
        client._quality_profiles = quality_profiles
        
    return client


def _configure_root_folders(client):
    """Configure root folders for Sonarr.
    
    Args:
        client: The Sonarr client
        
    Returns:
        object: The Sonarr client with configured root folders
    """
    setting_name = "sonarr_series_paths"
    
    root_folders = []
    
    if not hasattr(settings, setting_name):
        setattr(settings, setting_name, [])
        logger.warning(
            f"No {setting_name} setting detected. Please set one in settings.py "
            f"({setting_name}=[\"/path/1\", \"/path/2\"]). Proceeding with all root folders configured in Sonarr."
        )
        
    paths_setting = getattr(settings, setting_name)
    if not isinstance(paths_setting, list):
        setattr(settings, setting_name, [paths_setting])
        paths_setting = [paths_setting]
        
    for i in paths_setting:
        logger.debug(f"Looking up/validating Sonarr root folder for [{i}]...")
        foundPath = client.lookup_root_folder(i)
        
        if not foundPath:
            logger.error(f"Sonarr root folder path/id [{i}] is invalid!")
        else:
            logger.debug(f"Found Sonarr root folder for [{i}]: [{foundPath}]")
            root_folders.append(foundPath)
            
    if not root_folders:
        logger.warning(
            f"No valid Sonarr root folder(s) provided! "
            f"Using all of the root folders found in Sonarr: {client._root_folders}"
        )
    else:
        logger.debug(
            f"Using the following Sonarr root folder(s): "
            f"{[(x['id'], x['path']) for x in root_folders]}"
        )
        client._root_folders = root_folders
        
    return client


def _configure_tags(client):
    """Configure tags for Sonarr.
    
    Args:
        client: The Sonarr client
    """
    # Process forced tags
    forced_tags = getattr(settings, "sonarr_forced_tags", [])
    
    for t in forced_tags:
        if t_id := client.get_tag_id(t):
            logger.debug(f"Tag id [{t_id}] for forced Sonarr tag [{t}]")
            
    # Process user-selectable tags
    user_tags = getattr(settings, "sonarr_user_selectable_tags", [])
    
    for t in user_tags:
        if t_id := client.get_tag_id(t):
            logger.debug(f"Tag id [{t_id}] for user-selectable Sonarr tag [{t}]")


def _check_service_settings():
    """Check and set defaults for Sonarr settings."""
    # Check tag_with_username setting
    if not hasattr(settings, "sonarr_tag_with_username"):
        settings.sonarr_tag_with_username = True
        logger.warning(
            "No sonarr_tag_with_username setting found. Please add sonarr_tag_with_username to settings.py "
            "(sonarr_tag_with_username=True or sonarr_tag_with_username=False). Defaulting to True."
        )
        
    # Check command aliases setting
    if not hasattr(settings, "sonarr_series_command_aliases"):
        settings.sonarr_series_command_aliases = ["series"]
        logger.warning(
            "No sonarr_series_command_aliases setting found. Please add sonarr_series_command_aliases to settings.py "
            '(e.g. sonarr_series_command_aliases=["series", "s"]). '
            'Defaulting to ["series"].'
        )
        
    # Check forced tags setting
    if not hasattr(settings, "sonarr_forced_tags"):
        settings.sonarr_forced_tags = []
        logger.warning(
            "No sonarr_forced_tags setting found. Please add sonarr_forced_tags to settings.py "
            '(e.g. sonarr_forced_tags=["tag-1", "tag-2"]) if you want specific tags '
            "added to each series. Defaulting to empty list ([])."
        )
        
    # Check user_selectable_tags setting
    if not hasattr(settings, "sonarr_user_selectable_tags"):
        settings.sonarr_user_selectable_tags = []
        logger.warning(
            "No sonarr_user_selectable_tags setting found. Please add sonarr_user_selectable_tags to settings.py "
            '(e.g. sonarr_user_selectable_tags=["tag-1", "tag-2"]) if you want to limit the tags '
            "a user can select. Defaulting to empty list ([]), which will present the user with all tags."
        )
        
    # Check allow_user_to_select_tags setting
    if not hasattr(settings, "sonarr_allow_user_to_select_tags"):
        settings.sonarr_allow_user_to_select_tags = False
        logger.warning(
            "No sonarr_allow_user_to_select_tags setting found. Please add sonarr_allow_user_to_select_tags to settings.py "
            "(e.g. sonarr_allow_user_to_select_tags=True) "
            "if you want users to be able to select tags "
            "when adding a series. Defaulting to False."
        )
        
    # Check season_monitor_prompt setting
    if not hasattr(settings, "sonarr_season_monitor_prompt"):
        settings.sonarr_season_monitor_prompt = False
        logger.warning(
            "No sonarr_season_monitor_prompt setting found. Please add sonarr_season_monitor_prompt to settings.py "
            "(e.g. sonarr_season_monitor_prompt=True if you want users to choose whether to monitor "
            "all/first/latest season(s). Defaulting to False."
        )