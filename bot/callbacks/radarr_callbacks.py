"""
Searcharr
Sonarr, Radarr & Readarr Telegram Bot
Radarr-Specific Callback Handlers
By Todd Roberts
https://github.com/toddrob99/searcharr
"""
from bot.utils.conversation import get_add_data, update_add_data, delete_conversation
from bot.utils.formatting import prepare_response
from bot.utils.text import translate
from bot.utils.log import set_up_logger
from bot.callbacks.base import (
    handle_navigation,
    handle_cancel,
    check_path_selection,
    check_quality_selection,
    handle_tag_selection,
    process_tags,
    update_media_message
)
from config import settings

logger = set_up_logger("callbacks.radarr", False, False)

# Create a config object for Radarr-specific settings
RADARR_CONFIG = {
    "tag_with_username": settings.radarr_tag_with_username,
    "forced_tags": settings.radarr_forced_tags,
    "allow_user_to_select_tags": settings.radarr_allow_user_to_select_tags,
    "user_selectable_tags": settings.radarr_user_selectable_tags,
    "add_monitored": settings.radarr_add_monitored,
    "search_on_add": settings.radarr_search_on_add,
    "min_availability": settings.radarr_min_availability
}


async def handle_radarr_callback(update, context, bot, convo, cid, i, op, op_flags):
    """Handle callbacks related to Radarr (movies).
    
    Args:
        update: The update with the callback query
        context: The callback context
        bot: The SearcharrBot instance
        convo: The conversation data
        cid: The conversation ID
        i: The current index
        op: The operation
        op_flags: Additional operation flags
    """
    query = update.callback_query
    
    # Handle operations
    if op == "add":
        await handle_add_movie(update, context, bot, convo, cid, i, op_flags)
    elif op == "prev" or op == "next":
        await handle_navigation(update, context, "movie", convo, cid, i, op)
    elif op == "cancel" or op == "done":
        await handle_cancel(update, context, convo, cid, i, op)
    else:
        # Default action for unrecognized operations
        await query.answer()


async def handle_add_movie(update, context, bot, convo, cid, i, op_flags):
    """Handle adding a movie to Radarr.
    
    Args:
        update: The update with the callback query
        context: The callback context
        bot: The SearcharrBot instance
        convo: The conversation data
        cid: The conversation ID
        i: The current index
        op_flags: Additional operation flags
    """
    query = update.callback_query
    service = bot.radarr
    
    # Get the movie result
    r = convo["results"][i]
    
    # If we have flags, process them first
    if op_flags:
        for k, v in op_flags.items():
            logger.debug(f"Adding/Updating additional data for cid=[{cid}], key=[{k}], value=[{v}]...")
            update_add_data(cid, k, v)
        
        # If this is a tag selection, handle it and return
        if op_flags.get("tt") or op_flags.get("td"):
            handled = await handle_tag_selection(update, context, service, RADARR_CONFIG, convo, cid, i, op_flags)
            if handled:
                return
    
    # Get the additional data that has been collected so far
    additional_data = get_add_data(cid)
    logger.debug(f"Additional data: {additional_data}")
    
    # Step 1: Check for root folder selection
    if not await check_path_selection(update, context, service, "movie", convo, cid, i):
        return
    
    # Step 2: Check for quality profile selection
    if not await check_quality_selection(update, context, service, "movie", convo, cid, i):
        return
    
    # Step 3: Check for tag selection
    if RADARR_CONFIG["allow_user_to_select_tags"] and not additional_data.get("td"):
        all_tags = service.get_filtered_tags(
            RADARR_CONFIG["user_selectable_tags"],
            RADARR_CONFIG["forced_tags"],
        )
        
        if all_tags and not additional_data.get("tt"):
            # Present tags selection UI
            
            # Need to prompt user to select tags
            reply_message, reply_markup = prepare_response(
                "movie",
                r,
                cid,
                i,
                len(convo["results"]),
                add=True,
                tags=all_tags,
            )
            await update_media_message(
                query.message,
                r["remotePoster"],
                caption=reply_message,
                reply_markup=reply_markup
            )
            await query.answer()
            return
    
    # Step 4: Process tags (username tag and forced tags)
    await process_tags(service, RADARR_CONFIG, cid, query.from_user)
    
    # Step 5: All data collected, add the movie
    logger.debug("All data is accounted for, proceeding to add...")
    try:
        added = service.add_movie(
            movie_info=r,
            monitored=RADARR_CONFIG["add_monitored"],
            search=RADARR_CONFIG["search_on_add"],
            min_avail=RADARR_CONFIG["min_availability"],
            additional_data=get_add_data(cid),
        )
    except Exception as e:
        logger.error(f"Error adding movie: {e}")
        added = False
    
    logger.debug(f"Result of attempt to add movie: {added}")
    
    # Step 6: Handle the result
    if added:
        delete_conversation(cid)
        await query.message.reply_text(translate("added", title=r["title"]))
        await query.message.delete()
    else:
        await query.message.reply_text(
            translate("unknown_error_adding", kind="movie")
        )
    
    await query.answer()