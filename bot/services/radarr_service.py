"""
Searcharr
Sonarr, Radarr & Readarr Telegram Bot
Radarr Service Configuration
By Todd Roberts
https://github.com/toddrob99/searcharr
"""
from bot.utils.log import set_up_logger
import settings

logger = set_up_logger("radarr_service")


def configure_radarr(client):
    """Configure the Radarr client.
    
    Args:
        client: The Radarr client
        
    Returns:
        object: The configured Radarr client
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
    """Configure quality profiles for Radarr.
    
    Args:
        client: The Radarr client
        
    Returns:
        object: The Radarr client with configured quality profiles
    """
    quality_profiles = []
    setting_name = "radarr_quality_profile_id"
    
    profile_setting = getattr(settings, setting_name, [])
    if not isinstance(profile_setting, list):
        setattr(settings, setting_name, [profile_setting])
        profile_setting = [profile_setting]
        
    for i in profile_setting:
        logger.debug(f"Looking up/validating Radarr quality profile id for [{i}]...")
        foundProfile = client.lookup_quality_profile(i)
        
        if not foundProfile:
            logger.error(f"Radarr quality profile id/name [{i}] is invalid!")
        else:
            logger.debug(f"Found Radarr quality profile for [{i}]: [{foundProfile}]")
            quality_profiles.append(foundProfile)
            
    if not quality_profiles:
        logger.warning(
            f"No valid Radarr quality profile(s) provided! "
            f"Using all of the quality profiles found in Radarr: {client._quality_profiles}"
        )
    else:
        logger.debug(
            f"Using the following Radarr quality profile(s): "
            f"{[(x['id'], x['name']) for x in quality_profiles]}"
        )
        client._quality_profiles = quality_profiles
        
    return client


def _configure_root_folders(client):
    """Configure root folders for Radarr.
    
    Args:
        client: The Radarr client
        
    Returns:
        object: The Radarr client with configured root folders
    """
    setting_name = "radarr_movie_paths"
    
    root_folders = []
    
    if not hasattr(settings, setting_name):
        setattr(settings, setting_name, [])
        logger.warning(
            f"No {setting_name} setting detected. Please set one in settings.py "
            f"({setting_name}=[\"/path/1\", \"/path/2\"]). Proceeding with all root folders configured in Radarr."
        )
        
    paths_setting = getattr(settings, setting_name)
    if not isinstance(paths_setting, list):
        setattr(settings, setting_name, [paths_setting])
        paths_setting = [paths_setting]
        
    for i in paths_setting:
        logger.debug(f"Looking up/validating Radarr root folder for [{i}]...")
        foundPath = client.lookup_root_folder(i)
        
        if not foundPath:
            logger.error(f"Radarr root folder path/id [{i}] is invalid!")
        else:
            logger.debug(f"Found Radarr root folder for [{i}]: [{foundPath}]")
            root_folders.append(foundPath)
            
    if not root_folders:
        logger.warning(
            f"No valid Radarr root folder(s) provided! "
            f"Using all of the root folders found in Radarr: {client._root_folders}"
        )
    else:
        logger.debug(
            f"Using the following Radarr root folder(s): "
            f"{[(x['id'], x['path']) for x in root_folders]}"
        )
        client._root_folders = root_folders
        
    return client


def _configure_tags(client):
    """Configure tags for Radarr.
    
    Args:
        client: The Radarr client
    """
    # Process forced tags
    forced_tags = getattr(settings, "radarr_forced_tags", [])
    
    for t in forced_tags:
        if t_id := client.get_tag_id(t):
            logger.debug(f"Tag id [{t_id}] for forced Radarr tag [{t}]")
            
    # Process user-selectable tags
    user_tags = getattr(settings, "radarr_user_selectable_tags", [])
    
    for t in user_tags:
        if t_id := client.get_tag_id(t):
            logger.debug(f"Tag id [{t_id}] for user-selectable Radarr tag [{t}]")


def _check_service_settings():
    """Check and set defaults for Radarr settings."""
    # Check tag_with_username setting
    if not hasattr(settings, "radarr_tag_with_username"):
        settings.radarr_tag_with_username = True
        logger.warning(
            "No radarr_tag_with_username setting found. Please add radarr_tag_with_username to settings.py "
            "(radarr_tag_with_username=True or radarr_tag_with_username=False). Defaulting to True."
        )
        
    # Check command aliases setting
    if not hasattr(settings, "radarr_movie_command_aliases"):
        settings.radarr_movie_command_aliases = ["movie"]
        logger.warning(
            "No radarr_movie_command_aliases setting found. Please add radarr_movie_command_aliases to settings.py "
            '(e.g. radarr_movie_command_aliases=["movie", "m"]). '
            'Defaulting to ["movie"].'
        )
        
    # Check forced tags setting
    if not hasattr(settings, "radarr_forced_tags"):
        settings.radarr_forced_tags = []
        logger.warning(
            "No radarr_forced_tags setting found. Please add radarr_forced_tags to settings.py "
            '(e.g. radarr_forced_tags=["tag-1", "tag-2"]) if you want specific tags '
            "added to each movie. Defaulting to empty list ([])."
        )
        
    # Check user_selectable_tags setting
    if not hasattr(settings, "radarr_user_selectable_tags"):
        settings.radarr_user_selectable_tags = []
        logger.warning(
            "No radarr_user_selectable_tags setting found. Please add radarr_user_selectable_tags to settings.py "
            '(e.g. radarr_user_selectable_tags=["tag-1", "tag-2"]) if you want to limit the tags '
            "a user can select. Defaulting to empty list ([]), which will present the user with all tags."
        )
        
    # Check allow_user_to_select_tags setting
    if not hasattr(settings, "radarr_allow_user_to_select_tags"):
        settings.radarr_allow_user_to_select_tags = True
        logger.warning(
            "No radarr_allow_user_to_select_tags setting found. Please add radarr_allow_user_to_select_tags to settings.py "
            "(e.g. radarr_allow_user_to_select_tags=False) "
            "if you do not want users to be able to select tags "
            "when adding a movie. Defaulting to True."
        )
        
    # Check min_availability setting
    if not hasattr(settings, "radarr_min_availability"):
        settings.radarr_min_availability = "released"
        logger.warning(
            'No radarr_min_availability setting found. Please add radarr_min_availability to settings.py '
            '(options: "released", "announced", "inCinemas"). Defaulting to "released".'
        )