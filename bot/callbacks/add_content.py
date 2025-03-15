"""
Searcharr
Sonarr, Radarr & Readarr Telegram Bot
Add Content Callback Handler
By Todd Roberts
https://github.com/toddrob99/searcharr
"""
from telegram import InputMediaPhoto
from telegram.error import BadRequest

from bot.utils.conversation import get_add_data, update_add_data, delete_conversation
from bot.utils.formatting import prepare_response
from bot.utils.text import translate
from bot.utils.log import set_up_logger
from config import settings

logger = set_up_logger("callbacks.add_content", False, False)


async def handle_add_content(update, context, bot, convo, cid, i, op, op_flags):
    """Handle callbacks related to adding content.
    
    Args:
        update: The update with the callback query
        context: The callback context
        bot: The SearcharrBot instance
        convo: The conversation data
        cid: The conversation ID
        i: The current index
        op: The operation ("add")
        op_flags: Additional operation flags
    """
    query = update.callback_query
    
    # Get the content result
    r = convo["results"][i]
    
    # If we have flags, process them first
    if op_flags:
        for k, v in op_flags.items():
            logger.debug(f"Adding/Updating additional data for cid=[{cid}], key=[{k}], value=[{v}]...")
            update_add_data(cid, k, v)
        
        # If this is a tag selection, return immediately to show the next menu
        if op_flags.get("tt") or op_flags.get("td"):
            await query.answer()
            return
    
    # Get the additional data that has been collected so far
    additional_data = get_add_data(cid)
    logger.debug(f"Additional data: {additional_data}")
    
    # Determine which service we're working with based on content type
    if convo["type"] == "series":
        service = bot.sonarr
        paths = service._root_folders
        quality_profiles = service._quality_profiles
        metadata_profiles = None
        forced_tags = settings.sonarr_forced_tags
        tag_with_username = settings.sonarr_tag_with_username
        allow_user_to_select_tags = settings.sonarr_allow_user_to_select_tags
        user_selectable_tags = settings.sonarr_user_selectable_tags
    elif convo["type"] == "movie":
        service = bot.radarr
        paths = service._root_folders
        quality_profiles = service._quality_profiles
        metadata_profiles = None
        forced_tags = settings.radarr_forced_tags
        tag_with_username = settings.radarr_tag_with_username
        allow_user_to_select_tags = settings.radarr_allow_user_to_select_tags
        user_selectable_tags = settings.radarr_user_selectable_tags
    elif convo["type"] == "book":
        service = bot.readarr
        paths = service._root_folders
        quality_profiles = service._quality_profiles
        metadata_profiles = service._metadata_profiles
        forced_tags = settings.readarr_forced_tags
        tag_with_username = settings.readarr_tag_with_username
        allow_user_to_select_tags = settings.readarr_allow_user_to_select_tags
        user_selectable_tags = settings.readarr_user_selectable_tags
    else:
        logger.error(f"Unsupported content type: {convo['type']}")
        await query.answer()
        return
    
    # Step 1: Check for root folder selection
    if not additional_data.get("p"):
        if len(paths) > 1:
            # Need to prompt user to select a path
            reply_message, reply_markup = prepare_response(
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
                if str(e) in [
                    "Wrong type of the web page content",
                    "Wrong file identifier/http url specified",
                    "Media_empty",
                ]:
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
            # Only one path, use it automatically
            logger.debug(
                f"Only one root folder enabled. Adding/Updating additional data for cid=[{cid}], key=[p], value=[{paths[0]['path']}]..."
            )
            update_add_data(cid, "p", paths[0]["path"])
        else:
            # No paths available, show error and cancel
            delete_conversation(cid)
            await query.message.reply_text(
                translate(
                    "no_root_folders",
                    kind=translate(convo["type"]),
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
    else:
        # Path is already selected, but might be an ID that needs to be translated to a path
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
                update_add_data(cid, "p", path)
    
    # Step 2: Check for quality profile selection
    if not additional_data.get("q"):
        if len(quality_profiles) > 1:
            # Need to prompt user to select a quality profile
            reply_message, reply_markup = prepare_response(
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
                if str(e) in [
                    "Wrong type of the web page content",
                    "Wrong file identifier/http url specified",
                    "Media_empty",
                ]:
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
            # Only one quality profile, use it automatically
            logger.debug(
                f"Only one quality profile enabled. Adding/Updating additional data for cid=[{cid}], key=[q], value=[{quality_profiles[0]['id']}]..."
            )
            update_add_data(cid, "q", quality_profiles[0]["id"])
        else:
            # No quality profiles available, show error and cancel
            delete_conversation(cid)
            await query.message.reply_text(
                translate(
                    "no_quality_profiles",
                    kind=translate(convo["type"]),
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
    
    # Step 3: Check for metadata profile selection (Readarr only)
    if convo["type"] == "book" and not additional_data.get("m"):
        if len(metadata_profiles) > 1:
            # Need to prompt user to select a metadata profile
            reply_message, reply_markup = prepare_response(
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
                if str(e) in [
                    "Wrong type of the web page content",
                    "Wrong file identifier/http url specified",
                    "Media_empty",
                ]:
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
            # Only one metadata profile, use it automatically
            logger.debug(
                f"Only one metadata profile enabled. Adding/Updating additional data for cid=[{cid}], key=[m], value=[{metadata_profiles[0]['id']}]..."
            )
            update_add_data(cid, "m", metadata_profiles[0]["id"])
        else:
            # No metadata profiles available, show error and cancel
            delete_conversation(cid)
            await query.message.reply_text(
                translate(
                    "no_metadata_profiles",
                    kind=translate(convo["type"]),
                    app="Readarr",
                )
            )
            await query.message.delete()
            await query.answer()
            return
    
    # Step 4: Check for season monitor options (Sonarr only)
    if (
        convo["type"] == "series"
        and settings.sonarr_season_monitor_prompt
        and additional_data.get("m", False) is False
    ):
        # Need to prompt user to select season monitoring option
        monitor_options = [
            translate("all_seasons"),
            translate("first_season"),
            translate("latest_season"),
        ]
        reply_message, reply_markup = prepare_response(
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
            if str(e) in [
                "Wrong type of the web page content",
                "Wrong file identifier/http url specified",
                "Media_empty",
            ]:
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
    
    # Step 5: Check for tag selection
    if allow_user_to_select_tags and not additional_data.get("td"):
        all_tags = service.get_filtered_tags(
            user_selectable_tags,
            forced_tags,
        )
        
        if not all_tags:
            logger.warning(
                f"User tagging is enabled, but no tags found. Make sure there are tags in {convo['type'].title()} matching your Searcharr configuration."
            )
        elif not additional_data.get("tt"):
            # Need to prompt user to select tags
            reply_message, reply_markup = prepare_response(
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
                if str(e) in [
                    "Wrong type of the web page content",
                    "Wrong file identifier/http url specified",
                    "Media_empty",
                ]:
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
            # Tag was selected, add it and continue
            tag_ids = (
                additional_data.get("t", "").split(",")
                if len(additional_data.get("t", ""))
                else []
            )
            tag_ids.append(additional_data["tt"])
            logger.debug(f"Adding tag [{additional_data['tt']}]")
            update_add_data(cid, "t", ",".join(tag_ids))
            
            # Return to show updated tag selection
            await query.answer()
            return
    
    # Step 6: Process tags (username tag and forced tags)
    tags = (
        additional_data.get("t").split(",")
        if len(additional_data.get("t", ""))
        else []
    )
    logger.debug(f"Current tags: {tags}")
    
    # Add username tag if enabled
    if tag_with_username:
        tag = f"searcharr-{query.from_user.username if query.from_user.username else query.from_user.id}"
        if tag_id := service.get_tag_id(tag):
            tags.append(str(tag_id))
        else:
            logger.warning(
                f"Tag lookup/creation failed for [{tag}]. This tag will not be added to the {convo['type']}."
            )
    
    # Add forced tags
    for tag in forced_tags:
        if tag_id := service.get_tag_id(tag):
            tags.append(str(tag_id))
        else:
            logger.warning(
                f"Tag lookup/creation failed for forced tag [{tag}]. This tag will not be added to the {convo['type']}."
            )
    
    # Update tag list (deduplicated)
    update_add_data(cid, "t", ",".join(list(set(tags))))
    
    # Step 7: All data collected, add the content
    logger.debug("All data is accounted for, proceeding to add...")
    try:
        if convo["type"] == "series":
            added = service.add_series(
                series_info=r,
                monitored=settings.sonarr_add_monitored,
                search=settings.sonarr_search_on_add,
                additional_data=get_add_data(cid),
            )
        elif convo["type"] == "movie":
            added = service.add_movie(
                movie_info=r,
                monitored=settings.radarr_add_monitored,
                search=settings.radarr_search_on_add,
                min_avail=settings.radarr_min_availability,
                additional_data=get_add_data(cid),
            )
        elif convo["type"] == "book":
            added = service.add_book(
                book_info=r,
                monitored=settings.readarr_add_monitored,
                search=settings.readarr_search_on_add,
                additional_data=get_add_data(cid),
            )
        else:
            added = False
    except Exception as e:
        logger.error(f"Error adding {convo['type']}: {e}")
        added = False
    
    logger.debug(f"Result of attempt to add {convo['type']}: {added}")
    
    # Step 8: Handle the result
    if added:
        delete_conversation(cid)
        await query.message.reply_text(translate("added", title=r["title"]))
        await query.message.delete()
    else:
        await query.message.reply_text(
            translate("unknown_error_adding", kind=convo["type"])
        )