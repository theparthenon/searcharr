"""
Searcharr
Sonarr, Radarr & Readarr Telegram Bot
Readarr Service Configuration
By Todd Roberts
https://github.com/toddrob99/searcharr
"""
from bot.utils.log import set_up_logger
import settings

logger = set_up_logger("readarr_service")


def configure_readarr(client):
    """Configure the Readarr client.
    
    Args:
        client: The Readarr client
        
    Returns:
        object: The configured Readarr client
    """
    # Configure quality profiles
    client = _configure_quality_profiles(client)
    
    # Configure metadata profiles
    client = _configure_metadata_profiles(client)
    
    # Configure root folders
    client = _configure_root_folders(client)
    
    # Configure tags
    _configure_tags(client)
    
    # Check service-specific settings
    _check_service_settings()
    
    return client


def _configure_quality_profiles(client):
    """Configure quality profiles for Readarr.
    
    Args:
        client: The Readarr client
        
    Returns:
        object: The Readarr client with configured quality profiles
    """
    quality_profiles = []
    setting_name = "readarr_quality_profile_id"
    
    profile_setting = getattr(settings, setting_name, [])
    if not isinstance(profile_setting, list):
        setattr(settings, setting_name, [profile_setting])
        profile_setting = [profile_setting]
        
    for i in profile_setting:
        logger.debug(f"Looking up/validating Readarr quality profile id for [{i}]...")
        foundProfile = client.lookup_quality_profile(i)
        
        if not foundProfile:
            logger.error(f"Readarr quality profile id/name [{i}] is invalid!")
        else:
            logger.debug(f"Found Readarr quality profile for [{i}]: [{foundProfile}]")
            quality_profiles.append(foundProfile)
            
    if not quality_profiles:
        logger.warning(
            f"No valid Readarr quality profile(s) provided! "
            f"Using all of the quality profiles found in Readarr: {client._quality_profiles}"
        )
    else:
        logger.debug(
            f"Using the following Readarr quality profile(s): "
            f"{[(x['id'], x['name']) for x in quality_profiles]}"
        )
        client._quality_profiles = quality_profiles
        
    return client


def _configure_metadata_profiles(client):
    """Configure metadata profiles for Readarr.
    
    Args:
        client: The Readarr client
        
    Returns:
        object: The Readarr client with configured metadata profiles
    """
    metadata_profiles = []
    setting_name = "readarr_metadata_profile_id"
    
    profile_setting = getattr(settings, setting_name, [])
    if not isinstance(profile_setting, list):
        setattr(settings, setting_name, [profile_setting])
        profile_setting = [profile_setting]
        
    for i in profile_setting:
        logger.debug(f"Looking up/validating Readarr metadata profile id for [{i}]...")
        foundProfile = client.lookup_metadata_profile(i)
        
        if not foundProfile:
            logger.error(f"Readarr metadata profile id/name [{i}] is invalid!")
        else:
            logger.debug(f"Found Readarr metadata profile for [{i}]: [{foundProfile}]")
            metadata_profiles.append(foundProfile)
            
    if not metadata_profiles:
        logger.warning(
            f"No valid Readarr metadata profile(s) provided! "
            f"Using all of the metadata profiles found in Readarr: {client._metadata_profiles}"
        )
    else:
        logger.debug(
            f"Using the following Readarr metadata profile(s): "
            f"{[(x['id'], x['name']) for x in metadata_profiles]}"
        )
        client._metadata_profiles = metadata_profiles
        
    return client


def _configure_root_folders(client):
    """Configure root folders for Readarr.
    
    Args:
        client: The Readarr client
        
    Returns:
        object: The Readarr client with configured root folders
    """
    setting_name = "readarr_book_paths"
    
    root_folders = []
    
    if not hasattr(settings, setting_name):
        setattr(settings, setting_name, [])
        logger.warning(
            f"No {setting_name} setting detected. Please set one in settings.py "
            f"({setting_name}=[\"/path/1\", \"/path/2\"]). Proceeding with all root folders configured in Readarr."
        )
        
    paths_setting = getattr(settings, setting_name)
    if not isinstance(paths_setting, list):
        setattr(settings, setting_name, [paths_setting])
        paths_setting = [paths_setting]
        
    for i in paths_setting:
        logger.debug(f"Looking up/validating Readarr root folder for [{i}]...")
        foundPath = client.lookup_root_folder(i)
        
        if not foundPath:
            logger.error(f"Readarr root folder path/id [{i}] is invalid!")
        else:
            logger.debug(f"Found Readarr root folder for [{i}]: [{foundPath}]")
            root_folders.append(foundPath)
            
    if not root_folders:
        logger.warning(
            f"No valid Readarr root folder(s) provided! "
            f"Using all of the root folders found in Readarr: {client._root_folders}"
        )
    else:
        logger.debug(
            f"Using the following Readarr root folder(s): "
            f"{[(x['id'], x['path']) for x in root_folders]}"
        )
        client._root_folders = root_folders
        
    return client


def _configure_tags(client):
    """Configure tags for Readarr.
    
    Args:
        client: The Readarr client
    """
    # Process forced tags
    forced_tags = getattr(settings, "readarr_forced_tags", [])
    
    for t in forced_tags:
        if t_id := client.get_tag_id(t):
            logger.debug(f"Tag id [{t_id}] for forced Readarr tag [{t}]")
            
    # Process user-selectable tags
    user_tags = getattr(settings, "readarr_user_selectable_tags", [])
    
    for t in user_tags:
        if t_id := client.get_tag_id(t):
            logger.debug(f"Tag id [{t_id}] for user-selectable Readarr tag [{t}]")


def _check_service_settings():
    """Check and set defaults for Readarr settings."""
    # Check tag_with_username setting
    if not hasattr(settings, "readarr_tag_with_username"):
        settings.readarr_tag_with_username = True
        logger.warning(
            "No readarr_tag_with_username setting found. Please add readarr_tag_with_username to settings.py "
            "(readarr_tag_with_username=True or readarr_tag_with_username=False). Defaulting to True."
        )
        
    # Check command aliases setting
    if not hasattr(settings, "readarr_book_command_aliases"):
        settings.readarr_book_command_aliases = ["book"]
        logger.warning(
            "No readarr_book_command_aliases setting found. Please add readarr_book_command_aliases to settings.py "
            '(e.g. readarr_book_command_aliases=["book", "b"]). '
            'Defaulting to ["book"].'
        )
        
    # Check forced tags setting
    if not hasattr(settings, "readarr_forced_tags"):
        settings.readarr_forced_tags = []
        logger.warning(
            "No readarr_forced_tags setting found. Please add readarr_forced_tags to settings.py "
            '(e.g. readarr_forced_tags=["tag-1", "tag-2"]) if you want specific tags '
            "added to each book. Defaulting to empty list ([])."
        )
        
    # Check user_selectable_tags setting
    if not hasattr(settings, "readarr_user_selectable_tags"):
        settings.readarr_user_selectable_tags = []
        logger.warning(
            "No readarr_user_selectable_tags setting found. Please add readarr_user_selectable_tags to settings.py "
            '(e.g. readarr_user_selectable_tags=["tag-1", "tag-2"]) if you want to limit the tags '
            "a user can select. Defaulting to empty list ([]), which will present the user with all tags."
        )
        
    # Check allow_user_to_select_tags setting
    if not hasattr(settings, "readarr_allow_user_to_select_tags"):
        settings.readarr_allow_user_to_select_tags = True
        logger.warning(
            "No readarr_allow_user_to_select_tags setting found. Please add readarr_allow_user_to_select_tags to settings.py "
            "(e.g. readarr_allow_user_to_select_tags=False) "
            "if you do not want users to be able to select tags "
            "when adding a book. Defaulting to True."
        )