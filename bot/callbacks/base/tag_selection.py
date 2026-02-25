"""
Searcharr
Sonarr, Radarr & Readarr Telegram Bot
Tag Selection Utilities
By Todd Roberts
https://github.com/toddrob99/searcharr
"""
from bot.callbacks.base.media_message import update_media_message
from bot.utils.conversation import get_add_data, update_add_data
from bot.utils.formatting import prepare_response
from bot.utils.log import set_up_logger

logger = set_up_logger("callbacks.base.tag_selection")


async def handle_tag_selection(update, context, service, service_config, convo, cid, i, op_flags):
    """Handle tag selection for content.
    
    Args:
        update: The update with the callback query
        context: The callback context
        service: The service client (Sonarr, Radarr, Readarr)
        service_config: Configuration for the service (settings.sonarr_*, etc.)
        convo: The conversation data
        cid: The conversation ID
        i: The current index
        op_flags: Additional operation flags
        
    Returns:
        bool: True if tag selection is handled, False if should proceed to next step
    """
    query = update.callback_query
    
    # Get the content result
    r = convo["results"][i]
    
    # Return if no tag-related flags
    if not op_flags.get("tt") and not op_flags.get("td"):
        return False
    
    # Get current additional data
    additional_data = get_add_data(cid)
    
    # Process a new tag selection
    if op_flags.get("tt"):
        tag_id = op_flags.get("tt")
        
        # Get current tags
        tag_ids = (
            additional_data.get("t", "").split(",")
            if len(additional_data.get("t", ""))
            else []
        )
        
        # Add new tag
        if tag_id not in tag_ids:
            tag_ids.append(tag_id)
            logger.debug(f"Adding tag [{tag_id}]")
            update_add_data(cid, "t", ",".join(tag_ids))
        
        # Get all available tags
        all_tags = service.get_filtered_tags(
            service_config.get("user_selectable_tags", []),
            service_config.get("forced_tags", []),
        )
        
        # Prepare response with updated tag selection
        reply_message, reply_markup = prepare_response(
            convo["type"],
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
        return True
    
    # Process tag selection completion
    elif op_flags.get("td"):
        # Mark tag selection as done
        update_add_data(cid, "td", "1")
        await query.answer()
        return False
    
    return False


async def process_tags(service, service_config, cid, user):
    """Process tags for content (username tag and forced tags).
    
    Args:
        service: The service client (Sonarr, Radarr, Readarr)
        service_config: Configuration for the service
        cid: The conversation ID
        user: The user who triggered the action
        
    Returns:
        bool: True on success
    """
    additional_data = get_add_data(cid)
    
    # Extract current tags
    tags = (
        additional_data.get("t").split(",")
        if len(additional_data.get("t", ""))
        else []
    )
    logger.debug(f"Current tags: {tags}")
    
    # Add username tag if enabled
    if service_config.get("tag_with_username", True):
        tag = f"searcharr-{user.username if user.username else user.id}"
        if tag_id := service.get_tag_id(tag):
            tags.append(str(tag_id))
        else:
            logger.warning(
                f"Tag lookup/creation failed for [{tag}]. This tag will not be added to the content."
            )
    
    # Add forced tags
    for tag in service_config.get("forced_tags", []):
        if tag_id := service.get_tag_id(tag):
            tags.append(str(tag_id))
        else:
            logger.warning(
                f"Tag lookup/creation failed for forced tag [{tag}]. This tag will not be added to the content."
            )
    
    # Update tag list (deduplicated)
    update_add_data(cid, "t", ",".join(list(set(tags))))
    return True