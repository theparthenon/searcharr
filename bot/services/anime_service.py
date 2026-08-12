"""
Searcharr
Sonarr & Radarr Telegram Bot
Sonarr Service Configuration
By Todd Roberts
https://github.com/toddrob99/searcharr
"""
from bot.utils.log import set_up_logger
import settings

logger = set_up_logger("anime_service")


def configure_anime(client):
    """Configure the Anime client.

    Args:
        client: The Anime client

    Returns:
        object: The configured anime client
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
    """Configure quality profiles for Anime.

    Args:
        client: The Anime client

    Returns:
        object: The Anime client with configured quality profiles
    """
    quality_profiles = []
    setting_name = "anime_quality_profile_id"

    profile_setting = getattr(settings, setting_name, [])
    if not isinstance(profile_setting, list):
        setattr(settings, setting_name, [profile_setting])
        profile_setting = [profile_setting]

    for i in profile_setting:
        logger.debug(f"Looking up/validating Anime quality profile id for [{i}]...")
        foundProfile = client.lookup_quality_profile(i)

        if not foundProfile:
            logger.error(f"Anime quality profile id/name [{i}] is invalid!")
        else:
            logger.debug(f"Found Anime quality profile for [{i}]: [{foundProfile}]")
            quality_profiles.append(foundProfile)

    if not quality_profiles:
        logger.warning(
            f"No valid Anime quality profile(s) provided! "
            f"Using all of the quality profiles found in Anime: {client._quality_profiles}"
        )
    else:
        logger.debug(
            f"Using the following Anime quality profile(s): "
            f"{[(x['id'], x['name']) for x in quality_profiles]}"
        )
        client._quality_profiles = quality_profiles

    return client


def _configure_root_folders(client):
    """Configure root folders for Anime.

    Args:
        client: The Anime client

    Returns:
        object: The anime client with configured root folders
    """
    setting_name = "anime_series_paths"

    root_folders = []

    if not hasattr(settings, setting_name):
        setattr(settings, setting_name, [])
        logger.warning(
            f"No {setting_name} setting detected. Please set one in settings.py "
            f"({setting_name}=[\"/path/1\", \"/path/2\"]). Proceeding with all root folders configured in Anime."
        )

    paths_setting = getattr(settings, setting_name)
    if not isinstance(paths_setting, list):
        setattr(settings, setting_name, [paths_setting])
        paths_setting = [paths_setting]

    for i in paths_setting:
        logger.debug(f"Looking up/validating Anime root folder for [{i}]...")
        foundPath = client.lookup_root_folder(i)

        if not foundPath:
            logger.error(f"Anime root folder path/id [{i}] is invalid!")
        else:
            logger.debug(f"Found Anime root folder for [{i}]: [{foundPath}]")
            root_folders.append(foundPath)

    if not root_folders:
        logger.warning(
            f"No valid Anime root folder(s) provided! "
            f"Using all of the root folders found in Anime: {client._root_folders}"
        )
    else:
        logger.debug(
            f"Using the following Anime root folder(s): "
            f"{[(x['id'], x['path']) for x in root_folders]}"
        )
        client._root_folders = root_folders

    return client


def _configure_tags(client):
    """Configure tags for Anime.

    Args:
        client: The Anime client
    """
    # Process forced tags
    forced_tags = getattr(settings, "anime_forced_tags", [])

    for t in forced_tags:
        if t_id := client.get_tag_id(t):
            logger.debug(f"Tag id [{t_id}] for forced Anime tag [{t}]")

    # Process user-selectable tags
    user_tags = getattr(settings, "anime_user_selectable_tags", [])

    for t in user_tags:
        if t_id := client.get_tag_id(t):
            logger.debug(f"Tag id [{t_id}] for user-selectable Anime tag [{t}]")


def _check_service_settings():
    """Check and set defaults for Anime settings."""
    # Check tag_with_username setting
    if not hasattr(settings, "anime_tag_with_username"):
        settings.anime_tag_with_username = True
        logger.warning(
            "No anime_tag_with_username setting found. Please add anime_tag_with_username to settings.py "
            "(anime_tag_with_username=True or anime_tag_with_username=False). Defaulting to True."
        )

    # Check command aliases setting
    if not hasattr(settings, "anime_series_command_aliases"):
        settings.anime_series_command_aliases = ["series"]
        logger.warning(
            "No anime_series_command_aliases setting found. Please add anime_series_command_aliases to settings.py "
            '(e.g. anime_series_command_aliases=["series", "s"]). '
            'Defaulting to ["series"].'
        )

    # Check forced tags setting
    if not hasattr(settings, "anime_forced_tags"):
        settings.anime_forced_tags = []
        logger.warning(
            "No anime_forced_tags setting found. Please add anime_forced_tags to settings.py "
            '(e.g. anime_forced_tags=["tag-1", "tag-2"]) if you want specific tags '
            "added to each series. Defaulting to empty list ([])."
        )

    # Check user_selectable_tags setting
    if not hasattr(settings, "anime_user_selectable_tags"):
        settings.anime_user_selectable_tags = []
        logger.warning(
            "No anime_user_selectable_tags setting found. Please add anime_user_selectable_tags to settings.py "
            '(e.g. anime_user_selectable_tags=["tag-1", "tag-2"]) if you want to limit the tags '
            "a user can select. Defaulting to empty list ([]), which will present the user with all tags."
        )

    # Check allow_user_to_select_tags setting
    if not hasattr(settings, "anime_allow_user_to_select_tags"):
        settings.anime_allow_user_to_select_tags = False
        logger.warning(
            "No anime_allow_user_to_select_tags setting found. Please add anime_allow_user_to_select_tags to settings.py "
            "(e.g. anime_allow_user_to_select_tags=True) "
            "if you want users to be able to select tags "
            "when adding a series. Defaulting to False."
        )

    # Check season_monitor_prompt setting
    if not hasattr(settings, "anime_season_monitor_prompt"):
        settings.anime_season_monitor_prompt = False
        logger.warning(
            "No anime_season_monitor_prompt setting found. Please add anime_season_monitor_prompt to settings.py "
            "(e.g. anime_season_monitor_prompt=True if you want users to choose whether to monitor "
            "all/first/latest season(s). Defaulting to False."
        )