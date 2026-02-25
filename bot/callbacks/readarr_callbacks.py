"""
Searcharr
Sonarr, Radarr & Readarr Telegram Bot
Readarr-Specific Callback Handlers
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
import settings

logger = set_up_logger("callbacks.readarr")

# Create a config object for Readarr-specific settings
READARR_CONFIG = {
    "tag_with_username": settings.readarr_tag_with_username,
    "forced_tags": settings.readarr_forced_tags,
    "allow_user_to_select_tags": settings.readarr_allow_user_to_select_tags,
    "user_selectable_tags": settings.readarr_user_selectable_tags,
    "add_monitored": settings.readarr_add_monitored,
    "search_on_add": settings.readarr_search_on_add
}


async def handle_readarr_callback(update, context, bot, convo, cid, i, op, op_flags):
    """Handle callbacks related to Readarr (books).
    
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
        await handle_add_book(update, context, bot, convo, cid, i, op_flags)
    elif op == "prev" or op == "next":
        await handle_navigation(update, context, "book", convo, cid, i, op)
    elif op == "cancel" or op == "done":
        await handle_cancel(update, context, convo, cid, i, op)
    else:
        # Default action for unrecognized operations
        await query.answer()


async def handle_add_book(update, context, bot, convo, cid, i, op_flags):
    """Handle adding a book to Readarr.
    
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
    service = bot.readarr
    
    # Get the book result
    r = convo["results"][i]
    
    # If we have flags, process them first
    if op_flags:
        for k, v in op_flags.items():
            logger.debug(f"Adding/Updating additional data for cid=[{cid}], key=[{k}], value=[{v}]...")
            update_add_data(cid, k, v)
        
        # If this is a tag selection, handle it and return
        if op_flags.get("tt") or op_flags.get("td"):
            handled = await handle_tag_selection(update, context, service, READARR_CONFIG, convo, cid, i, op_flags)
            if handled:
                return
    
    # Get the additional data that has been collected so far
    additional_data = get_add_data(cid)
    logger.debug(f"Additional data: {additional_data}")
    
    # Step 1: Check for root folder selection
    if not await check_path_selection(update, context, service, "book", convo, cid, i):
        return
    
    # Step 2: Check for quality profile selection
    if not await check_quality_selection(update, context, service, "book", convo, cid, i):
        return
    
    # Step 3: Check for metadata profile selection (Readarr-specific)
    if not additional_data.get("m"):
        metadata_profiles = service._metadata_profiles
        if len(metadata_profiles) > 1:
            # Need to prompt user to select a metadata profile
            reply_message, reply_markup = prepare_response(
                "book",
                r,
                cid,
                i,
                len(convo["results"]),
                add=True,
                metadata_profiles=metadata_profiles,
            )
            await update_media_message(
                query.message,
                r["remotePoster"],
                caption=reply_message,
                reply_markup=reply_markup
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
                    kind=translate("book"),
                    app="Readarr",
                )
            )
            await query.message.delete()
            await query.answer()
            return
    
    # Step 4: Check for tag selection
    if READARR_CONFIG["allow_user_to_select_tags"] and not additional_data.get("td"):
        all_tags = service.get_filtered_tags(
            READARR_CONFIG["user_selectable_tags"],
            READARR_CONFIG["forced_tags"],
        )
        
        if all_tags and not additional_data.get("tt"):
            # Need to prompt user to select tags
            reply_message, reply_markup = prepare_response(
                "book",
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
    
    # Step 5: Process tags (username tag and forced tags)
    await process_tags(service, READARR_CONFIG, cid, query.from_user)
    
    # Step 6: All data collected, add the book
    logger.debug("All data is accounted for, proceeding to add...")
    try:
        added = service.add_book(
            book_info=r,
            monitored=READARR_CONFIG["add_monitored"],
            search=READARR_CONFIG["search_on_add"],
            additional_data=get_add_data(cid),
        )
    except Exception as e:
        logger.error(f"Error adding book: {e}")
        added = False
    
    logger.debug(f"Result of attempt to add book: {added}")
    
    # Step 7: Handle the result
    if added:
        delete_conversation(cid)
        await query.message.reply_text(translate("added", title=r["title"]))
        await query.message.delete()
    else:
        await query.message.reply_text(
            translate("unknown_error_adding", kind="book")
        )
    
    await query.answer()