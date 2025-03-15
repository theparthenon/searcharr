"""
Searcharr
Sonarr, Radarr & Readarr Telegram Bot
By Todd Roberts
https://github.com/toddrob99/searcharr
"""
import argparse
import json
import os
import yaml
import sqlite3
from threading import Lock
from urllib.parse import parse_qsl
import uuid
from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.error import BadRequest
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler

from log import set_up_logger
import radarr
import sonarr
import readarr
import settings

__version__ = "3.2.2"

DBPATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), "data")
DBFILE = "searcharr.db"
DBLOCK = Lock()


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


class Searcharr(object):
    def __init__(self, token):
        self.DEV_MODE = True if args.dev_mode else False
        self.token = token
        logger.info(f"Searcharr v{__version__} - Logging started!")
        
        # Load language
        self._lang = self._load_language()
        if self._lang.get("language_ietf") != "en-us":
            self._lang_default = self._load_language("en-us")
            
        # Initialize service clients
        self.sonarr = self._init_service("sonarr")
        self.radarr = self._init_service("radarr")
        self.readarr = self._init_service("readarr")
        
        # Initialize conversation tracking
        self.conversations = {}
        
        # Check and validate common settings
        self._check_common_settings()
        
    def _init_service(self, service_name):
        """Initialize a service client with error handling
        
        Args:
            service_name (str): Name of the service to initialize (sonarr, radarr, readarr)
            
        Returns:
            object: Service client or None if not enabled/failed
        """
        # Check if service is enabled
        enabled_setting = f"{service_name}_enabled"
        if not hasattr(settings, enabled_setting):
            # Setting doesn't exist, create it and set to False
            setattr(settings, enabled_setting, False)
            logger.warning(
                f"No {enabled_setting} setting found. If you want Searcharr to support {service_name.title()}, "
                f"please refer to the sample settings on github and add settings for {service_name.title()} to settings.py."
            )
            return None
        elif not getattr(settings, enabled_setting):
            # Setting exists but is False
            logger.info(f"{service_name.title()} is disabled in settings")
            return None
        
        # Get the right module for the service
        service_module = globals().get(service_name)
        if not service_module:
            logger.error(f"Could not import {service_name} module")
            return None
        
        # Get the service class (capitalized name)
        service_class = getattr(service_module, service_name.title())
        if not service_class:
            logger.error(f"Could not find {service_name.title()} class in {service_name} module")
            return None
        
        try:
            # Initialize the service client
            service_url = getattr(settings, f"{service_name}_url")
            service_api_key = getattr(settings, f"{service_name}_api_key")
            
            client = service_class(service_url, service_api_key, args.verbose)
            logger.info(f"{service_name.title()} client initialized successfully")
            
            # Configure the service
            client = self._configure_service(client, service_name)
            
            return client
            
        except Exception as e:
            logger.error(f"Failed to initialize {service_name.title()}: {e}")
            setattr(settings, f"{service_name}_enabled", False)
            return None
            
    def _configure_service(self, client, service_name):
        """Configure a service client with profiles, folders, and tags
        
        Args:
            client: Service client to configure
            service_name (str): Name of the service (sonarr, radarr, readarr)
            
        Returns:
            object: Configured service client
        """
        # Configure quality profiles
        client = self._configure_quality_profiles(client, service_name)
        
        # Configure metadata profiles for Readarr
        if service_name == "readarr":
            client = self._configure_metadata_profiles(client, service_name)
        
        # Configure root folders
        client = self._configure_root_folders(client, service_name)
        
        # Configure tags
        self._configure_tags(client, service_name)
        
        # Check other service-specific settings
        self._check_service_settings(service_name)
        
        return client
        
    def _configure_quality_profiles(self, client, service_name):
        """Configure quality profiles for a service
        
        Args:
            client: Service client to configure
            service_name (str): Name of the service (sonarr, radarr, readarr)
            
        Returns:
            object: Service client with configured quality profiles
        """
        quality_profiles = []
        setting_name = f"{service_name}_quality_profile_id"
        
        profile_setting = getattr(settings, setting_name, [])
        if not isinstance(profile_setting, list):
            setattr(settings, setting_name, [profile_setting])
            profile_setting = [profile_setting]
            
        for i in profile_setting:
            logger.debug(f"Looking up/validating {service_name.title()} quality profile id for [{i}]...")
            foundProfile = client.lookup_quality_profile(i)
            
            if not foundProfile:
                logger.error(f"{service_name.title()} quality profile id/name [{i}] is invalid!")
            else:
                logger.debug(f"Found {service_name.title()} quality profile for [{i}]: [{foundProfile}]")
                quality_profiles.append(foundProfile)
                
        if not len(quality_profiles):
            logger.warning(
                f"No valid {service_name.title()} quality profile(s) provided! "
                f"Using all of the quality profiles I found in {service_name.title()}: {client._quality_profiles}"
            )
        else:
            logger.debug(
                f"Using the following {service_name.title()} quality profile(s): "
                f"{[(x['id'], x['name']) for x in quality_profiles]}"
            )
            client._quality_profiles = quality_profiles
            
        return client
        
    def _configure_metadata_profiles(self, client, service_name):
        """Configure metadata profiles for Readarr
        
        Args:
            client: Service client to configure
            service_name (str): Must be "readarr"
            
        Returns:
            object: Service client with configured metadata profiles
        """
        if service_name != "readarr":
            return client
            
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
                
        if not len(metadata_profiles):
            logger.warning(
                f"No valid Readarr metadata profile(s) provided! "
                f"Using all of the metadata profiles I found in Readarr: {client._metadata_profiles}"
            )
        else:
            logger.debug(
                f"Using the following Readarr metadata profile(s): "
                f"{[(x['id'], x['name']) for x in metadata_profiles]}"
            )
            client._metadata_profiles = metadata_profiles
            
        return client
        
    def _configure_root_folders(self, client, service_name):
        """Configure root folders for a service
        
        Args:
            client: Service client to configure
            service_name (str): Name of the service (sonarr, radarr, readarr)
            
        Returns:
            object: Service client with configured root folders
        """
        content_type = {
            "sonarr": "series",
            "radarr": "movie",
            "readarr": "book"
        }.get(service_name, "content")
        
        setting_name = f"{service_name}_{content_type}_paths"
        
        root_folders = []
        
        if not hasattr(settings, setting_name):
            setattr(settings, setting_name, [])
            logger.warning(
                f"No {setting_name} setting detected. Please set one in settings.py "
                f"({setting_name}=[\"/path/1\", \"/path/2\"]). Proceeding with all root folders configured in {service_name.title()}."
            )
            
        paths_setting = getattr(settings, setting_name)
        if not isinstance(paths_setting, list):
            setattr(settings, setting_name, [paths_setting])
            paths_setting = [paths_setting]
            
        for i in paths_setting:
            logger.debug(f"Looking up/validating {service_name.title()} root folder for [{i}]...")
            foundPath = client.lookup_root_folder(i)
            
            if not foundPath:
                logger.error(f"{service_name.title()} root folder path/id [{i}] is invalid!")
            else:
                logger.debug(f"Found {service_name.title()} root folder for [{i}]: [{foundPath}]")
                root_folders.append(foundPath)
                
        if not len(root_folders):
            logger.warning(
                f"No valid {service_name.title()} root folder(s) provided! "
                f"Using all of the root folders I found in {service_name.title()}: {client._root_folders}"
            )
        else:
            logger.debug(
                f"Using the following {service_name.title()} root folder(s): "
                f"{[(x['id'], x['path']) for x in root_folders]}"
            )
            client._root_folders = root_folders
            
        return client
        
    def _configure_tags(self, client, service_name):
        """Configure tags for a service
        
        Args:
            client: Service client to configure
            service_name (str): Name of the service (sonarr, radarr, readarr)
        """
        # Process forced tags
        forced_tags_setting = f"{service_name}_forced_tags"
        forced_tags = getattr(settings, forced_tags_setting, [])
        
        for t in forced_tags:
            if t_id := client.get_tag_id(t):
                logger.debug(f"Tag id [{t_id}] for forced {service_name.title()} tag [{t}]")
                
        # Process user-selectable tags
        user_tags_setting = f"{service_name}_user_selectable_tags"
        user_tags = getattr(settings, user_tags_setting, [])
        
        for t in user_tags:
            if t_id := client.get_tag_id(t):
                logger.debug(f"Tag id [{t_id}] for user-selectable {service_name.title()} tag [{t}]")
                
    def _check_service_settings(self, service_name):
        """Check and set defaults for service-specific settings
        
        Args:
            service_name (str): Name of the service (sonarr, radarr, readarr)
        """
        content_type = {
            "sonarr": "series",
            "radarr": "movie",
            "readarr": "book"
        }.get(service_name, "content")
        
        # Check tag_with_username setting
        tag_setting = f"{service_name}_tag_with_username"
        if not hasattr(settings, tag_setting):
            setattr(settings, tag_setting, True)
            logger.warning(
                f"No {tag_setting} setting found. Please add {tag_setting} to settings.py "
                f"({tag_setting}=True or {tag_setting}=False). Defaulting to True."
            )
            
        # Check command aliases setting
        cmd_setting = f"{service_name}_{content_type}_command_aliases"
        if not hasattr(settings, cmd_setting):
            setattr(settings, cmd_setting, [content_type])
            logger.warning(
                f"No {cmd_setting} setting found. Please add {cmd_setting} to settings.py "
                f"(e.g. {cmd_setting}=[\"{content_type}\", \"{content_type[0]}\"]). "
                f"Defaulting to [\"{content_type}\"]."
            )
            
        # Check forced tags setting
        forced_tags_setting = f"{service_name}_forced_tags"
        if not hasattr(settings, forced_tags_setting):
            setattr(settings, forced_tags_setting, [])
            logger.warning(
                f"No {forced_tags_setting} setting found. Please add {forced_tags_setting} to settings.py "
                f"(e.g. {forced_tags_setting}=[\"tag-1\", \"tag-2\"]) if you want specific tags "
                f"added to each {content_type}. Defaulting to empty list ([])."
            )
            
        # Check user_selectable_tags setting
        user_tags_setting = f"{service_name}_user_selectable_tags"
        if not hasattr(settings, user_tags_setting):
            setattr(settings, user_tags_setting, [])
            logger.warning(
                f"No {user_tags_setting} setting found. Please add {user_tags_setting} to settings.py "
                f"(e.g. {user_tags_setting}=[\"tag-1\", \"tag-2\"]) if you want to limit the tags "
                f"a user can select. Defaulting to empty list ([]), which will present the user with all tags."
            )
            
        # Check allow_user_to_select_tags setting
        allow_tags_setting = f"{service_name}_allow_user_to_select_tags"
        default_value = True if service_name in ["radarr", "readarr"] else False
        if not hasattr(settings, allow_tags_setting):
            setattr(settings, allow_tags_setting, default_value)
            logger.warning(
                f"No {allow_tags_setting} setting found. Please add {allow_tags_setting} to settings.py "
                f"(e.g. {allow_tags_setting}={'False' if default_value else 'True'}) "
                f"{'if you do not want' if default_value else 'if you want'} users to be able to select tags "
                f"when adding a {content_type}. Defaulting to {default_value}."
            )
            
        # Service-specific settings
        if service_name == "sonarr":
            if not hasattr(settings, "sonarr_season_monitor_prompt"):
                settings.sonarr_season_monitor_prompt = False
                logger.warning(
                    "No sonarr_season_monitor_prompt setting found. Please add sonarr_season_monitor_prompt to settings.py "
                    "(e.g. sonarr_season_monitor_prompt=True if you want users to choose whether to monitor "
                    "all/first/latest season(s). Defaulting to False."
                )
        elif service_name == "radarr":
            if not hasattr(settings, "radarr_min_availability"):
                settings.radarr_min_availability = "released"
                logger.warning(
                    'No radarr_min_availability setting found. Please add radarr_min_availability to settings.py '
                    '(options: "released", "announced", "inCinema"). Defaulting to "released".'
                )
                
    def _check_common_settings(self):
        """Check and set defaults for general settings"""
        # Check admin password
        if not hasattr(settings, "searcharr_admin_password"):
            settings.searcharr_admin_password = uuid.uuid4().hex
            logger.warning(
                f'No admin password detected. Please set one in settings.py (searcharr_admin_password="your admin password"). '
                f'Using {settings.searcharr_admin_password} as the admin password for this session.'
            )
            
        # Check user password
        if getattr(settings, "searcharr_password", "") == "":
            logger.warning(
                'Password is blank. This will allow anyone to add series/movies/books using your bot. '
                'If this is unexpected, set a password in settings.py (searcharr_password="your password").'
            )
            
        # Check command aliases
        for cmd_type in ["start", "help", "users"]:
            setting_name = f"searcharr_{cmd_type}_command_aliases"
            if not hasattr(settings, setting_name):
                setattr(settings, setting_name, [cmd_type])
                logger.warning(
                    f'No {setting_name} setting found. Please add {setting_name} to settings.py '
                    f'(e.g. {setting_name}=["{cmd_type}"]. Defaulting to ["{cmd_type}"].'
                )

    async def cmd_start(self, update, context):
        logger.debug(f"Received start cmd from [{update.message.from_user.username}]")
        password = self._strip_entities(update.message)
        if password and password == settings.searcharr_admin_password:
            self._add_user(
                id=update.message.from_user.id,
                username=str(update.message.from_user.username),
                admin=1,
            )
            await update.message.reply_text(
                self._xlate(
                    "admin_auth_success",
                    commands=" OR ".join(
                        [f"`/{c}`" for c in settings.searcharr_help_command_aliases]
                    ),
                )
            )
        elif self._authenticated(update.message.from_user.id):
            await update.message.reply_text(
                self._xlate(
                    "already_authenticated",
                    commands=" OR ".join(
                        [f"`/{c}`" for c in settings.searcharr_help_command_aliases]
                    ),
                )
            )
        elif password == settings.searcharr_password:
            self._add_user(
                id=update.message.from_user.id,
                username=str(update.message.from_user.username),
            )
            await update.message.reply_text(
                self._xlate(
                    "auth_successful",
                    commands=" OR ".join(
                        [f"`/{c}`" for c in settings.searcharr_help_command_aliases]
                    ),
                )
            )
        else:
            await update.message.reply_text(self._xlate("incorrect_pw"))

    async def cmd_book(self, update, context):
        logger.debug(f"Received book cmd from [{update.message.from_user.username}]")
        if not self._authenticated(update.message.from_user.id):
            await update.message.reply_text(
                self._xlate(
                    "auth_required",
                    commands=" OR ".join(
                        [
                            f"`/{c} <{self._xlate('password')}>`"
                            for c in settings.searcharr_start_command_aliases
                        ]
                    ),
                )
            )
            return
        if not settings.readarr_enabled:
            await update.message.reply_text(self._xlate("readarr_disabled"))
            return
        title = self._strip_entities(update.message)
        if not len(title):
            x_title = self._xlate("title").title()
            await update.message.reply_text(
                self._xlate(
                    "include_book_title_in_cmd",
                    commands=" OR ".join(
                        [
                            f"`/{c} {x_title}`"
                            for c in settings.readarr_book_command_aliases
                        ]
                    ),
                )
            )
            return
        results = self.readarr.lookup_book(title)
        cid = self._generate_cid()
        self._create_conversation(
            id=cid,
            username=str(update.message.from_user.username),
            kind="book",
            results=results,
        )

        if not len(results):
            await update.message.reply_text(self._xlate("no_matching_books"))
        else:
            r = results[0]
            reply_message, reply_markup = self._prepare_response(
                "book", r, cid, 0, len(results)
            )
            try:
                await context.bot.sendPhoto(
                    chat_id=update.message.chat.id,
                    photo=r["remotePoster"],
                    caption=reply_message,
                    reply_markup=reply_markup,
                )
            except BadRequest as e:
                if str(e) in self._bad_request_poster_error_messages:
                    logger.error(
                        f"Error sending photo [{r['remotePoster']}]: BadRequest: {e}. Attempting to send with default poster..."
                    )
                    await context.bot.sendPhoto(
                        chat_id=update.message.chat.id,
                        photo="https://artworks.thetvdb.com/banners/images/missing/movie.jpg",
                        caption=reply_message,
                        reply_markup=reply_markup,
                    )
                else:
                    raise

    async def cmd_movie(self, update, context):
        logger.debug(f"Received movie cmd from [{update.message.from_user.username}]")
        if not self._authenticated(update.message.from_user.id):
            await update.message.reply_text(
                self._xlate(
                    "auth_required",
                    commands=" OR ".join(
                        [
                            f"`/{c} <{self._xlate('password')}>`"
                            for c in settings.searcharr_start_command_aliases
                        ]
                    ),
                )
            )
            return
        if not settings.radarr_enabled:
            await update.message.reply_text(self._xlate("radarr_disabled"))
            return
        title = self._strip_entities(update.message)
        if not len(title):
            x_title = self._xlate("title").title()
            await update.message.reply_text(
                self._xlate(
                    "include_movie_title_in_cmd",
                    commands=" OR ".join(
                        [
                            f"`/{c} {x_title}`"
                            for c in settings.radarr_movie_command_aliases
                        ]
                    ),
                )
            )
            return
        results = self.radarr.lookup_movie(title)
        cid = self._generate_cid()
        self._create_conversation(
            id=cid,
            username=str(update.message.from_user.username),
            kind="movie",
            results=results,
        )

        if not len(results):
            await update.message.reply_text(self._xlate("no_matching_movies"))
        else:
            r = results[0]
            reply_message, reply_markup = self._prepare_response(
                "movie", r, cid, 0, len(results)
            )
            try:
                await context.bot.sendPhoto(
                    chat_id=update.message.chat.id,
                    photo=r["remotePoster"],
                    caption=reply_message,
                    reply_markup=reply_markup,
                )
            except BadRequest as e:
                if str(e) in self._bad_request_poster_error_messages:
                    logger.error(
                        f"Error sending photo [{r['remotePoster']}]: BadRequest: {e}. Attempting to send with default poster..."
                    )
                    await context.bot.sendPhoto(
                        chat_id=update.message.chat.id,
                        photo="https://artworks.thetvdb.com/banners/images/missing/movie.jpg",
                        caption=reply_message,
                        reply_markup=reply_markup,
                    )
                else:
                    raise

    async def cmd_series(self, update, context):
        logger.debug(f"Received series cmd from [{update.message.from_user.username}]")
        if not self._authenticated(update.message.from_user.id):
            await update.message.reply_text(
                self._xlate(
                    "auth_required",
                    commands=" OR ".join(
                        [
                            f"`/{c} <{self._xlate('password')}>`"
                            for c in settings.searcharr_start_command_aliases
                        ]
                    ),
                )
            )
            return
        if not settings.sonarr_enabled:
            await update.message.reply_text(self._xlate("sonarr_disabled"))
            return
        title = self._strip_entities(update.message)
        if not len(title):
            x_title = self._xlate("title").title()
            await update.message.reply_text(
                self._xlate(
                    "include_series_title_in_cmd",
                    commands=" OR ".join(
                        [
                            f"`/{c} {x_title}`"
                            for c in settings.sonarr_series_command_aliases
                        ]
                    ),
                )
            )
            return
        results = self.sonarr.lookup_series(title)
        cid = self._generate_cid()
        self._create_conversation(
            id=cid,
            username=str(update.message.from_user.username),
            kind="series",
            results=results,
        )

        if not len(results):
            await update.message.reply_text(self._xlate("no_matching_series"))
        else:
            r = results[0]
            reply_message, reply_markup = self._prepare_response(
                "series", r, cid, 0, len(results)
            )
            try:
                await context.bot.sendPhoto(
                    chat_id=update.message.chat.id,
                    photo=r["remotePoster"],
                    caption=reply_message,
                    reply_markup=reply_markup,
                )
            except BadRequest as e:
                if str(e) in self._bad_request_poster_error_messages:
                    logger.error(
                        f"Error sending photo [{r['remotePoster']}]: BadRequest: {e}. Attempting to send with default poster..."
                    )
                    await context.bot.sendPhoto(
                        chat_id=update.message.chat.id,
                        photo="https://artworks.thetvdb.com/banners/images/missing/movie.jpg",
                        caption=reply_message,
                        reply_markup=reply_markup,
                    )
                else:
                    raise

    async def cmd_users(self, update, context):
        logger.debug(f"Received users cmd from [{update.message.from_user.username}]")
        auth_level = self._authenticated(update.message.from_user.id)
        if not auth_level:
            await update.message.reply_text(
                self._xlate(
                    "auth_required",
                    commands=" OR ".join(
                        [
                            f"`/{c} <{self._xlate('password')}>`"
                            for c in settings.searcharr_start_command_aliases
                        ]
                    ),
                )
            )
            return
        elif auth_level != 2:
            await update.message.reply_text(
                self._xlate(
                    "admin_auth_required",
                    commands=" OR ".join(
                        [
                            f"`/{c} <{self._xlate('admin_password')}>`"
                            for c in settings.searcharr_start_command_aliases
                        ]
                    ),
                )
            )
            return

        results = self._get_users()
        cid = self._generate_cid()
        self._create_conversation(
            id=cid,
            username=str(update.message.from_user.username),
            kind="users",
            results=results,
        )
        if not len(results):
            await update.message.reply_text(self._xlate("no_users_found"))
        else:
            reply_message, reply_markup = self._prepare_response_users(
                cid,
                results,
                0,
                5,
                len(results),
            )
            await context.bot.sendMessage(
                chat_id=update.message.chat.id,
                text=reply_message,
                reply_markup=reply_markup,
            )

    async def callback(self, update, context):
        query = update.callback_query
        logger.debug(
            f"Received callback from [{query.from_user.username}]: [{query.data}]"
        )
        auth_level = self._authenticated(query.from_user.id)
        if not auth_level:
            await query.message.reply_text(
                self._xlate(
                    "auth_required",
                    commands=" OR ".join(
                        [
                            f"`/{c} <{self._xlate('password')}>`"
                            for c in settings.searcharr_start_command_aliases
                        ]
                    ),
                )
            )
            await query.message.delete()
            await query.answer()
            return

        if not query.data or not len(query.data):
            await query.answer()
            return

        convo = self._get_conversation(query.data.split("^^^")[0])
        if not convo:
            await query.message.reply_text(self._xlate("convo_not_found"))
            await query.message.delete()
            await query.answer()
            return

        cid, i, op = query.data.split("^^^")
        if "^^" in op:
            op, op_flags = op.split("^^")
            op_flags = dict(parse_qsl(op_flags))
            for k, v in op_flags.items():
                logger.debug(
                    f"Adding/Updating additional data for cid=[{cid}], key=[{k}], value=[{v}]..."
                )
                self._update_add_data(cid, k, v)
        i = int(i)
        if op == "noop":
            pass
        elif op == "cancel":
            self._delete_conversation(cid)
            await query.message.reply_text(self._xlate("search_canceled"))
            await query.message.delete()
        elif op == "done":
            self._delete_conversation(cid)
            await query.message.delete()
        elif op == "prev":
            if convo["type"] in ["series", "movie", "book"]:
                if i <= 0:
                    await query.answer()
                    return
                r = convo["results"][i - 1]
                reply_message, reply_markup = self._prepare_response(
                    convo["type"], r, cid, i - 1, len(convo["results"])
                )
                try:
                    await query.message.edit_media(
                        media=InputMediaPhoto(r["remotePoster"]),
                        reply_markup=reply_markup,
                    )
                except BadRequest as e:
                    if str(e) in self._bad_request_poster_error_messages:
                        logger.error(
                            f"Error sending photo [{r['remotePoster']}]: BadRequest: {e}. Attempting to send with default poster..."
                        )
                        await query.message.edit_media(
                            media=InputMediaPhoto(
                                "https://artworks.thetvdb.com/banners/images/missing/movie.jpg"
                            ),
                            reply_markup=reply_markup,
                        )
                    else:
                        raise
                await query.bot.edit_message_caption(
                    chat_id=query.message.chat_id,
                    message_id=query.message.message_id,
                    caption=reply_message,
                    reply_markup=reply_markup,
                )
            elif convo["type"] == "users":
                if i <= 0:
                    i = 0
                reply_message, reply_markup = self._prepare_response_users(
                    cid,
                    convo["results"],
                    i,
                    5,
                    len(convo["results"]),
                )
                await context.bot.edit_message_text(
                    chat_id=query.message.chat.id,
                    message_id=query.message.message_id,
                    text=reply_message,
                    reply_markup=reply_markup,
                )
        elif op == "next":
            if convo["type"] in ["series", "movie", "book"]:
                if i >= len(convo["results"]):
                    await query.answer()
                    return
                r = convo["results"][i + 1]
                logger.debug(f"{r=}")
                reply_message, reply_markup = self._prepare_response(
                    convo["type"], r, cid, i + 1, len(convo["results"])
                )
                try:
                    await query.message.edit_media(
                        media=InputMediaPhoto(r["remotePoster"]),
                        reply_markup=reply_markup,
                    )
                except BadRequest as e:
                    if str(e) in self._bad_request_poster_error_messages:
                        logger.error(
                            f"Error sending photo [{r['remotePoster']}]: BadRequest: {e}. Attempting to send with default poster..."
                        )
                        await query.message.edit_media(
                            media=InputMediaPhoto(
                                "https://artworks.thetvdb.com/banners/images/missing/movie.jpg"
                            ),
                            reply_markup=reply_markup,
                        )
                    else:
                        raise
                await query.bot.edit_message_caption(
                    chat_id=query.message.chat_id,
                    message_id=query.message.message_id,
                    caption=reply_message,
                    reply_markup=reply_markup,
                )
            elif convo["type"] == "users":
                if i > len(convo["results"]):
                    await query.answer()
                    return
                reply_message, reply_markup = self._prepare_response_users(
                    cid,
                    convo["results"],
                    i,
                    5,
                    len(convo["results"]),
                )
                await context.bot.edit_message_text(
                    chat_id=query.message.chat.id,
                    message_id=query.message.message_id,
                    text=reply_message,
                    reply_markup=reply_markup,
                )
        elif op == "add":
            r = convo["results"][i]
            additional_data = self._get_add_data(cid)
            logger.debug(f"{additional_data=}")
            paths = (
                self.sonarr._root_folders
                if convo["type"] == "series"
                else self.radarr._root_folders
                if convo["type"] == "movie"
                else self.readarr._root_folders
                if convo["type"] == "book"
                else []
            )
            if not additional_data.get("p"):
                if len(paths) > 1:
                    reply_message, reply_markup = self._prepare_response(
                        convo["type"],
                        r,
                        cid,
                        i,
                        len(convo["results"]),
                        add=True,
                        paths=paths,
                    )
                    try:
                        await query.message.edit_media(
                            media=InputMediaPhoto(r["remotePoster"]),
                            reply_markup=reply_markup,
                        )
                    except BadRequest as e:
                        if str(e) in self._bad_request_poster_error_messages:
                            logger.error(
                                f"Error sending photo [{r['remotePoster']}]: BadRequest: {e}. Attempting to send with default poster..."
                            )
                            await query.message.edit_media(
                                media=InputMediaPhoto(
                                    "https://artworks.thetvdb.com/banners/images/missing/movie.jpg"
                                ),
                                reply_markup=reply_markup,
                            )
                        else:
                            raise
                    await query.bot.edit_message_caption(
                        chat_id=query.message.chat_id,
                        message_id=query.message.message_id,
                        caption=reply_message,
                        reply_markup=reply_markup,
                    )
                    await query.answer()
                    return
                elif len(paths) == 1:
                    logger.debug(
                        f"Only one root folder enabled. Adding/Updating additional data for cid=[{cid}], key=[p], value=[{paths[0]['id']}]..."
                    )
                    self._update_add_data(cid, "p", paths[0]["path"])
                else:
                    self._delete_conversation(cid)
                    await query.message.reply_text(
                        self._xlate(
                            "no_root_folders",
                            kind=self._xlate(convo["type"]),
                            app="Sonarr"
                            if convo["type"] == "series"
                            else "Radarr"
                            if convo["type"] == "movie"
                            else "Readarr"
                            if convo["type"] == "book"
                            else "???",
                        )
                    )
                    await query.message.delete()
                    await query.answer()
                    return
            else:
                try:
                    int(additional_data.get("p"))
                except ValueError:
                    # Value is already the full path
                    pass
                else:
                    # Translate id to actual path
                    path = next(
                        (
                            p["path"]
                            for p in paths
                            if p["id"] == int(additional_data["p"])
                        ),
                        None,
                    )
                    logger.debug(
                        f"Path id [{additional_data['p']}] lookup result: [{path}]"
                    )
                    if path:
                        self._update_add_data(cid, "p", path)

            if not additional_data.get("q"):
                quality_profiles = (
                    self.sonarr._quality_profiles
                    if convo["type"] == "series"
                    else self.radarr._quality_profiles
                    if convo["type"] == "movie"
                    else self.readarr._quality_profiles
                )
                if len(quality_profiles) > 1:
                    # prepare response to prompt user to select quality profile, and return
                    reply_message, reply_markup = self._prepare_response(
                        convo["type"],
                        r,
                        cid,
                        i,
                        len(convo["results"]),
                        add=True,
                        quality_profiles=quality_profiles,
                    )
                    try:
                        await query.message.edit_media(
                            media=InputMediaPhoto(r["remotePoster"]),
                            reply_markup=reply_markup,
                        )
                    except BadRequest as e:
                        if str(e) in self._bad_request_poster_error_messages:
                            logger.error(
                                f"Error sending photo [{r['remotePoster']}]: BadRequest: {e}. Attempting to send with default poster..."
                            )
                            await query.message.edit_media(
                                media=InputMediaPhoto(
                                    "https://artworks.thetvdb.com/banners/images/missing/movie.jpg"
                                ),
                                reply_markup=reply_markup,
                            )
                        else:
                            raise
                    await query.bot.edit_message_caption(
                        chat_id=query.message.chat_id,
                        message_id=query.message.message_id,
                        caption=reply_message,
                        reply_markup=reply_markup,
                    )
                    await query.answer()
                    return
                elif len(quality_profiles) == 1:
                    logger.debug(
                        f"Only one quality profile enabled. Adding/Updating additional data for cid=[{cid}], key=[q], value=[{quality_profiles[0]['id']}]..."
                    )
                    self._update_add_data(cid, "q", quality_profiles[0]["id"])
                else:
                    self._delete_conversation(cid)
                    await query.message.reply_text(
                        self._xlate(
                            "no_quality_profiles",
                            kind=self._xlate(convo["type"]),
                            app="Sonarr"
                            if convo["type"] == "series"
                            else "Radarr"
                            if convo["type"] == "movie"
                            else "Readarr",
                        )
                    )
                    await query.message.delete()
                    await query.answer()
                    return

            if convo["type"] == "book" and not additional_data.get("m"):
                metadata_profiles = self.readarr._metadata_profiles
                if len(metadata_profiles) > 1:
                    # prepare response to prompt user to select quality profile, and return
                    reply_message, reply_markup = self._prepare_response(
                        convo["type"],
                        r,
                        cid,
                        i,
                        len(convo["results"]),
                        add=True,
                        metadata_profiles=metadata_profiles,
                    )
                    try:
                        await query.message.edit_media(
                            media=InputMediaPhoto(r["remotePoster"]),
                            reply_markup=reply_markup,
                        )
                    except BadRequest as e:
                        if str(e) in self._bad_request_poster_error_messages:
                            logger.error(
                                f"Error sending photo [{r['remotePoster']}]: BadRequest: {e}. Attempting to send with default poster..."
                            )
                            await query.message.edit_media(
                                media=InputMediaPhoto(
                                    "https://artworks.thetvdb.com/banners/images/missing/movie.jpg"
                                ),
                                reply_markup=reply_markup,
                            )
                        else:
                            raise
                    await query.bot.edit_message_caption(
                        chat_id=query.message.chat_id,
                        message_id=query.message.message_id,
                        caption=reply_message,
                        reply_markup=reply_markup,
                    )
                    await query.answer()
                    return
                elif len(metadata_profiles) == 1:
                    logger.debug(
                        f"Only one metadata profile enabled. Adding/Updating additional data for cid=[{cid}], key=[m], value=[{metadata_profiles[0]['id']}]..."
                    )
                    self._update_add_data(cid, "m", metadata_profiles[0]["id"])
                else:
                    self._delete_conversation(cid)
                    await query.message.reply_text(
                        self._xlate(
                            "no_metadata_profiles",
                            kind=self._xlate(convo["type"]),
                            app="Sonarr"
                            if convo["type"] == "series"
                            else "Radarr"
                            if convo["type"] == "movie"
                            else "Readarr",
                        )
                    )
                    await query.message.delete()
                    await query.answer()
                    return

            if (
                convo["type"] == "series"
                and settings.sonarr_season_monitor_prompt
                and additional_data.get("m", False) is False
            ):
                # m = monitor season(s)
                monitor_options = [
                    self._xlate("all_seasons"),
                    self._xlate("first_season"),
                    self._xlate("latest_season"),
                ]
                # prepare response to prompt user to select quality profile, and return
                reply_message, reply_markup = self._prepare_response(
                    convo["type"],
                    r,
                    cid,
                    i,
                    len(convo["results"]),
                    add=True,
                    monitor_options=monitor_options,
                )
                try:
                    await query.message.edit_media(
                        media=InputMediaPhoto(r["remotePoster"]),
                        reply_markup=reply_markup,
                    )
                except BadRequest as e:
                    if str(e) in self._bad_request_poster_error_messages:
                        logger.error(
                            f"Error sending photo [{r['remotePoster']}]: BadRequest: {e}. Attempting to send with default poster..."
                        )
                        await query.message.edit_media(
                            media=InputMediaPhoto(
                                "https://artworks.thetvdb.com/banners/images/missing/movie.jpg"
                            ),
                            reply_markup=reply_markup,
                        )
                    else:
                        raise
                await query.bot.edit_message_caption(
                    chat_id=query.message.chat_id,
                    message_id=query.message.message_id,
                    caption=reply_message,
                    reply_markup=reply_markup,
                )
                await query.answer()
                return

            if convo["type"] == "series":
                all_tags = self.sonarr.get_filtered_tags(
                    settings.sonarr_user_selectable_tags,
                    settings.sonarr_forced_tags,
                )
                allow_user_to_select_tags = settings.sonarr_allow_user_to_select_tags
                forced_tags = settings.sonarr_forced_tags
            elif convo["type"] == "movie":
                all_tags = self.radarr.get_filtered_tags(
                    settings.radarr_user_selectable_tags,
                    settings.radarr_forced_tags,
                )
                allow_user_to_select_tags = settings.radarr_allow_user_to_select_tags
                forced_tags = settings.radarr_forced_tags
            elif convo["type"] == "book":
                all_tags = self.readarr.get_filtered_tags(
                    settings.readarr_user_selectable_tags,
                    settings.readarr_forced_tags,
                )
                allow_user_to_select_tags = settings.readarr_allow_user_to_select_tags
                forced_tags = settings.readarr_forced_tags
            if allow_user_to_select_tags and not additional_data.get("td"):
                if not len(all_tags):
                    logger.warning(
                        f"User tagging is enabled, but no tags found. Make sure there are tags{' in Sonarr' if convo['type'] == 'series' else ' in Radarr' if convo['type'] == 'movie' else ' in Readarr' if convo['type'] == 'book' else ''} matching your Searcharr configuration."
                    )
                elif not additional_data.get("tt"):
                    reply_message, reply_markup = self._prepare_response(
                        convo["type"],
                        r,
                        cid,
                        i,
                        len(convo["results"]),
                        add=True,
                        tags=all_tags,
                    )
                    try:
                        await query.message.edit_media(
                            media=InputMediaPhoto(r["remotePoster"]),
                            reply_markup=reply_markup,
                        )
                    except BadRequest as e:
                        if str(e) in self._bad_request_poster_error_messages:
                            logger.error(
                                f"Error sending photo [{r['remotePoster']}]: BadRequest: {e}. Attempting to send with default poster..."
                            )
                            await query.message.edit_media(
                                media=InputMediaPhoto(
                                    "https://artworks.thetvdb.com/banners/images/missing/movie.jpg"
                                ),
                                reply_markup=reply_markup,
                            )
                        else:
                            raise
                    await query.bot.edit_message_caption(
                        chat_id=query.message.chat_id,
                        message_id=query.message.message_id,
                        caption=reply_message,
                        reply_markup=reply_markup,
                    )
                    await query.answer()
                    return
                else:
                    tag_ids = (
                        additional_data.get("t", "").split(",")
                        if len(additional_data.get("t", ""))
                        else []
                    )
                    tag_ids.append(additional_data["tt"])
                    logger.debug(f"Adding tag [{additional_data['tt']}]")
                    self._update_add_data(cid, "t", ",".join(tag_ids))
                    return

            tags = (
                additional_data.get("t").split(",")
                if len(additional_data.get("t", ""))
                else []
            )
            logger.debug(f"{tags=}")
            if convo["type"] == "series":
                get_tag_id = self.sonarr.get_tag_id
                tag_with_username = settings.sonarr_tag_with_username
            elif convo["type"] == "movie":
                get_tag_id = self.radarr.get_tag_id
                tag_with_username = settings.radarr_tag_with_username
            elif convo["type"] == "book":
                get_tag_id = self.readarr.get_tag_id
                tag_with_username = settings.readarr_tag_with_username
            if tag_with_username:
                tag = f"searcharr-{query.from_user.username if query.from_user.username else query.from_user.id}"
                if tag_id := get_tag_id(tag):
                    tags.append(str(tag_id))
                else:
                    self.logger.warning(
                        f"Tag lookup/creation failed for [{tag}]. This tag will not be added to the {convo['type']}."
                    )
            for tag in forced_tags:
                if tag_id := get_tag_id(tag):
                    tags.append(str(tag_id))
                else:
                    self.logger.warning(
                        f"Tag lookup/creation failed for forced tag [{tag}]. This tag will not be added to the {convo['type']}."
                    )
            self._update_add_data(cid, "t", ",".join(list(set(tags))))

            logger.debug("All data is accounted for, proceeding to add...")
            try:
                if convo["type"] == "series":
                    added = self.sonarr.add_series(
                        series_info=r,
                        monitored=settings.sonarr_add_monitored,
                        search=settings.sonarr_search_on_add,
                        additional_data=self._get_add_data(cid),
                    )
                elif convo["type"] == "movie":
                    added = self.radarr.add_movie(
                        movie_info=r,
                        monitored=settings.radarr_add_monitored,
                        search=settings.radarr_search_on_add,
                        min_avail=settings.radarr_min_availability,
                        additional_data=self._get_add_data(cid),
                    )
                elif convo["type"] == "book":
                    added = self.readarr.add_book(
                        book_info=r,
                        monitored=settings.readarr_add_monitored,
                        search=settings.readarr_search_on_add,
                        additional_data=self._get_add_data(cid),
                    )
                else:
                    added = False
            except Exception as e:
                logger.error(f"Error adding {convo['type']}: {e}")
                added = False
            logger.debug(f"Result of attempt to add {convo['type']}: {added}")
            if added:
                self._delete_conversation(cid)
                await query.message.reply_text(self._xlate("added", title=r["title"]))
                await query.message.delete()
            else:
                await query.message.reply_text(
                    self._xlate("unknown_error_adding", kind=convo["type"])
                )
        elif op == "remove_user":
            if auth_level != 2:
                await query.message.reply_text(
                    self._xlate(
                        "admin_auth_required",
                        commands=" OR ".join(
                            [
                                f"`/{c} <{self._xlate('admin_password')}>`"
                                for c in settings.searcharr_start_command_aliases
                            ]
                        ),
                    )
                )
                await query.message.delete()
                await query.answer()
                return
            try:
                self._remove_user(i)
                # Update the conversation with fresh user data
                convo.update({"results": self._get_users()})
                self._create_conversation(
                    id=cid,
                    username=str(query.from_user.username),
                    kind="users",
                    results=convo["results"],
                )
                reply_message, reply_markup = self._prepare_response_users(
                    cid,
                    convo["results"],
                    0,
                    5,
                    len(convo["results"]),
                )
                await context.bot.edit_message_text(
                    chat_id=query.message.chat.id,
                    message_id=query.message.message_id,
                    text=f"{self._xlate('removed_user', user=i)} {reply_message}",
                    reply_markup=reply_markup,
                )
            except Exception as e:
                logger.error(f"Error removing all access for user id [{i}]: {e}")
                await query.message.reply_text(
                    self._xlate("unknown_error_removing_user", user=i)
                )
        elif op == "make_admin":
            if auth_level != 2:
                await query.message.reply_text(
                    self._xlate(
                        "admin_auth_required",
                        commands=" OR ".join(
                            [
                                f"`/{c} <{self._xlate('admin_password')}>`"
                                for c in settings.searcharr_start_command_aliases
                            ]
                        ),
                    )
                )
                await query.message.delete()
                await query.answer()
                return
            try:
                self._update_admin_access(i, 1)
                # Update the conversation with fresh user data
                convo.update({"results": self._get_users()})
                self._create_conversation(
                    id=cid,
                    username=str(query.from_user.username),
                    kind="users",
                    results=convo["results"],
                )
                reply_message, reply_markup = self._prepare_response_users(
                    cid,
                    convo["results"],
                    0,
                    5,
                    len(convo["results"]),
                )
                await context.bot.edit_message_text(
                    chat_id=query.message.chat.id,
                    message_id=query.message.message_id,
                    text=f"{self._xlate('added_admin_access', user=i)} {reply_message}",
                    reply_markup=reply_markup,
                )
            except Exception as e:
                logger.error(f"Error adding admin access for user id [{i}]: {e}")
                await query.message.reply_text(
                    self._xlate("unknown_error_adding_admin", user=i)
                )
        elif op == "remove_admin":
            if auth_level != 2:
                await query.message.reply_text(
                    self._xlate(
                        "admin_auth_required",
                        commands=" OR ".join(
                            [
                                f"`/{c} <{self._xlate('admin_password')}>`"
                                for c in settings.searcharr_start_command_aliases
                            ]
                        ),
                    )
                )
                await query.message.delete()
                await query.answer()
                return
            try:
                self._update_admin_access(i, "")
                # Update the conversation with fresh user data
                convo.update({"results": self._get_users()})
                self._create_conversation(
                    id=cid,
                    username=str(query.from_user.username),
                    kind="users",
                    results=convo["results"],
                )
                reply_message, reply_markup = self._prepare_response_users(
                    cid,
                    convo["results"],
                    0,
                    5,
                    len(convo["results"]),
                )
                await context.bot.edit_message_text(
                    chat_id=query.message.chat.id,
                    message_id=query.message.message_id,
                    text=f"{self._xlate('removed_admin_access', user=i)} {reply_message}",
                    reply_markup=reply_markup,
                )
            except Exception as e:
                logger.error(f"Error removing admin access for user id [{i}]: {e}")
                await query.message.reply_text(
                    self._xlate("unknown_error_removing_admin", user=i)
                )

        await query.answer()
        
    def _prepare_response(
        self,
        kind,
        r,
        cid,
        i,
        total_results,
        add=False,
        paths=None,
        quality_profiles=None,
        metadata_profiles=None,
        monitor_options=None,
        tags=None,
    ):
        keyboard = []
        keyboardNavRow = []
        if i > 0:
            keyboardNavRow.append(
                InlineKeyboardButton(
                    self._xlate("prev_button"), callback_data=f"{cid}^^^{i}^^^prev"
                )
            )
        if kind == "series" and r["tvdbId"]:
            keyboardNavRow.append(
                InlineKeyboardButton(
                    "tvdb", url=f"https://thetvdb.com/series/{r['titleSlug']}"
                )
            )
        elif kind == "movie" and r["tmdbId"]:
            keyboardNavRow.append(
                InlineKeyboardButton(
                    "TMDB", url=f"https://www.themoviedb.org/movie/{r['tmdbId']}"
                )
            )
        elif kind == "book" and r["links"]:
            for link in r["links"]:
                keyboardNavRow.append(
                    InlineKeyboardButton(link["name"], url=link["url"])
                )
        if kind == "series" or kind == "movie":
            if r["imdbId"]:
                keyboardNavRow.append(
                    InlineKeyboardButton(
                        "IMDb", url=f"https://imdb.com/title/{r['imdbId']}"
                    )
                )
        if total_results > 1 and i < total_results - 1:
            keyboardNavRow.append(
                InlineKeyboardButton(
                    self._xlate("next_button"), callback_data=f"{cid}^^^{i}^^^next"
                )
            )
        keyboard.append(keyboardNavRow)

        if add:
            if tags:
                for tag in tags[:12]:
                    keyboard.append(
                        [
                            InlineKeyboardButton(
                                self._xlate("add_tag_button", tag=tag["label"]),
                                callback_data=f"{cid}^^^{i}^^^add^^tt={tag['id']}",
                            )
                        ],
                    )
                keyboard.append(
                    [
                        InlineKeyboardButton(
                            self._xlate("finished_tagging_button"),
                            callback_data=f"{cid}^^^{i}^^^add^^td=1",
                        )
                    ],
                )
            elif monitor_options:
                for k, o in enumerate(monitor_options):
                    keyboard.append(
                        [
                            InlineKeyboardButton(
                                self._xlate("monitor_button", option=o),
                                callback_data=f"{cid}^^^{i}^^^add^^m={k}",
                            )
                        ],
                    )
            elif quality_profiles:
                for q in quality_profiles:
                    keyboard.append(
                        [
                            InlineKeyboardButton(
                                self._xlate("add_quality_button", quality=q["name"]),
                                callback_data=f"{cid}^^^{i}^^^add^^q={q['id']}",
                            )
                        ],
                    )
            elif metadata_profiles:
                for m in metadata_profiles:
                    keyboard.append(
                        [
                            InlineKeyboardButton(
                                self._xlate("add_metadata_button", metadata=m["name"]),
                                callback_data=f"{cid}^^^{i}^^^add^^m={m['id']}",
                            )
                        ],
                    )
            elif paths:
                for p in paths:
                    keyboard.append(
                        [
                            InlineKeyboardButton(
                                self._xlate("add_path_button", path=p["path"]),
                                callback_data=f"{cid}^^^{i}^^^add^^p={p['id']}",
                            )
                        ],
                    )

        keyboardActRow = []
        if not add:
            if not r["id"]:
                keyboardActRow.append(
                    InlineKeyboardButton(
                        self._xlate("add_button", kind=self._xlate(kind).title()),
                        callback_data=f"{cid}^^^{i}^^^add",
                    ),
                )
            else:
                keyboardActRow.append(
                    InlineKeyboardButton(
                        self._xlate("already_added_button"),
                        callback_data=f"{cid}^^^{i}^^^noop",
                    ),
                )
        keyboardActRow.append(
            InlineKeyboardButton(
                self._xlate("cancel_search_button"),
                callback_data=f"{cid}^^^{i}^^^cancel",
            ),
        )
        if len(keyboardActRow):
            keyboard.append(keyboardActRow)
        if not add and kind == "series" and "Anime" in r["genres"]:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        self._xlate("add_series_anime_button"),
                        callback_data=f"{cid}^^^{i}^^^add^^st=a",
                    )
                ]
            )

        reply_markup = InlineKeyboardMarkup(keyboard)

        if kind == "series":
            reply_message = f"{r['title']}{' (' + str(r['year']) + ')' if r['year'] and str(r['year']) not in r['title'] else ''} - {r['seasonCount']} Season{'s' if r['seasonCount'] != 1 else ''}{' - ' + r['network'] if r['network'] else ''} - {r['status'].title()}\n\n{r['overview']}"[
                0:1024
            ]
        elif kind == "movie":
            reply_message = f"{r['title']}{' (' + str(r['year']) + ')' if r['year'] and str(r['year']) not in r['title'] else ''}{' - ' + str(r['runtime']) + ' min' if r['runtime'] else ''} - {r['status'].title()}\n\n{r['overview']}"[
                0:1024
            ]
        elif kind == "book":
            try:
                release = datetime.strptime(
                    r["releaseDate"], "%Y-%m-%dT%H:%M:%SZ"
                ).strftime("%b %d, %Y")
            except (ValueError, TypeError):
                release = "???"
            reply_message = f"{r['author']['authorName']} - {r['title']}{' - ' + r['disambiguation'] if r['disambiguation'] else ''}{' - ' + r['seriesTitle'] if r['seriesTitle'] else ''} ({release})\n\n{r['overview']}"[
                0:1024
            ]
        else:
            reply_message = self._xlate("unexpected_error")

        return (reply_message, reply_markup)

    def _prepare_response_users(self, cid, users, offset, num, total_results):
        keyboard = []
        for u in users[offset : offset + num]:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        self._xlate("remove_user_button"),
                        callback_data=f"{cid}^^^{u['id']}^^^remove_user",
                    ),
                    InlineKeyboardButton(
                        f"{u['username'] if u['username'] != 'None' else u['id']}",
                        callback_data=f"{cid}^^^{u['id']}^^^noop",
                    ),
                    InlineKeyboardButton(
                        self._xlate("remove_admin_button")
                        if u["admin"]
                        else self._xlate("make_admin_button"),
                        callback_data=f"{cid}^^^{u['id']}^^^{'remove_admin' if u['admin'] else 'make_admin'}",
                    ),
                ]
            )
        keyboardNavRow = []
        if offset > 0:
            keyboardNavRow.append(
                InlineKeyboardButton(
                    self._xlate("prev_button"),
                    callback_data=f"{cid}^^^{offset - num}^^^prev",
                ),
            )
        keyboardNavRow.append(
            InlineKeyboardButton(
                self._xlate("done"), callback_data=f"{cid}^^^{offset}^^^done"
            ),
        )
        if total_results > 1 and offset + num < total_results:
            keyboardNavRow.append(
                InlineKeyboardButton(
                    self._xlate("next_button"),
                    callback_data=f"{cid}^^^{offset + num}^^^next",
                ),
            )
        keyboard.append(keyboardNavRow)
        reply_markup = InlineKeyboardMarkup(keyboard)

        reply_message = self._xlate(
            "listing_users_pagination",
            page_info=f"{offset + 1}-{min(offset + num, total_results)} of {total_results}",
        )
        return (reply_message, reply_markup)

    async def handle_error(self, update, context):
        logger.error(f"Caught error: {context.error}")
        try:
            await update.callback_query.answer()
        except Exception:
            pass

    async def cmd_help(self, update, context):
        logger.debug(f"Received help cmd from [{update.message.from_user.username}]")
        auth_level = self._authenticated(update.message.from_user.id)
        if not auth_level:
            await update.message.reply_text(
                self._xlate(
                    "auth_required",
                    commands=" OR ".join(
                        [
                            f"`/{c} <{self._xlate('password')}>`"
                            for c in settings.searcharr_start_command_aliases
                        ]
                    ),
                )
            )
            return
        sonarr_help = self._xlate(
            "help_sonarr",
            series_commands=" OR ".join(
                [
                    f"`/{c} {self._xlate('title').title()}`"
                    for c in settings.sonarr_series_command_aliases
                ]
            ),
        )
        radarr_help = self._xlate(
            "help_radarr",
            movie_commands=" OR ".join(
                [
                    f"`/{c} {self._xlate('title').title()}`"
                    for c in settings.radarr_movie_command_aliases
                ]
            ),
        )
        if self.readarr:
            readarr_help = self._xlate(
                "help_readarr",
                book_commands=" OR ".join(
                    [
                        f"`/{c} {self._xlate('title').title()}`"
                        for c in settings.readarr_book_command_aliases
                    ]
                ),
            )

        if (
            settings.sonarr_enabled
            or settings.radarr_enabled
            or settings.readarr_enabled
        ):
            resp = ""
            if settings.sonarr_enabled:
                resp += f" {sonarr_help}"
            if settings.radarr_enabled:
                resp += f" {radarr_help}"
            if settings.readarr_enabled:
                resp += f" {readarr_help}"
        else:
            resp = self._xlate("no_features")

        if auth_level == 2:
            resp += " " + self._xlate(
                "admin_help",
                commands=" OR ".join(
                    [f"/{c}" for c in settings.searcharr_users_command_aliases]
                ),
            )

        await update.message.reply_text(resp)

    def _strip_entities(self, message):
        text = message.text
        entities = message.parse_entities()
        logger.debug(f"{entities=}")
        for v in entities.values():
            text = text.replace(v, "")
        text = text.replace("  ", "").strip()
        logger.debug(f"Stripped entities from message [{message.text}]: [{text}]")
        return text

    def run(self):
        self._init_db()
        
        # Build the application
        application = ApplicationBuilder().token(self.token).build()
        
        # Register command handlers
        for c in settings.searcharr_help_command_aliases:
            logger.debug(f"Registering [/{c}] as a help command")
            application.add_handler(CommandHandler(c, self.cmd_help))
        
        for c in settings.searcharr_start_command_aliases:
            logger.debug(f"Registering [/{c}] as a start command")
            application.add_handler(CommandHandler(c, self.cmd_start))
        
        if self.readarr:
            for c in settings.readarr_book_command_aliases:
                logger.debug(f"Registering [/{c}] as a book command")
                application.add_handler(CommandHandler(c, self.cmd_book))
        
        for c in settings.radarr_movie_command_aliases:
            logger.debug(f"Registering [/{c}] as a movie command")
            application.add_handler(CommandHandler(c, self.cmd_movie))
        
        for c in settings.sonarr_series_command_aliases:
            logger.debug(f"Registering [/{c}] as a series command")
            application.add_handler(CommandHandler(c, self.cmd_series))
        
        for c in settings.searcharr_users_command_aliases:
            logger.debug(f"Registering [/{c}] as a users command")
            application.add_handler(CommandHandler(c, self.cmd_users))
        
        # Register callback handler
        application.add_handler(CallbackQueryHandler(self.callback))
        
        # Add error handler if not in dev mode
        if not self.DEV_MODE:
            application.add_error_handler(self.handle_error)
        else:
            logger.info("Developer mode is enabled; skipping registration of error handler--exceptions will be raised.")
        
        # Start the bot
        logger.info("Starting Searcharr bot...")
        application.run_polling()

    def _prepare_response(
        self,
        kind,
        r,
        cid,
        i,
        total_results,
        add=False,
        paths=None,
        quality_profiles=None,
        metadata_profiles=None,
        monitor_options=None,
        tags=None,
    ):
        keyboard = []
        keyboardNavRow = []
        if i > 0:
            keyboardNavRow.append(
                InlineKeyboardButton(
                    self._xlate("prev_button"), callback_data=f"{cid}^^^{i}^^^prev"
                )
            )
        if kind == "series" and r["tvdbId"]:
            keyboardNavRow.append(
                InlineKeyboardButton(
                    "tvdb", url=f"https://thetvdb.com/series/{r['titleSlug']}"
                )
            )
        elif kind == "movie" and r["tmdbId"]:
            keyboardNavRow.append(
                InlineKeyboardButton(
                    "TMDB", url=f"https://www.themoviedb.org/movie/{r['tmdbId']}"
                )
            )
        elif kind == "book" and r["links"]:
            for link in r["links"]:
                keyboardNavRow.append(
                    InlineKeyboardButton(link["name"], url=link["url"])
                )
        if kind == "series" or kind == "movie":
            if r["imdbId"]:
                keyboardNavRow.append(
                    InlineKeyboardButton(
                        "IMDb", url=f"https://imdb.com/title/{r['imdbId']}"
                    )
                )
        if total_results > 1 and i < total_results - 1:
            keyboardNavRow.append(
                InlineKeyboardButton(
                    self._xlate("next_button"), callback_data=f"{cid}^^^{i}^^^next"
                )
            )
        keyboard.append(keyboardNavRow)

        if add:
            if tags:
                for tag in tags[:12]:
                    keyboard.append(
                        [
                            InlineKeyboardButton(
                                self._xlate("add_tag_button", tag=tag["label"]),
                                callback_data=f"{cid}^^^{i}^^^add^^tt={tag['id']}",
                            )
                        ],
                    )
                keyboard.append(
                    [
                        InlineKeyboardButton(
                            self._xlate("finished_tagging_button"),
                            callback_data=f"{cid}^^^{i}^^^add^^td=1",
                        )
                    ],
                )
            elif monitor_options:
                for k, o in enumerate(monitor_options):
                    keyboard.append(
                        [
                            InlineKeyboardButton(
                                self._xlate("monitor_button", option=o),
                                callback_data=f"{cid}^^^{i}^^^add^^m={k}",
                            )
                        ],
                    )
            elif quality_profiles:
                for q in quality_profiles:
                    keyboard.append(
                        [
                            InlineKeyboardButton(
                                self._xlate("add_quality_button", quality=q["name"]),
                                callback_data=f"{cid}^^^{i}^^^add^^q={q['id']}",
                            )
                        ],
                    )
            elif metadata_profiles:
                for m in metadata_profiles:
                    keyboard.append(
                        [
                            InlineKeyboardButton(
                                self._xlate("add_metadata_button", metadata=m["name"]),
                                callback_data=f"{cid}^^^{i}^^^add^^m={m['id']}",
                            )
                        ],
                    )
            elif paths:
                for p in paths:
                    keyboard.append(
                        [
                            InlineKeyboardButton(
                                self._xlate("add_path_button", path=p["path"]),
                                callback_data=f"{cid}^^^{i}^^^add^^p={p['id']}",
                            )
                        ],
                    )

        keyboardActRow = []
        if not add:
            if not r["id"]:
                keyboardActRow.append(
                    InlineKeyboardButton(
                        self._xlate("add_button", kind=self._xlate(kind).title()),
                        callback_data=f"{cid}^^^{i}^^^add",
                    ),
                )
            else:
                keyboardActRow.append(
                    InlineKeyboardButton(
                        self._xlate("already_added_button"),
                        callback_data=f"{cid}^^^{i}^^^noop",
                    ),
                )
        keyboardActRow.append(
            InlineKeyboardButton(
                self._xlate("cancel_search_button"),
                callback_data=f"{cid}^^^{i}^^^cancel",
            ),
        )
        if len(keyboardActRow):
            keyboard.append(keyboardActRow)
        if not add and kind == "series" and "Anime" in r["genres"]:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        self._xlate("add_series_anime_button"),
                        callback_data=f"{cid}^^^{i}^^^add^^st=a",
                    )
                ]
            )

        reply_markup = InlineKeyboardMarkup(keyboard)

        if kind == "series":
            reply_message = f"{r['title']}{' (' + str(r['year']) + ')' if r['year'] and str(r['year']) not in r['title'] else ''} - {r['seasonCount']} Season{'s' if r['seasonCount'] != 1 else ''}{' - ' + r['network'] if r['network'] else ''} - {r['status'].title()}\n\n{r['overview']}"[
                0:1024
            ]
        elif kind == "movie":
            reply_message = f"{r['title']}{' (' + str(r['year']) + ')' if r['year'] and str(r['year']) not in r['title'] else ''}{' - ' + str(r['runtime']) + ' min' if r['runtime'] else ''} - {r['status'].title()}\n\n{r['overview']}"[
                0:1024
            ]
        elif kind == "book":
            try:
                release = datetime.strptime(
                    r["releaseDate"], "%Y-%m-%dT%H:%M:%SZ"
                ).strftime("%b %d, %Y")
            except (ValueError, TypeError):
                release = "???"
            reply_message = f"{r['author']['authorName']} - {r['title']}{' - ' + r['disambiguation'] if r['disambiguation'] else ''}{' - ' + r['seriesTitle'] if r['seriesTitle'] else ''} ({release})\n\n{r['overview']}"[
                0:1024
            ]
        else:
            reply_message = self._xlate("unexpected_error")

        return (reply_message, reply_markup)

    def _prepare_response_users(self, cid, users, offset, num, total_results):
        keyboard = []
        for u in users[offset : offset + num]:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        self._xlate("remove_user_button"),
                        callback_data=f"{cid}^^^{u['id']}^^^remove_user",
                    ),
                    InlineKeyboardButton(
                        f"{u['username'] if u['username'] != 'None' else u['id']}",
                        callback_data=f"{cid}^^^{u['id']}^^^noop",
                    ),
                    InlineKeyboardButton(
                        self._xlate("remove_admin_button")
                        if u["admin"]
                        else self._xlate("make_admin_button"),
                        callback_data=f"{cid}^^^{u['id']}^^^{'remove_admin' if u['admin'] else 'make_admin'}",
                    ),
                ]
            )
        keyboardNavRow = []
        if offset > 0:
            keyboardNavRow.append(
                InlineKeyboardButton(
                    self._xlate("prev_button"),
                    callback_data=f"{cid}^^^{offset - num}^^^prev",
                ),
            )
        keyboardNavRow.append(
            InlineKeyboardButton(
                self._xlate("done"), callback_data=f"{cid}^^^{offset}^^^done"
            ),
        )
        if total_results > 1 and offset + num < total_results:
            keyboardNavRow.append(
                InlineKeyboardButton(
                    self._xlate("next_button"),
                    callback_data=f"{cid}^^^{offset + num}^^^next",
                ),
            )
        keyboard.append(keyboardNavRow)
        reply_markup = InlineKeyboardMarkup(keyboard)

        reply_message = self._xlate(
            "listing_users_pagination",
            page_info=f"{offset + 1}-{min(offset + num, total_results)} of {total_results}",
        )
        return (reply_message, reply_markup)

    def _load_language(self, lang_ietf=None):
        if not lang_ietf:
            if not hasattr(settings, "searcharr_language"):
                logger.warning(
                    "No language defined! Defaulting to en-us. Please add searcharr_language to settings.py if you want another language, where the value is a filename (without .yml) in the lang folder."
                )
                settings.searcharr_language = "en-us"
            lang_ietf = settings.searcharr_language
        logger.debug(f"Attempting to load language file: lang/{lang_ietf}.yml...")
        try:
            with open(f"lang/{lang_ietf}.yml", mode="r", encoding="utf-8") as y:
                lang = yaml.load(y, Loader=yaml.SafeLoader)
        except FileNotFoundError:
            logger.error(
                f"Error loading lang/{lang_ietf}.yml. Confirm searcharr_language in settings.py has a corresponding yml file in the lang subdirectory. Using default (English) language file."
            )
            with open("lang/en-us.yml", "r") as y:
                lang = yaml.load(y, Loader=yaml.SafeLoader)
        return lang

    def _xlate(self, key, **kwargs):
        if t := self._lang.get(key):
            return t.format(**kwargs)
        else:
            logger.error(f"No translation found for key [{key}]!")
            if self._lang.get("language_ietf") != "en-us":
                if t := self._lang_default.get(key):
                    logger.info(f"Using default language for key [{key}]...")
                    return t.format(**kwargs)
        return "(translation not found)"

    def _init_db(self):
        con, cur = self._get_con_cur()
        queries = [
            """CREATE TABLE IF NOT EXISTS conversations (
                id text primary key,
                username text not null,
                type text,
                results text
            );""",
            """CREATE TABLE IF NOT EXISTS users (
                id integer primary key,
                username text not null,
                admin text,
                permissions text
            );""",
            """CREATE TABLE IF NOT EXISTS add_data (
                cid text,
                key text,
                value text,
                primary key (cid, key)
            );""",
        ]
        for q in queries:
            logger.debug(f"Executing query: [{q}] with no args...")
            try:
                with DBLOCK:
                    cur.execute(q)
            except sqlite3.Error as e:
                logger.error(f"Error executing database query [{q}]: {e}")
                raise

        con.commit()
        con.close()

    def _dict_factory(self, cursor, row):
        """From sqlite3 documentation:
        https://docs.python.org/3/library/sqlite3.html#sqlite3.Connection.row_factory
        """
        d = {}
        for idx, col in enumerate(cursor.description):
            d[col[0]] = row[idx]
        return d

    def _get_con_cur(self):
        # Connect to local DB and return tuple containing connection and cursor
        if not os.path.isdir(DBPATH):
            try:
                logger.debug(
                    "The data directory does not exist. Attempting to create it..."
                )
                os.mkdir(DBPATH)
            except Exception as e:
                logger.error(f"Error creating data directory: {e}.")
                raise

        try:
            con = sqlite3.connect(os.path.join(DBPATH, DBFILE), timeout=30)
            con.execute("PRAGMA journal_mode = off;")
            con.row_factory = self._dict_factory
            cur = con.cursor()
            logger.debug(
                f"Database connection established [{os.path.join(DBPATH, DBFILE)}]."
            )
        except sqlite3.Error as e:
            logger.error(f"Error connecting to database: {e}")
            raise

        return (con, cur)

    def _create_conversation(self, id, username, kind, results):
        con, cur = self._get_con_cur()
        q = "INSERT OR REPLACE INTO conversations (id, username, type, results) VALUES (?, ?, ?, ?)"
        qa = (id, username, kind, json.dumps(results))
        logger.debug(f"Executing query: [{q}] with args: [{qa}]")
        try:
            with DBLOCK:
                cur.execute(q, qa)
                con.commit()
                con.close()
                return True
        except sqlite3.Error as e:
            logger.error(
                f"Error executing database query to create conversation [{q}]: {e}"
            )
            raise

    def _generate_cid(self):
        q = "SELECT * FROM conversations WHERE id=?"
        con, cur = self._get_con_cur()
        while True:
            u = uuid.uuid4().hex[:8]
            try:
                r = cur.execute(q, (u,))
            except sqlite3.Error as e:
                r = None
                logger.error(
                    f"Error executing database query to check conversation id uniqueness [{q}]: {e}"
                )

            if not r:
                return None
            elif not len(r.fetchall()):
                con.close()
                return u
            else:
                logger.warning("Detected conversation id collision. Interesting.")

    def _get_conversation(self, id):
        q = "SELECT * FROM conversations WHERE id=?;"
        qa = (id,)
        logger.debug(f"Executing query: [{q}] with args: [{qa}]...")
        try:
            con, cur = self._get_con_cur()
            r = cur.execute(q, qa)
        except sqlite3.Error as e:
            r = None
            logger.error(
                f"Error executing database query to look up conversation from the database [{q}]: {e}"
            )

        if r:
            record = r.fetchone()
            if record:
                logger.debug(f"Found conversation {record['id']} in the database")
                record.update({"results": json.loads(record["results"])})
            con.close()
            return record

        logger.debug(f"Found no conversation for id [{id}]")
        return None

    def _delete_conversation(self, id):
        self._clear_add_data(id)
        q = "DELETE FROM conversations WHERE id=?;"
        qa = (id,)
        logger.debug(f"Executing query: [{q}] with args: [{qa}]")
        try:
            con, cur = self._get_con_cur()
            with DBLOCK:
                cur.execute(q, qa)
                con.commit()
                con.close()
                return True
        except sqlite3.Error as e:
            logger.error(
                f"Error executing database query to delete conversation from the database [{q}]: {e}"
            )
            return False

    def _get_add_data(self, cid):
        q = "SELECT * FROM add_data WHERE cid=?;"
        qa = (cid,)
        logger.debug(f"Executing query: [{q}] with args: [{qa}]...")
        try:
            con, cur = self._get_con_cur()
            r = cur.execute(q, qa)
        except sqlite3.Error as e:
            r = None
            logger.error(
                f"Error executing database query to look up conversation add data from the database [{q}]: {e}"
            )

        if r:
            records = r.fetchall()
            con.close()
            logger.debug(f"Query response: {records}")
            return {x["key"]: x["value"] for x in records}
        else:
            return {}

    def _update_add_data(self, cid, key, value):
        con, cur = self._get_con_cur()
        q = "INSERT OR REPLACE INTO add_data (cid, key, value) VALUES (?, ?, ?)"
        qa = (cid, key, value)
        logger.debug(f"Executing query: [{q}] with args: [{qa}]")
        try:
            with DBLOCK:
                cur.execute(q, qa)
                con.commit()
                con.close()
                return True
        except sqlite3.Error as e:
            logger.error(f"Error executing database query [{q}]: {e}")
            raise

    def _clear_add_data(self, cid):
        q = "DELETE FROM add_data WHERE cid=?;"
        qa = (cid,)
        logger.debug(f"Executing query: [{q}] with args: [{qa}]")
        try:
            con, cur = self._get_con_cur()
            with DBLOCK:
                cur.execute(q, qa)
                con.commit()
                con.close()
                return True
        except sqlite3.Error as e:
            logger.error(
                f"Error executing database query to delete conversation add data from the database [{q}]: {e}"
            )
            return False

    def _add_user(self, id, username, admin=""):
        con, cur = self._get_con_cur()
        q = "INSERT OR REPLACE INTO users (id, username, admin) VALUES (?, ?, ?);"
        qa = (id, username, admin)
        logger.debug(f"Executing query: [{q}] with args: [{qa}]")
        try:
            with DBLOCK:
                cur.execute(q, qa)
                con.commit()
                con.close()
                return True
        except sqlite3.Error as e:
            logger.error(f"Error executing database query [{q}]: {e}")
            raise

    def _remove_user(self, id):
        con, cur = self._get_con_cur()
        q = "DELETE FROM users where id=?;"
        qa = (id,)
        logger.debug(f"Executing query: [{q}] with args: [{qa}]")
        try:
            with DBLOCK:
                cur.execute(q, qa)
                con.commit()
                con.close()
                return True
        except sqlite3.Error as e:
            logger.error(f"Error executing database query [{q}]: {e}")
            raise

    def _get_users(self, admin=False):
        adminQ = " where IFNULL(admin, '') != ''" if admin else ""
        q = f"SELECT * FROM users{adminQ};"
        logger.debug(f"Executing query: [{q}] with no args...")
        try:
            con, cur = self._get_con_cur()
            r = cur.execute(q)
        except sqlite3.Error as e:
            r = None
            logger.error(
                f"Error executing database query to look up users from the database [{q}]: {e}"
            )

        if r:
            records = r.fetchall()
            con.close()
            return records

        logger.debug(
            f"Found no {'admin ' if admin else ''}users in the database (this seems wrong)."
        )
        return []

    def _update_admin_access(self, user_id, admin=""):
        con, cur = self._get_con_cur()
        q = "UPDATE users set admin=? where id=?;"
        qa = (str(admin), user_id)
        logger.debug(f"Executing query: [{q}] with args: [{qa}]")
        try:
            with DBLOCK:
                cur.execute(q, qa)
                con.commit()
                con.close()
                return True
        except sqlite3.Error as e:
            logger.error(f"Error executing database query [{q}]: {e}")
            raise

    def _authenticated(self, user_id):
        # Return True if user is authenticated
        # Else return False
        q = "SELECT * FROM users WHERE id=?;"
        qa = (user_id,)
        logger.debug(f"Executing query: [{q}] with args: [{qa}]...")
        try:
            con, cur = self._get_con_cur()
            r = cur.execute(q, qa)
        except sqlite3.Error as e:
            r = None
            logger.error(
                f"Error executing database query to look up user from the database [{q}]: {e}"
            )
            return False

        if r:
            record = r.fetchone()
            logger.debug(f"Query result for user lookup: {record}")
            con.close()
            if record and record["id"] == user_id:
                return 2 if record["admin"] else 1

        logger.debug(f"Did not find user [{user_id}] in the database.")
        return False

    _bad_request_poster_error_messages = [
        "Wrong type of the web page content",
        "Wrong file identifier/http url specified",
        "Media_empty",
    ]


if __name__ == "__main__":
    args = parse_args()
    logger = set_up_logger("searcharr", args.verbose, args.console_logging)
    tgr = Searcharr(settings.tgram_token)
    tgr.run()